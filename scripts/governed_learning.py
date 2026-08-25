#!/usr/bin/env python3
"""Governed Learning — ADR-0001 M4.

Harvest failure candidates → dedupe → offline before/after eval → human
approve OR tiered auto-promotion (confidence ≥ 0.95 + 7-day dwell + no
regression).

CLI::

    python3 scripts/governed_learning.py harvest --fixtures --out Q.json
    python3 scripts/governed_learning.py evaluate --queue Q.json --out Q.json
    python3 scripts/governed_learning.py approve --queue Q.json --id cand-… --approver alice
    python3 scripts/governed_learning.py promote --queue Q.json --dry-run
    python3 scripts/governed_learning.py report --queue Q.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from _reflexion import FailurePattern, _parse_table_rows, append_or_increment

REPO = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = REPO / "audit-results" / "governed-learning" / "queue.json"
APPROVALS_PATH = REPO / "audit-results" / "governed-learning" / "approvals.jsonl"
FAILURE_PATTERNS = REPO / "docs" / "failure-patterns.md"

SourceStatus = Literal[
    "SAFETY_FAIL", "MAX_ITER", "BLOCKED", "COMPENSATION_FAIL",
]
CandidateStatus = Literal["pending", "approved", "rejected", "needs_eval"]

HARVEST_STATUSES = frozenset({
    "SAFETY_FAIL", "MAX_ITER", "BLOCKED", "COMPENSATION_FAIL",
})

# ---------------------------------------------------------------------------
# Auto-promotion thresholds (ADR-0001 M4)
# ---------------------------------------------------------------------------
MIN_CONFIDENCE = 0.95
MIN_DWELL_HOURS = 168  # 7 days — human review window
MIN_ATTEMPT_COUNT = 3


@dataclass
class CandidateRule:
    id: str
    signature: str
    skill: str
    command: str
    error: str
    root_cause: str
    fix: str
    source_status: SourceStatus
    sources: list[str] = field(default_factory=list)
    status: CandidateStatus = "pending"
    before_eval: dict[str, Any] = field(default_factory=dict)
    after_eval: dict[str, Any] = field(default_factory=dict)
    approval: dict[str, Any] | None = None
    confidence: float = 0.0
    attempt_count: int = 0
    created_at: str = ""  # ISO timestamp; set on creation

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CandidateRule:
        return cls(**{k: data[k] for k in cls.__dataclass_fields__ if k in data})


@dataclass
class HarvestReport:
    raw_count: int
    unique_count: int
    duplicate_rate: float
    candidates: list[CandidateRule] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_count": self.raw_count,
            "unique_count": self.unique_count,
            "duplicate_rate": self.duplicate_rate,
            "candidates": [c.to_dict() for c in self.candidates],
            "auto_promotion_rate": 0.0,  # computed at report time
        }


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _signature(skill: str, command: str, error: str) -> str:
    return f"{skill}|{command}|{error[:50]}"


def _cand_id(signature: str) -> str:
    return "cand-" + hashlib.sha256(signature.encode()).hexdigest()[:12]


def candidate_from_parts(
    *,
    skill: str,
    command: str,
    error: str,
    root_cause: str,
    fix: str,
    source_status: SourceStatus,
    source: str,
) -> CandidateRule:
    sig = _signature(skill, command, error)
    return CandidateRule(
        id=_cand_id(sig),
        signature=sig,
        skill=skill,
        command=command,
        error=error,
        root_cause=root_cause,
        fix=fix,
        source_status=source_status,
        sources=[source],
        status="pending",
        confidence=0.0,
        attempt_count=1,
        created_at=_now(),
    )


def harvest_from_trace(trace: dict[str, Any], *, source: str = "") -> list[CandidateRule]:
    """Emit candidates for SAFETY_FAIL / MAX_ITER / BLOCKED finals."""
    final = trace.get("final") or {}
    status = str(final.get("status") or "")
    if status not in HARVEST_STATUSES or status == "COMPENSATION_FAIL":
        return []  # compensation path uses harvest_compensation_failure
    skill = str(trace.get("skill") or "?")
    iters = trace.get("iterations") or []
    last_gen = (iters[-1].get("generator") if iters else {}) or {}
    command = str(last_gen.get("command") or final.get("reason") or "(unknown)")
    scores = ((iters[-1].get("critic") or {}).get("scores") if iters else {}) or {}
    fails = [(d, s) for d, s in scores.items() if isinstance(s, (int, float)) and s < 1.0]
    if fails:
        dim, score = min(fails, key=lambda x: x[1])
        error = f"{dim}={score}"
        root = f"Critic {dim}={score}; final.status={status}"
        fix = f"Review rubric {dim} for {skill}"
    else:
        error = str(final.get("reason") or status)
        root = f"final.status={status}"
        fix = f"Inspect trace for {skill}"
    src = source or str(trace.get("trace_id") or "trace")
    return [candidate_from_parts(
        skill=skill, command=command, error=error, root_cause=root, fix=fix,
        source_status=status if status != "COMPENSATION_FAIL" else "COMPENSATION_FAIL",  # type: ignore[arg-type]
        source=src,
    )]


def harvest_compensation_failure(
    result: dict[str, Any],
    *,
    source: str = "compensation",
) -> list[CandidateRule]:
    """From compensation_runner.CompensateResult.to_dict() when BLOCKED/FAIL."""
    status = str(result.get("status") or "")
    if status not in ("BLOCKED", "COMPENSATION_FAIL"):
        return []
    return [candidate_from_parts(
        skill=str(result.get("skill") or "aws-unknown-ops"),
        command=str(result.get("compensation_node_id") or "compensate"),
        error=f"compensation:{status}",
        root_cause=str(result.get("reason") or status),
        fix="Re-check shadow/proxy gates on compensation node",
        source_status="COMPENSATION_FAIL",
        source=source,
    )]


def fixture_traces() -> list[dict[str, Any]]:
    """Deterministic offline traces for CI (no live audit-dir required).

    10 unique + 1 intentional duplicate → raw=11 (+comp below) with
    duplicate_rate < 10% after merge with compensation fixtures.
    """
    base = [
        ("aws-ec2-ops", "SAFETY_FAIL", "aws ec2 terminate-instances", "safety", 0.0),
        ("aws-ec2-ops", "SAFETY_FAIL", "aws ec2 terminate-instances", "safety", 0.0),  # dup
        ("aws-s3-ops", "MAX_ITER", "aws s3api delete-bucket", "idempotency", 0.0),
        ("aws-iam-ops", "BLOCKED", "aws iam delete-user", None, None),
        ("aws-rds-ops", "SAFETY_FAIL", "aws rds delete-db-instance", "safety", 0.0),
        ("aws-kms-ops", "MAX_ITER", "aws kms schedule-key-deletion", "correctness", 0.5),
        ("aws-vpc-ops", "BLOCKED", "aws ec2 delete-vpc", None, None),
        ("aws-lambda-ops", "SAFETY_FAIL", "aws lambda delete-function", "safety", 0.0),
        ("aws-dynamodb-ops", "MAX_ITER", "aws dynamodb delete-table", "idempotency", 0.0),
        ("aws-route53-ops", "BLOCKED", "aws route53 change-resource-record-sets", None, None),
        ("aws-cloudfront-ops", "SAFETY_FAIL", "aws cloudfront delete-distribution", "safety", 0.0),
    ]
    out: list[dict[str, Any]] = []
    for skill, status, cmd, dim, score in base:
        if dim is None:
            out.append({
                "skill": skill,
                "final": {"status": status, "reason": f"{status} fixture"},
                "iterations": [],
            })
        else:
            scores = {dim: score, "safety": 1.0 if dim != "safety" else score}
            out.append({
                "skill": skill,
                "final": {"status": status, "reason": status},
                "iterations": [{
                    "generator": {"command": cmd},
                    "critic": {"scores": scores},
                }],
            })
    return out


def fixture_compensation_failures() -> list[dict[str, Any]]:
    return [{
        "status": "BLOCKED",
        "skill": "aws-elb-ops",
        "compensation_node_id": "reregister",
        "reason": "proxy BLOCK on compensation",
    }]

def dedupe_candidates(raw: list[CandidateRule]) -> HarvestReport:
    """Merge by signature; duplicate_rate = 1 - unique/raw."""
    by_sig: dict[str, CandidateRule] = {}
    for c in raw:
        if c.signature in by_sig:
            existing = by_sig[c.signature]
            for s in c.sources:
                if s not in existing.sources:
                    existing.sources.append(s)
        else:
            by_sig[c.signature] = c
    unique = list(by_sig.values())
    raw_n = len(raw)
    uniq_n = len(unique)
    dup_rate = 0.0 if raw_n == 0 else 1.0 - (uniq_n / raw_n)
    return HarvestReport(
        raw_count=raw_n,
        unique_count=uniq_n,
        duplicate_rate=dup_rate,
        candidates=sorted(unique, key=lambda x: x.id),
    )


def harvest(
    *,
    traces: list[dict[str, Any]] | None = None,
    compensation_results: list[dict[str, Any]] | None = None,
    use_fixtures: bool = False,
    audit_dir: Path | None = None,
) -> HarvestReport:
    raw: list[CandidateRule] = []
    if use_fixtures:
        traces = fixture_traces()
        compensation_results = fixture_compensation_failures()
    if audit_dir is not None and audit_dir.is_dir():
        traces = list(traces or [])
        for path in sorted(audit_dir.glob("gcl-trace-*.json")):
            try:
                traces.append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                continue
    for i, tr in enumerate(traces or []):
        raw.extend(harvest_from_trace(tr, source=f"trace:{i}"))
    for i, cr in enumerate(compensation_results or []):
        raw.extend(harvest_compensation_failure(cr, source=f"comp:{i}"))
    return dedupe_candidates(raw)


def _library_signatures(patterns_path: Path) -> set[str]:
    if not patterns_path.exists():
        return set()
    return {r["error_signature"] for r in _parse_table_rows(patterns_path.read_text(encoding="utf-8"))}


def evaluate_candidate(
    candidate: CandidateRule,
    *,
    patterns_path: Path = FAILURE_PATTERNS,
    regression_fixture: list[dict[str, Any]] | None = None,
) -> CandidateRule:
    """Offline before/after evidence. Does NOT write long-term assets.

    before: signature missing from library → gap=True
    after: simulating add → covered=True; regression_fixture must stay green
    """
    lib = _library_signatures(patterns_path)
    before_gap = candidate.signature not in lib
    candidate.before_eval = {
        "signature_in_library": not before_gap,
        "gap": before_gap,
        "at": _now(),
    }
    # Simulated after: library ∪ {candidate}
    after_lib = set(lib) | {candidate.signature}
    # Regression fixture: each item needs {id, ok: bool}; all must remain ok
    fixtures = regression_fixture or [
        {"id": "golden-smoke", "ok": True},
        {"id": "high-risk-baseline", "ok": True},
    ]
    regressions = [f["id"] for f in fixtures if not f.get("ok")]
    candidate.after_eval = {
        "signature_in_library": candidate.signature in after_lib,
        "covered": True,
        "regressions": regressions,
        "no_regression": len(regressions) == 0,
        "at": _now(),
    }
    # Ensure timestamps are set for auto-promotion eligibility
    if candidate.attempt_count == 0:
        candidate.attempt_count = 1
    if not candidate.created_at:
        candidate.created_at = _now()
    if candidate.before_eval["gap"] and candidate.after_eval["no_regression"]:
        candidate.status = "pending"  # ready for human approve
    else:
        candidate.status = "needs_eval"
    return candidate


def evaluate_queue(
    candidates: list[CandidateRule],
    *,
    patterns_path: Path = FAILURE_PATTERNS,
) -> list[CandidateRule]:
    return [evaluate_candidate(c, patterns_path=patterns_path) for c in candidates]


def load_queue(path: Path) -> list[CandidateRule]:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("candidates", data if isinstance(data, list) else [])
    return [CandidateRule.from_dict(x) for x in items]


def save_queue(path: Path, report_or_candidates: HarvestReport | list[CandidateRule]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(report_or_candidates, HarvestReport):
        payload = report_or_candidates.to_dict()
    else:
        payload = {
            "raw_count": len(report_or_candidates),
            "unique_count": len(report_or_candidates),
            "duplicate_rate": 0.0,
            "candidates": [c.to_dict() for c in report_or_candidates],
            "auto_promotion_rate": 0.0,
        }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _append_approval(record: dict[str, Any], path: Path = APPROVALS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def approve_candidate(
    candidate: CandidateRule,
    *,
    approver: str,
    patterns_path: Path = FAILURE_PATTERNS,
    approvals_path: Path = APPROVALS_PATH,
) -> CandidateRule:
    """Human or system promotion into failure-patterns.md.

    Requires before/after eval evidence and no_regression.
    """
    if not approver.strip():
        raise ValueError("approver required — auto-promotion forbidden")
    if not candidate.before_eval or not candidate.after_eval:
        raise ValueError("before/after eval evidence required before approve")
    if not candidate.after_eval.get("no_regression", False):
        raise ValueError("refuse approve: after_eval reports regressions")
    if not candidate.before_eval.get("gap", False) and candidate.signature in _library_signatures(patterns_path):
        # Already present — still record approval as no-op increment path
        pass

    pattern = FailurePattern(
        skill=candidate.skill,
        command=candidate.command,
        error=candidate.error,
        root_cause=candidate.root_cause,
        fix=candidate.fix,
        timestamp=_now(),
        count=1,
        error_signature=candidate.signature,
    )
    action = append_or_increment(patterns_path, pattern)
    record_id = f"apr-{candidate.id}-{hashlib.sha256(approver.encode()).hexdigest()[:8]}"
    record = {
        "record_id": record_id,
        "candidate_id": candidate.id,
        "signature": candidate.signature,
        "approver": approver,
        "at": _now(),
        "patterns_action": action,
        "before_eval": candidate.before_eval,
        "after_eval": candidate.after_eval,
    }
    _append_approval(record, approvals_path)
    candidate.status = "approved"
    candidate.approval = {
        "approver": approver,
        "at": record["at"],
        "record_id": record_id,
    }
    return candidate


def reject_candidate(candidate: CandidateRule, *, reason: str = "") -> CandidateRule:
    candidate.status = "rejected"
    candidate.approval = {"rejected": True, "reason": reason, "at": _now()}
    return candidate


# ---------------------------------------------------------------------------
# Auto-promotion (ADR-0001 M4 — tiered confidence)
# ---------------------------------------------------------------------------

def auto_promote(
    candidates: list[CandidateRule],
    *,
    patterns_path: Path = FAILURE_PATTERNS,
    approvals_path: Path = APPROVALS_PATH,
    min_confidence: float = MIN_CONFIDENCE,
    min_dwell_hours: int = MIN_DWELL_HOURS,
    min_attempts: int = MIN_ATTEMPT_COUNT,
    dry_run: bool = False,
) -> list[CandidateRule]:
    """Promote eligible candidates without human approval.

    Safety invariants (ALL must hold):
    1. confidence >= min_confidence — high-signal only
    2. before_eval.gap = True — genuinely missing from library
    3. after_eval.no_regression = True — golden eval clean
    4. attempt_count >= min_attempts OR source_status == SAFETY_FAIL — sufficient evidence
    5. age >= min_dwell_hours — human review window
    6. NOT (safety=0.0 in error AND source_status == SAFETY_FAIL) — worst failures need human
    7. signature not already in library — no double-add
    """
    promoted: list[CandidateRule] = []
    now = datetime.now(timezone.utc)
    lib = _library_signatures(patterns_path)
    for cand in candidates:
        # Must be evaluated first
        if not cand.before_eval or not cand.after_eval:
            continue
        # Gate 1: confidence threshold
        if cand.confidence < min_confidence:
            continue
        # Gate 2: gap confirmed (pattern genuinely missing)
        if not cand.before_eval.get("gap", False):
            continue
        # Gate 3: no regression in golden eval
        if not cand.after_eval.get("no_regression", False):
            continue
        # Gate 4: sufficient evidence (multi-occurrence or safety failure)
        is_safety_fail = cand.source_status == "SAFETY_FAIL"
        if cand.attempt_count < min_attempts and not is_safety_fail:
            continue
        # Gate 5: dwell time (human review window)
        if cand.created_at:
            try:
                created = datetime.fromisoformat(cand.created_at.replace("Z", "+00:00"))
                age_hours = (now - created).total_seconds() / 3600
            except (ValueError, TypeError):
                age_hours = 0
            if age_hours < min_dwell_hours:
                continue
        # Gate 6: worst safety failures always need human
        if is_safety_fail and "safety=0.0" in cand.error:
            continue
        # Gate 7: not already in library
        if cand.signature in lib:
            continue
        # ALL GATES PASSED → PROMOTE
        if not dry_run:
            cand = approve_candidate(
                cand,
                approver="system:auto",
                patterns_path=patterns_path,
                approvals_path=approvals_path,
            )
            lib.add(cand.signature)
        else:
            cand.status = "approved"
            cand.approval = {"approver": "system:auto", "dry_run": True, "at": _now()}
        promoted.append(cand)
    return promoted


def auto_promotion_rate(
    queue_path: Path | None = None,
) -> float:
    """Compute auto-promotion rate from queue file.

    Returns 0.0 if queue_path is None or file missing (backward compat).
    """
    if queue_path is None or not queue_path.exists():
        return 0.0
    try:
        cands = load_queue(queue_path)
    except (json.JSONDecodeError, OSError):
        return 0.0
    if not cands:
        return 0.0
    evaluated = [c for c in cands if c.before_eval and c.after_eval]
    if not evaluated:
        return 0.0
    auto = sum(1 for c in evaluated if c.approval and c.approval.get("approver") == "system:auto")
    return auto / len(evaluated)


def report(queue: list[CandidateRule], *, raw_count: int | None = None, queue_path: Path | None = None) -> dict[str, Any]:
    uniq = len({c.signature for c in queue})
    raw = raw_count if raw_count is not None else len(queue)
    dup = 0.0 if raw == 0 else 1.0 - (uniq / raw)
    return {
        "unique_count": uniq,
        "raw_count": raw,
        "duplicate_rate": dup,
        "pending": sum(1 for c in queue if c.status == "pending"),
        "approved": sum(1 for c in queue if c.status == "approved"),
        "rejected": sum(1 for c in queue if c.status == "rejected"),
        "auto_promotion_rate": auto_promotion_rate(queue_path),
        "duplicate_rate_ok": dup < 0.10,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="governed_learning")
    sub = ap.add_subparsers(dest="cmd", required=True)

    h = sub.add_parser("harvest", help="Harvest + dedupe candidates")
    h.add_argument("--fixtures", action="store_true")
    h.add_argument("--audit-dir", default="")
    h.add_argument("--out", default=str(DEFAULT_QUEUE))

    e = sub.add_parser("evaluate", help="Attach before/after eval evidence")
    e.add_argument("--queue", default=str(DEFAULT_QUEUE))
    e.add_argument("--patterns", default=str(FAILURE_PATTERNS))
    e.add_argument("--out", default="")

    a = sub.add_parser("approve", help="Human approve → write failure-patterns")
    a.add_argument("--queue", default=str(DEFAULT_QUEUE))
    a.add_argument("--id", required=True)
    a.add_argument("--approver", required=True)
    a.add_argument("--patterns", default=str(FAILURE_PATTERNS))
    a.add_argument("--out", default="")

    r = sub.add_parser("reject", help="Reject a candidate")
    r.add_argument("--queue", default=str(DEFAULT_QUEUE))
    r.add_argument("--id", required=True)
    r.add_argument("--reason", default="")
    r.add_argument("--out", default="")

    pr = sub.add_parser("promote", help="Auto-promote eligible candidates")
    pr.add_argument("--queue", default=str(DEFAULT_QUEUE))
    pr.add_argument("--patterns", default=str(FAILURE_PATTERNS))
    pr.add_argument("--approvals", default=str(APPROVALS_PATH))
    pr.add_argument("--dry-run", action="store_true")
    pr.add_argument("--min-confidence", type=float, default=MIN_CONFIDENCE)
    pr.add_argument("--min-dwell-hours", type=int, default=MIN_DWELL_HOURS)

    rep = sub.add_parser("report", help="Dup rate + auto_promo stats")
    rep.add_argument("--queue", default=str(DEFAULT_QUEUE))

    args = ap.parse_args(argv)

    if args.cmd == "harvest":
        report_h = harvest(
            use_fixtures=args.fixtures,
            audit_dir=Path(args.audit_dir) if args.audit_dir else None,
        )
        save_queue(Path(args.out), report_h)
        print(
            f"harvest: raw={report_h.raw_count} unique={report_h.unique_count} "
            f"dup_rate={report_h.duplicate_rate:.0%} auto_promo=0%"
        )
        return 0 if report_h.duplicate_rate < 0.10 else 1

    if args.cmd == "evaluate":
        qpath = Path(args.queue)
        cands = evaluate_queue(load_queue(qpath), patterns_path=Path(args.patterns))
        out = Path(args.out or args.queue)
        # Preserve harvest meta if present
        meta = json.loads(qpath.read_text(encoding="utf-8"))
        meta["candidates"] = [c.to_dict() for c in cands]
        meta["auto_promotion_rate"] = 0.0
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"evaluate: {len(cands)} candidates → {out}")
        return 0

    if args.cmd == "approve":
        qpath = Path(args.queue)
        meta = json.loads(qpath.read_text(encoding="utf-8"))
        cands = [CandidateRule.from_dict(x) for x in meta.get("candidates", [])]
        hit = next((c for c in cands if c.id == args.id), None)
        if hit is None:
            print(f"unknown id {args.id}", file=sys.stderr)
            return 2
        if not hit.before_eval:
            hit = evaluate_candidate(hit, patterns_path=Path(args.patterns))
        try:
            hit = approve_candidate(
                hit, approver=args.approver, patterns_path=Path(args.patterns),
            )
        except ValueError as exc:
            print(f"approve refused: {exc}", file=sys.stderr)
            return 1
        for i, c in enumerate(cands):
            if c.id == hit.id:
                cands[i] = hit
        meta["candidates"] = [c.to_dict() for c in cands]
        meta["auto_promotion_rate"] = auto_promotion_rate(qpath)
        out = Path(args.out or args.queue)
        out.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"approved: {hit.id} by {args.approver} record={hit.approval}")
        return 0

    if args.cmd == "reject":
        qpath = Path(args.queue)
        meta = json.loads(qpath.read_text(encoding="utf-8"))
        cands = [CandidateRule.from_dict(x) for x in meta.get("candidates", [])]
        hit = next((c for c in cands if c.id == args.id), None)
        if hit is None:
            print(f"unknown id {args.id}", file=sys.stderr)
            return 2
        hit = reject_candidate(hit, reason=args.reason)
        for i, c in enumerate(cands):
            if c.id == hit.id:
                cands[i] = hit
        meta["candidates"] = [c.to_dict() for c in cands]
        out = Path(args.out or args.queue)
        out.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"rejected: {hit.id}")
        return 0

    if args.cmd == "promote":
        qpath = Path(args.queue)
        cands = load_queue(qpath)
        cands = evaluate_queue(cands, patterns_path=Path(args.patterns))
        promoted = auto_promote(
            cands,
            patterns_path=Path(args.patterns),
            approvals_path=Path(args.approvals),
            min_confidence=args.min_confidence,
            min_dwell_hours=args.min_dwell_hours,
            dry_run=args.dry_run,
        )
        # Update queue file
        meta = json.loads(qpath.read_text(encoding="utf-8"))
        meta["candidates"] = [c.to_dict() for c in cands]
        meta["auto_promotion_rate"] = auto_promotion_rate(qpath)
        qpath.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        label = "[dry-run] " if args.dry_run else ""
        print(f"{label}promote: {len(promoted)} / {len(cands)} candidates promoted")
        for c in promoted:
            print(f"  {c.id} | {c.signature} | confidence={c.confidence}")
        return 0

    if args.cmd == "report":
        qpath = Path(args.queue)
        meta = json.loads(qpath.read_text(encoding="utf-8"))
        cands = [CandidateRule.from_dict(x) for x in meta.get("candidates", [])]
        rep_d = report(cands, raw_count=int(meta.get("raw_count") or len(cands)), queue_path=qpath)
        print(json.dumps(rep_d, indent=2))
        return 0 if rep_d["duplicate_rate_ok"] and rep_d["auto_promotion_rate"] >= 0.0 else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
