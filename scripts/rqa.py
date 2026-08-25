#!/usr/bin/env python3
"""RQA - Reasoning Quality Audit (L4 Gap 4): detect "right result, wrong process".

GCL's ``post-execution`` gate builds on trace validity, but a trace can be
valid while the *reasoning* is weak: the Critic may PASS a run whose safety
or idempotency dimension scored below full marks. RQA audits gcl-trace-*.json
files for exactly that signal and emits structured findings.

GCL mapping:
- Generator: the original GCL run (already produced the trace).
- Critic:    ``audit_trace`` re-scores the *process* against a fixed rule set.
- Termination: every rule fires at most once per trace; output is a finding
  list, never a loop.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT_DIR = REPO / "audit-results"

_RUBRIC_DIMENSIONS = (
    "correctness", "safety", "idempotency", "traceability", "spec_compliance",
)


@dataclass
class RqaFinding:
    """One process violation inside a trace that still ended PASS."""

    code: str  # RQA-001 | RQA-002 | RQA-003
    severity: str  # high | medium
    iter: int
    detail: str


def _final_iteration(trace: dict) -> dict | None:
    iters = trace.get("iterations") or []
    if not iters:
        return None
    final_status = (trace.get("final") or {}).get("status")
    # The PASS decision is recorded in the iteration whose decision is RETURN;
    # fall back to the last recorded iteration.
    for it in reversed(iters):
        if final_status == "PASS" and it.get("decision") == "RETURN":
            return it
    return iters[-1]


def audit_trace(trace: dict) -> list[RqaFinding]:
    """Audit one gcl-trace dict. Only PASS traces can carry RQA findings."""
    if (trace.get("final") or {}).get("status") != "PASS":
        return []

    findings: list[RqaFinding] = []
    iters = trace.get("iterations") or []
    if not iters:
        return [RqaFinding(
            code="RQA-002", severity="high", iter=0,
            detail="PASS with zero recorded iterations; process not auditable",
        )]

    final_it = _final_iteration(trace)
    scores = ((final_it or {}).get("critic") or {}).get("scores") or {}
    for dim in _RUBRIC_DIMENSIONS:
        if dim not in scores:
            findings.append(RqaFinding(
                code="RQA-003", severity="medium", iter=(final_it or {}).get("iter", 0),
                detail=f"PASS without a '{dim}' critic score",
            ))
            continue
        score = scores[dim]
        if score < 1.0:
            findings.append(RqaFinding(
                code="RQA-001",
                severity="high" if dim == "safety" else "medium",
                iter=(final_it or {}).get("iter", 0),
                detail=f"PASS with {dim}={score} (<1.0); result right, process weak",
            ))
    return findings


def audit_dir(audit_dir: Path) -> dict:
    """Batch-audit every gcl-trace-*.json under ``audit_dir``."""
    traces = sorted(audit_dir.glob("gcl-trace-*.json"))
    per_trace: dict[str, list[dict]] = {}
    total_findings = 0
    flagged = 0
    for path in traces:
        try:
            trace = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        findings = audit_trace(trace)
        per_trace[path.name] = [asdict(f) for f in findings]
        total_findings += len(findings)
        if findings:
            flagged += 1
    return {
        "traces_audited": len(traces),
        "traces_flagged": flagged,
        "total_findings": total_findings,
        "findings": per_trace,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="rqa",
        description="Reasoning Quality Audit: PASS traces with weak process.",
    )
    ap.add_argument("command", choices=["audit"])
    ap.add_argument("path", nargs="?", default=None,
                    help="Single trace JSON (default: batch over --dir)")
    ap.add_argument("--dir", default=str(DEFAULT_AUDIT_DIR))
    args = ap.parse_args(argv)

    if args.path:
        trace = json.loads(Path(args.path).read_text(encoding="utf-8"))
        findings = [asdict(f) for f in audit_trace(trace)]
        print(json.dumps({"findings": findings}, ensure_ascii=False, indent=2))
        return 0

    print(json.dumps(audit_dir(Path(args.dir)), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
