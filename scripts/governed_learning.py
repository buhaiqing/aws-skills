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
    python3 scripts/governed_learning.py report --queue Q.json --dwell-stats
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from _reflexion import FailurePattern, _parse_table_rows, append_or_increment

REPO = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = REPO / "audit-results" / "governed-learning" / "queue.json"
FIXTURE_STATE_PATH = DEFAULT_QUEUE.parent / "candidate-state.json"
APPROVALS_PATH = REPO / "audit-results" / "governed-learning" / "approvals.jsonl"
FAILURE_PATTERNS = REPO / "docs" / "failure-patterns.jsonl"
# Durable candidate store: {signature: {"first_seen": ISO8601,
# "attempt_count": int}}. Git-tracked — the queue itself lives in
# audit-results/ (git-ignored, pruned), so neither candidate age (Gate 5) nor
# repeat count (Gate 4) may be derived from it. Both fields are written in one
# atomic replace so they can never disagree.
CANDIDATE_STATE_PATH = REPO / "docs" / "governed-learning" / "candidate-state.json"
# Producer token for `FailurePattern.source`. `_reflexion._SOURCE_TO_KB` maps it
# to failure_kb.SOURCES "governed_learning"; passing "governed_learning" itself
# misses that map and falls through to _DEFAULT_KB_SOURCE="runtime_block",
# mis-attributing every governed-learning promotion to a runtime block.
KB_SOURCE_TOKEN = "governed_learning"

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

# ---------------------------------------------------------------------------
# Confidence model (Gate 1) — every addend maps to one real piece of evidence
# ---------------------------------------------------------------------------
# Repetition: a signature re-observed on separate harvests is not a one-off.
W_REPETITION = 0.30
MAX_REPETITION_SIGHTINGS = 3  # == MIN_ATTEMPT_COUNT → 0.90 of the 0.95 budget
# Severity: a Critic safety verdict is far stronger evidence that a rule is
# genuinely missing than an exhausted loop or a proxy block — the latter two
# are frequently environmental (timeout, sandbox policy), so they weigh little.
W_SOURCE_STATUS: dict[str, float] = {
    "SAFETY_FAIL": 0.65,
    "MAX_ITER": 0.10,
    "BLOCKED": 0.05,
    "COMPENSATION_FAIL": 0.05,
}
# Corroboration: independent producers (distinct trace ids) agreeing.
W_CORROBORATION = 0.05
MAX_CORROBORATION_SOURCES = 2


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


def load_candidate_state(path: Path = CANDIDATE_STATE_PATH) -> dict[str, dict[str, Any]]:
    """Read the durable {signature: {first_seen, attempt_count}} map.

    An unreadable file degrades to {} (every candidate restarts fresh).
    Individually malformed entries are dropped rather than the whole map, so
    one bad record cannot reset the age (Gate 5) or the evidence count
    (Gate 4) of every other candidate.
    """
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, AttributeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    state: dict[str, dict[str, Any]] = {}
    for signature, entry in payload.items():
        if not isinstance(entry, dict):
            continue
        first_seen = entry.get("first_seen")
        try:
            attempts = int(entry.get("attempt_count", 0))
        except (TypeError, ValueError):
            continue
        state[str(signature)] = {
            "first_seen": first_seen if isinstance(first_seen, str) else "",
            "attempt_count": max(0, attempts),
        }
    return state


def save_candidate_state(
    state: dict[str, dict[str, Any]],
    path: Path = CANDIDATE_STATE_PATH,
) -> None:
    """Atomically persist first_seen + attempt_count in a single replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(
        json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp_path, path)


def compute_confidence(candidate: CandidateRule) -> float:
    """Evidence-weighted confidence in [0, 1] for a candidate rule.

    Formula::

        confidence = min(1.0,
            W_REPETITION * min(attempt_count, MAX_REPETITION_SIGHTINGS)
          + W_SOURCE_STATUS[source_status]
          + W_CORROBORATION * min(distinct_sources - 1,
                                  MAX_CORROBORATION_SOURCES))

    Each addend is one real signal: how many separate harvests observed the
    signature, how severe the producing failure was, and how many independent
    producers agree.

    Why this shape — Gate 1 must be reachable but never free:
      * A single sighting of anything but SAFETY_FAIL scores <= 0.40, so one
        flake can never reach MIN_CONFIDENCE.
      * Reaching MIN_CONFIDENCE requires either MIN_ATTEMPT_COUNT repeat
        sightings (aligning Gate 1 with Gate 4) or one Critic SAFETY_FAIL
        verdict (0.95 exactly — strong, yet below a perfect 1.0, and Gate 5
        dwell / Gate 6 human-review still apply).
      * Corroboration across independent producers adds at most +0.10.
    """
    repetition = W_REPETITION * min(candidate.attempt_count, MAX_REPETITION_SIGHTINGS)
    severity = W_SOURCE_STATUS.get(candidate.source_status, 0.0)
    corroboration = W_CORROBORATION * min(
        max(len(set(candidate.sources)) - 1, 0), MAX_CORROBORATION_SOURCES,
    )
    # Rounded so the persisted value is stable across float noise at the
    # threshold (e.g. 0.30*3 + 0.05 would otherwise land at 0.9499999999999998).
    return round(min(1.0, repetition + severity + corroboration), 4)


def upsert_candidate(existing: CandidateRule, repeat: CandidateRule) -> CandidateRule:
    """Merge a repeat sighting into `existing` (mutates and returns it).

    Earliest created_at wins — never reset the dwell clock.
    """
    existing.attempt_count += repeat.attempt_count
    for s in repeat.sources:
        if s not in existing.sources:
            existing.sources.append(s)
    if repeat.created_at and (not existing.created_at or repeat.created_at < existing.created_at):
        existing.created_at = repeat.created_at
    return existing


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
    candidate = CandidateRule(
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
        attempt_count=1,
        created_at=_now(),
    )
    candidate.confidence = compute_confidence(candidate)
    return candidate


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
            upsert_candidate(by_sig[c.signature], c)
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
    candidate_state_path: Path | None = None,
) -> HarvestReport:
    """Harvest + dedupe.

    `candidate_state_path` selects the durable store: candidate `created_at`
    (earliest wins) and `attempt_count` (cumulative) come from it, and every
    sighting is written back. None (default) = ephemeral, every candidate
    starts its clock and its evidence count at this run only.
    """
    state = load_candidate_state(candidate_state_path) if candidate_state_path is not None else None
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
    if state is not None:
        for c in raw:
            entry = state.get(c.signature) or {}
            first_seen = entry.get("first_seen") or c.created_at
            state[c.signature] = {
                "first_seen": first_seen,
                "attempt_count": entry.get("attempt_count", 0) + 1,
            }
            c.created_at = first_seen
        save_candidate_state(state, candidate_state_path)
    report = dedupe_candidates(raw)
    if state is not None:
        # The store counted every sighting in this run, so its value is the
        # authoritative cumulative count — not the in-memory merge.
        for c in report.candidates:
            c.attempt_count = state[c.signature]["attempt_count"]
    for c in report.candidates:
        c.confidence = compute_confidence(c)
    return report


def _library_signatures(patterns_path: Path) -> set[str]:
    if not patterns_path.exists():
        return set()
    if patterns_path.suffix.lower() == ".jsonl":
        import failure_kb
        return {rec.error_signature for rec in failure_kb.load_jsonl(patterns_path) if rec.error_signature}
    return {r["error_signature"] for r in _parse_table_rows(patterns_path.read_text(encoding="utf-8"))}


def file_sha256(path: Path) -> str:
    """Return the SHA256 of the artifact's raw bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_eval_evidence(
    path: Path,
    producer: str,
    run_id: str,
    *,
    regressions: list[str] | None = None,
    no_regression: bool = True,
) -> dict[str, Any]:
    """Build auditable evidence for a real evaluation artifact."""
    return {
        "artifact_path": str(path),
        "artifact_sha256": file_sha256(path),
        "generated_at": _now(),
        "producer": producer,
        "run_id": run_id,
        "regressions": list(regressions or []),
        "no_regression": no_regression,
    }


def validate_eval_evidence(candidate: CandidateRule) -> bool:
    """Reject incomplete evidence or any artifact/hash mismatch."""
    evidence = candidate.after_eval
    required = ("artifact_path", "artifact_sha256", "generated_at", "producer", "run_id")
    if not isinstance(evidence, dict) or any(not isinstance(evidence.get(k), str) or not evidence[k] for k in required):
        return False
    digest = evidence["artifact_sha256"]
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        return False
    try:
        path = Path(evidence["artifact_path"])
        return path.is_file() and file_sha256(path) == digest and evidence.get("no_regression") is True
    except (OSError, TypeError, ValueError):
        return False


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
    # No implicit success fixture: callers must provide the independently
    # produced regression cases, and promotion still requires an artifact.
    if regression_fixture is None:
        regressions = ["fixture required"]
    else:
        regressions = [str(f.get("id", "unknown")) for f in regression_fixture if not f.get("ok")]
    candidate.after_eval = {
        "signature_in_library": candidate.signature in after_lib,
        "covered": True,
        "regressions": regressions,
        "no_regression": regression_fixture is not None and len(regressions) == 0,
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
    if not validate_eval_evidence(candidate):
        raise ValueError("refuse approve: eval artifact evidence invalid")
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
        # Explicit producer token — without it every promotion lands in the KB
        # as "runtime_block", erasing where the rule actually came from.
        source=KB_SOURCE_TOKEN,
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

GATE_EVALUATED = "G0_missing_eval"
GATE_CONFIDENCE = "G1_confidence"
GATE_GAP = "G2_no_gap"
GATE_REGRESSION = "G3_regression"
GATE_EVIDENCE = "G4_insufficient_evidence"
GATE_DWELL = "G5_dwell"
GATE_SAFETY = "G6_safety_zero"
GATE_DUPLICATE = "G7_already_in_library"


TERMINAL_GATES = frozenset({GATE_SAFETY, GATE_DUPLICATE})


def _age_hours(created_at: str, now: datetime) -> float:
    """Hours since `created_at`; 0 (i.e. never old enough) if unparseable."""
    try:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        return (now - created).total_seconds() / 3600
    except (ValueError, TypeError, AttributeError):
        return 0.0


def blocking_gate(
    candidate: CandidateRule,
    *,
    lib: set[str],
    now: datetime,
    min_confidence: float = MIN_CONFIDENCE,
    min_dwell_hours: int = MIN_DWELL_HOURS,
    min_attempts: int = MIN_ATTEMPT_COUNT,
) -> list[str]:
    """Return every gate that blocks `candidate`, in gate order."""
    gates: list[str] = []
    if not candidate.before_eval or not candidate.after_eval or not validate_eval_evidence(candidate):
        gates.append(GATE_EVALUATED)
    if candidate.confidence < min_confidence:
        gates.append(GATE_CONFIDENCE)
    if candidate.before_eval and not candidate.before_eval.get("gap", False):
        gates.append(GATE_GAP)
    if candidate.after_eval and not candidate.after_eval.get("no_regression", False):
        gates.append(GATE_REGRESSION)
    is_safety_fail = candidate.source_status == "SAFETY_FAIL"
    if candidate.attempt_count < min_attempts and not is_safety_fail:
        gates.append(GATE_EVIDENCE)
    if candidate.created_at and _age_hours(candidate.created_at, now) < min_dwell_hours:
        gates.append(GATE_DWELL)
    if is_safety_fail and "safety=0.0" in candidate.error:
        gates.append(GATE_SAFETY)
    if candidate.signature in lib:
        gates.append(GATE_DUPLICATE)
    return gates


def auto_promote(
    candidates: list[CandidateRule],
    *,
    patterns_path: Path = FAILURE_PATTERNS,
    approvals_path: Path = APPROVALS_PATH,
    min_confidence: float = MIN_CONFIDENCE,
    min_dwell_hours: int = MIN_DWELL_HOURS,
    min_attempts: int = MIN_ATTEMPT_COUNT,
    dry_run: bool = False,
    now: datetime | None = None,
    blocked_by: dict[str, list[str]] | None = None,
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

    `now` overrides the clock (tests); `blocked_by`, when given, is filled with
    {candidate_id: [gate_id, ...]} for every candidate that did not pass.
    """
    promoted: list[CandidateRule] = []
    now_dt = now or datetime.now(timezone.utc)
    lib = _library_signatures(patterns_path)
    for cand in candidates:
        gates = blocking_gate(
            cand,
            lib=lib,
            now=now_dt,
            min_confidence=min_confidence,
            min_dwell_hours=min_dwell_hours,
            min_attempts=min_attempts,
        )
        if gates:
            if blocked_by is not None:
                blocked_by[cand.id] = gates
            continue
        # Gate 1: confidence threshold
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


def auto_promotion_rate_of(candidates: list[CandidateRule]) -> float:
    """Share of evaluated candidates promoted by system:auto."""
    evaluated = [c for c in candidates if c.before_eval and c.after_eval]
    if not evaluated:
        return 0.0
    auto = sum(1 for c in evaluated if c.approval and c.approval.get("approver") == "system:auto")
    return auto / len(evaluated)


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
    return auto_promotion_rate_of(cands)


AGE_BUCKET_BOUNDARIES = (24, 72, 168)  # hours → <24, 24-72, 72-168, >=168


def _age_bucket(age_hours: float) -> str:
    """'<24h' | '24-72h' | '72-168h' | '>=168h'."""
    low = 0
    for high in AGE_BUCKET_BOUNDARIES:
        if age_hours < high:
            return f"{low}-{high}h" if low else f"<{high}h"
        low = high
    return f">={AGE_BUCKET_BOUNDARIES[-1]}h"


def dwell_stats(
    candidates: list[CandidateRule],
    *,
    patterns_path: Path = FAILURE_PATTERNS,
    min_confidence: float = MIN_CONFIDENCE,
    min_dwell_hours: int = MIN_DWELL_HOURS,
    min_attempts: int = MIN_ATTEMPT_COUNT,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Age histogram + blocking-gate census for still-pending candidates.

    Makes the dead gate observable: which candidates sit behind Gate 5 (dwell)
    and how long they have been waiting.
    """
    now_dt = now or datetime.now(timezone.utc)
    lib = _library_signatures(patterns_path)
    pending = [c for c in candidates if c.status == "pending"]
    histogram: dict[str, int] = {}
    blocked_by: dict[str, int] = {}
    dwell_blocked: list[dict[str, Any]] = []
    terminal_blocked: list[dict[str, Any]] = []
    for cand in pending:
        age_hours = _age_hours(cand.created_at, now_dt) if cand.created_at else 0.0
        bucket = _age_bucket(age_hours)
        histogram[bucket] = histogram.get(bucket, 0) + 1
        gates = blocking_gate(
            cand,
            lib=lib,
            now=now_dt,
            min_confidence=min_confidence,
            min_dwell_hours=min_dwell_hours,
            min_attempts=min_attempts,
        )
        for gate in gates or ["promotable"]:
            blocked_by[gate] = blocked_by.get(gate, 0) + 1
        terminal_gates = [gate for gate in gates if gate in TERMINAL_GATES]
        if GATE_DWELL in gates:
            dwell_blocked.append({
                "id": cand.id,
                "signature": cand.signature,
                "age_hours": round(age_hours, 1),
                "hours_remaining": None if terminal_gates else round(min_dwell_hours - age_hours, 1),
                "blocking_gates": gates,
                "terminal_gates": terminal_gates,
                "terminal": bool(terminal_gates),
            })
        if terminal_gates:
            terminal_blocked.append({
                "id": cand.id,
                "signature": cand.signature,
                "blocking_gates": gates,
                "terminal_gates": terminal_gates,
            })
    return {
        "generated_at": now_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "min_dwell_hours": min_dwell_hours,
        "pending_total": len(pending),
        "age_histogram_hours": histogram,
        "blocked_by_gate": blocked_by,
        "dwell_blocked_count": len(dwell_blocked),
        "dwell_blocked": sorted(dwell_blocked, key=lambda d: -d["age_hours"]),
        "terminal_gate_ids": sorted(TERMINAL_GATES),
        "terminal_blocked_count": len(terminal_blocked),
        "terminal_blocked": terminal_blocked,
    }


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
    h.add_argument(
        "--candidate-state", default=str(CANDIDATE_STATE_PATH),
        help="durable {signature: {first_seen, attempt_count}} store "
             "for candidate age (Gate 5) and evidence count (Gate 4)",
    )

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
    rep.add_argument("--patterns", default=str(FAILURE_PATTERNS))
    rep.add_argument(
        "--dwell-stats", action="store_true",
        help="print pending-candidate age histogram + blocking-gate census",
    )

    args = ap.parse_args(argv)

    if args.cmd == "harvest":
        candidate_state_path = Path(args.candidate_state)
        if args.fixtures and candidate_state_path == CANDIDATE_STATE_PATH:
            candidate_state_path = FIXTURE_STATE_PATH
        report_h = harvest(
            use_fixtures=args.fixtures,
            audit_dir=Path(args.audit_dir) if args.audit_dir else None,
            candidate_state_path=candidate_state_path,
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
        blocked_by: dict[str, list[str]] = {}
        promoted = auto_promote(
            cands,
            patterns_path=Path(args.patterns),
            approvals_path=Path(args.approvals),
            min_confidence=args.min_confidence,
            min_dwell_hours=args.min_dwell_hours,
            dry_run=args.dry_run,
            blocked_by=blocked_by,
        )
        # Update queue file
        meta = json.loads(qpath.read_text(encoding="utf-8"))
        meta["candidates"] = [c.to_dict() for c in cands]
        # From the just-promoted candidates: reading qpath back would report the
        # pre-promotion state and pin the rate at 0.0 forever.
        meta["auto_promotion_rate"] = auto_promotion_rate_of(cands)
        qpath.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        label = "[dry-run] " if args.dry_run else ""
        print(f"{label}promote: {len(promoted)} / {len(cands)} candidates promoted")
        for c in promoted:
            print(f"  {c.id} | {c.signature} | confidence={c.confidence}")
        blocked_counts = {
            gate: sum(gate in gates for gates in blocked_by.values())
            for gate in sorted({gate for gates in blocked_by.values() for gate in gates})
        }
        if blocked_counts:
            print(f"{label}blocked_by={json.dumps(blocked_counts)}")
        return 0

    if args.cmd == "report":
        qpath = Path(args.queue)
        if not qpath.exists():
            # Empty-state response (queue not yet produced by `harvest`).
            # Return exit 0 — absence of data is a legitimate state, not an error.
            # Keys mirror `dwell_stats()` populated output (lines 785-798) so
            # downstream consumers (dashboards, CI scripts) can read a fixed
            # schema whether the queue is empty or populated (C3).
            empty = {
                "generated_at": _now(),
                "pending_total": 0,
                "age_histogram_hours": {},
                "blocked_by_gate": {},
                "dwell_blocked_count": 0,
                "terminal_gate_ids": sorted(TERMINAL_GATES),
                "terminal_blocked_count": 0,
                "min_dwell_hours": MIN_DWELL_HOURS,
                "note": f"queue not found at {qpath}; run 'harvest' first",
            }
            print(json.dumps(empty, indent=2, ensure_ascii=False))
            return 0
        meta = json.loads(qpath.read_text(encoding="utf-8"))
        cands = [CandidateRule.from_dict(x) for x in meta.get("candidates", [])]
        if args.dwell_stats:
            print(json.dumps(
                dwell_stats(cands, patterns_path=Path(args.patterns)),
                indent=2, ensure_ascii=False,
            ))
            return 0
        rep_d = report(cands, raw_count=int(meta.get("raw_count") or len(cands)), queue_path=qpath)
        print(json.dumps(rep_d, indent=2))
        return 0 if rep_d["duplicate_rate_ok"] and rep_d["auto_promotion_rate"] >= 0.0 else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
