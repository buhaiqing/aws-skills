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
    python3 scripts/gcl_metrics.py --timeseries docs/metrics/timeseries.csv
    python3 scripts/gcl_metrics.py --staleness-check --max-age-days 7
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

REPO = Path(__file__).resolve().parents[1]
AUDIT_DIR = REPO / "audit-results"
DEFAULT_TIMESERIES = REPO / "docs" / "metrics" / "timeseries.csv"
TIMESERIES_SCHEMA = ("timestamp", "window_days", "skill", "total", "pass", "fail", "pass_rate")

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


# P0-4: a self-test stub uses generator.command == "aws --self-test".
# These are produced by `gcl_runner.py --self-test` for unit-test / CI
# verification. They MUST NOT count toward production pass-rate — they
# always emit safety=0 deterministically (see gcl_runner self-test path).
SELF_TEST_COMMAND = "aws --self-test"


def is_real_trace(trace: dict) -> bool:
    """True iff the trace's last generator command was a real (non-stub) run."""
    iters = trace.get("iterations", [])
    if not iters:
        return False
    last_cmd = iters[-1].get("generator", {}).get("command", "")
    return isinstance(last_cmd, str) and bool(last_cmd.strip()) and last_cmd.strip() != SELF_TEST_COMMAND


def collect_traces(
    audit_dir: Path,
    days: int = 30,
    include_self_test: bool = False,
) -> list[TraceRow]:
    """Walk audit_dir for gcl-trace-*.json, classify, build TraceRow list.

    By default, self-test stub traces are excluded so dashboard pass-rates
    reflect real production runs only. Pass `include_self_test=True` to
    include stubs (debug / CI verification).
    """
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
        if not include_self_test and not is_real_trace(trace):
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
    md.append(
        "_Traces shown = real runs only (self-test stubs excluded). "
        "Pass `--include-self-test` to count stubs._"
    )
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


# ---------------------------------------------------------------------------
# Append-only timeseries (P0-1 persistence)
# ---------------------------------------------------------------------------

def utc_today() -> str:
    """UTC date (YYYY-MM-DD); the idempotency key for timeseries rows."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def read_timeseries(path: Path) -> list[dict[str, str]]:
    """Parse a timeseries CSV into dict rows. Missing file → []."""
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh) if r.get("timestamp") and r.get("skill")]


def build_timeseries_rows(rows: list[TraceRow], window_days: int, day: str) -> list[dict[str, str]]:
    """One CSV data row per skill that has ≥1 trace in the window."""
    agg = aggregate(rows)
    return [
        {
            "timestamp": day,
            "window_days": str(window_days),
            "skill": skill,
            "total": str(s["TOTAL"]),
            "pass": str(s["PASS"]),
            "fail": str(s["FAIL"]),
            "pass_rate": f"{s['PASS'] / s['TOTAL']:.4f}",
        }
        for skill, s in sorted(agg["by_skill"].items())
        if s["TOTAL"]
    ]


def append_timeseries(
    path: Path, rows: list[TraceRow], window_days: int, day: str | None = None,
) -> int:
    """Upsert per-skill rows into the append-only CSV.

    Same (timestamp, skill) replaces the stored row, so re-running inside one
    UTC day never duplicates data. Returns the number of rows written.

    Writes via a temp file + os.replace so an interrupted run leaves the previous
    CSV intact instead of a truncated one.
    """
    day = day or utc_today()
    new_rows = build_timeseries_rows(rows, window_days, day)
    new_keys = {(r["timestamp"], r["skill"]) for r in new_rows}
    kept = [r for r in read_timeseries(path) if (r["timestamp"], r["skill"]) not in new_keys]
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(TIMESERIES_SCHEMA))
            writer.writeheader()
            writer.writerows(kept + new_rows)
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise
    return len(new_rows)


def parse_timeseries_day(value: str) -> date | None:
    """Parse a YYYY-MM-DD cell; None when the row is dirty (never raise)."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def latest_timeseries_day(path: Path) -> date | None:
    """Most recent parseable date in the CSV; None when there is no usable row."""
    days = [d for d in (parse_timeseries_day(r["timestamp"]) for r in read_timeseries(path)) if d]
    return max(days) if days else None


def staleness_check(
    path: Path, max_age_days: int, today: date | None = None,
) -> tuple[bool, str]:
    """(ok, message): ok when the newest timeseries entry is within max_age_days."""
    today = today or datetime.now(timezone.utc).date()
    if (latest := latest_timeseries_day(path)) is None:
        return False, f"metrics stale: no data rows in {path}"
    age = (today - latest).days
    if age > max_age_days:
        return False, (f"metrics stale: latest entry {latest} is {age}d old "
                       f"(max {max_age_days}d)")
    return True, f"metrics fresh: latest entry {latest} ({age}d old, max {max_age_days}d)"


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
    ap.add_argument(
        "--timeseries",
        type=Path,
        default=None,
        help="append-only CSV to upsert per-skill metrics into",
    )
    ap.add_argument(
        "--staleness-check",
        action="store_true",
        help="exit 1 when the timeseries has no data or is older than --max-age-days",
    )
    ap.add_argument("--max-age-days", type=int, default=7)
    ap.add_argument(
        "--include-self-test",
        action="store_true",
        help="include self-test stub traces (generator.command == 'aws --self-test') "
        "in the dashboard. Default: hidden, so pass-rate reflects real runs only.",
    )
    args = ap.parse_args(argv)

    if args.staleness_check:
        ts_path = args.timeseries or DEFAULT_TIMESERIES
        ok, msg = staleness_check(ts_path, args.max_age_days)
        print(msg)
        return 0 if ok else 1

    rows = collect_traces(
        args.audit_dir,
        days=args.days,
        include_self_test=args.include_self_test,
    )
    if args.timeseries:
        written = append_timeseries(args.timeseries, rows, args.days)
        print(f"timeseries: {written} row(s) -> {args.timeseries}", file=sys.stderr)
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
