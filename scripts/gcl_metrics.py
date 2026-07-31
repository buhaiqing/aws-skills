#!/usr/bin/env python3
"""GCL Metrics — observability dashboard for audit-results/gcl-trace-*.json.

Parses real GCL traces (含 iterations + final) and excludes plan artifacts
(含 strategy / agents). Outputs Markdown report (default) or JSON (--json).

L4 dim #5: 可观测 / 遥测. Feeds P2 dashboard work.

Usage:
    python3 scripts/gcl_metrics.py                       # Markdown to stdout (30 days)
    python3 scripts/gcl_metrics.py --days 7              # window adjustable
    python3 scripts/gcl_metrics.py --json                # machine-readable
    python3 scripts/gcl_metrics.py --out PATH            # write Markdown to file
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

REPO = Path(__file__).resolve().parents[1]
AUDIT_DIR = REPO / "audit-results"

Status = Literal["PASS", "SAFETY_FAIL", "MAX_ITER", "OTHER"]


@dataclass
class TraceRow:
    path: Path
    skill: str
    status: Status
    started_at: datetime
    iter_count: int
    fail_dimensions: list[str]
    duration_seconds: float
    command: str


def classify_trace(trace: dict) -> Literal["gcl", "plan_artifact"]:
    """A real GCL trace has 'iterations' + 'final'; a plan artifact has 'strategy'/'agents'."""
    if "iterations" in trace and "final" in trace:
        return "gcl"
    return "plan_artifact"


def extract_final_status(trace: dict) -> str:
    return trace.get("final", {}).get("status", "OTHER")


def collect_traces(audit_dir: Path, days: int = 30) -> list[TraceRow]:
    """Walk audit_dir for gcl-trace-*.json, classify, build TraceRow list."""
    rows: list[TraceRow] = []
    if not audit_dir.exists():
        return rows
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    for p in sorted(audit_dir.glob("gcl-trace-*.json")):
        try:
            trace = json.loads(p.read_text())
        except Exception:
            continue
        if classify_trace(trace) != "gcl":
            continue
        iters = trace.get("iterations", [])
        last_critic = iters[-1].get("critic", {}).get("scores", {}) if iters else {}
        fail_dims = [f"{dim}={score}" for dim, score in last_critic.items() if score < 1.0]
        last_gen = iters[-1].get("generator", {}) if iters else {}
        command = last_gen.get("command", "(unknown)")
        mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
        if mtime < cutoff:
            continue
        rows.append(TraceRow(
            path=p,
            skill=trace.get("skill", "?"),
            status=extract_final_status(trace),  # type: ignore[arg-type]
            started_at=mtime,
            iter_count=len(iters),
            fail_dimensions=fail_dims,
            duration_seconds=(datetime.now(timezone.utc) - mtime).total_seconds(),
            command=command,
        ))
    return rows


def aggregate(rows: list[TraceRow]) -> dict[str, Any]:
    """Per-skill pass-rate + dimension fail histogram."""
    by_skill: dict[str, dict[str, int]] = {}
    dim_fails: dict[str, int] = {}
    for r in rows:
        s = by_skill.setdefault(r.skill, {"PASS": 0, "FAIL": 0, "TOTAL": 0})
        s["TOTAL"] += 1
        if r.status == "PASS":
            s["PASS"] += 1
        else:
            s["FAIL"] += 1
        for fd in r.fail_dimensions:
            dim = fd.split("=")[0]
            dim_fails[dim] = dim_fails.get(dim, 0) + 1
    return {"by_skill": by_skill, "dim_fails": dim_fails}


def render_markdown(rows: list[TraceRow]) -> str:
    """Three tables: Overview by skill / Pass-rate by skill / Failure dimensions histogram."""
    agg = aggregate(rows)
    now = datetime.now(timezone.utc).isoformat()
    md: list[str] = []
    md.append("# GCL Metrics Report")
    md.append("")
    md.append(f"_Generated: {now}_")
    md.append(f"_Traces (last 30 days): {len(rows)}_")
    md.append("")
    md.append("## Overview by skill")
    md.append("")
    md.append("| skill | PASS | FAIL | TOTAL | pass_rate |")
    md.append("|-------|------|------|-------|-----------|")
    for skill, s in sorted(agg["by_skill"].items()):
        rate = (s["PASS"] / s["TOTAL"]) if s["TOTAL"] else 0.0
        md.append(f"| {skill} | {s['PASS']} | {s['FAIL']} | {s['TOTAL']} | {rate:.2f} |")
    md.append("")
    md.append("## Pass-rate by skill")
    md.append("")
    md.append("| skill | pass_rate |")
    md.append("|-------|-----------|")
    for skill, s in sorted(agg["by_skill"].items()):
        rate = (s["PASS"] / s["TOTAL"]) * 100 if s["TOTAL"] else 0.0
        md.append(f"| {skill} | {rate:.0f}% |")
    md.append("")
    md.append("## Failure dimensions histogram")
    md.append("")
    md.append("| dimension | fail_count |")
    md.append("|-----------|------------|")
    for dim, cnt in sorted(agg["dim_fails"].items(), key=lambda x: -x[1]):
        md.append(f"| {dim} | {cnt} |")
    md.append("")
    return "\n".join(md)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="GCL metrics dashboard")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", type=str, default=None)
    ap.add_argument(
        "--audit-dir",
        type=Path,
        default=AUDIT_DIR,
        help="directory of gcl-trace-*.json (default: repo audit-results/)",
    )
    args = ap.parse_args(argv)
    rows = collect_traces(args.audit_dir, days=args.days)
    if args.json:
        out = json.dumps(
            [{**asdict(r), "path": str(r.path)} for r in rows],
            default=str, indent=2,
        )
        sys.stdout.write(out)
        return 0
    md = render_markdown(rows)
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
        print(f"wrote {args.out} ({len(rows)} traces)")
    else:
        sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
