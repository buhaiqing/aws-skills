#!/usr/bin/env python3
"""Telemetry Dashboard — production telemetry aggregation (L4 #8).

Aggregates signals from three sources into a single 30-day rolling dashboard:
1. `audit-results/gcl-trace-*.json` — per-GCL-run final status + iterations
2. `audit-results/golden/*.json`    — golden_eval per-scenario results
3. `audit-results/reflexion/*.json` — reflexion pattern counts (count >= 3)

Contract: `docs/superpowers/specs/2026-07-25-telemetry-dashboard-design.md`.

CLI:
    python3 scripts/telemetry_dashboard.py dashboard \\
        --audit-dir audit-results/ \\
        --out docs/telemetry/dashboard.md

        --timeseries docs/metrics/timeseries.csv

    python3 scripts/telemetry_dashboard.py alert \\
        --audit-dir audit-results/ \\
        --drop-threshold 0.05
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Sequence
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from gcl_metrics import is_real_trace, read_timeseries

REPO = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT_DIR = REPO / "audit-results"
DEFAULT_TIMESERIES = REPO / "docs" / "metrics" / "timeseries.csv"

_VALID_TRACE_STATUSES = {"PASS", "SAFETY_FAIL", "MAX_ITER"}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class SignalSlice:
    skill: str
    status: str
    timestamp: datetime
    source: str  # "gcl-trace" | "golden" | "reflexion"
    scenario_id: str | None = None
    fail_dim: str | None = None  # for gcl-trace: which dim scored < 1.0


@dataclass
class SkillMetric:
    skill: str
    pass_count: int
    fail_count: int
    total: int
    pass_rate: float           # 0..1
    # None == no prior data. Coercing it to a number rendered every Δ as +0.00,
    # i.e. "unknown" was displayed as "flat" (RSI P0-1).
    prior_pass_rate: float | None = None
    delta: float | None = None  # pass_rate - prior_pass_rate
    regression: bool = False


@dataclass
class Dashboard:
    window_days: int
    prior_window_days: int
    generated_at: datetime
    by_skill: list[SkillMetric]
    by_fail_mode: dict[str, int] = field(default_factory=dict)
    total_signals: int = 0
    signals_in_window: int = 0


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def _trace_timestamp(trace: dict, path: Path) -> datetime | None:
    """Best-effort timestamp extraction from a trace + its filename.

    Falls back to filesystem mtime if no in-trace timestamp. We rely on
    filename (`gcl-trace-YYYYMMDD-HHMMSS.json`) for stable ordering.
    """
    name = path.name
    # gcl-trace-YYYYMMDD-HHMMSS.json
    parts = name.replace(".json", "").split("-")
    if len(parts) >= 5:
        try:
            return datetime(
                int(parts[-3]), int(parts[-2]), int(parts[-1][:2]),
                int(parts[-1][2:4]), int(parts[-1][4:6]),
                tzinfo=timezone.utc,
            )
        except (ValueError, IndexError):
            pass
    # Fallback: file mtime
    try:
        ts = path.stat().st_mtime
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except OSError:
        return None


def load_signals(
    audit_dir: Path, golden_files: Sequence[Path] | None = None,
) -> list[SignalSlice]:
    """Load real traces and only explicitly selected Golden artifacts."""
    audit_dir = Path(audit_dir)
    signals: list[SignalSlice] = []

    # Source 1: gcl-trace-*.json
    for p in sorted(audit_dir.glob("gcl-trace-*.json")):
        try:
            trace = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        # Skip plan artifacts (no `iterations` key, or no final.status)
        if "iterations" not in trace or not is_real_trace(trace):
            continue
        final = trace.get("final") or {}
        status = final.get("status", "OTHER")
        if status not in _VALID_TRACE_STATUSES:
            continue
        ts = _trace_timestamp(trace, p)
        if ts is None:
            continue
        skill = trace.get("skill", "?")
        # Best-effort failed dim extraction (last iteration)
        fail_dim = None
        iters = trace.get("iterations") or []
        if iters:
            scores = (iters[-1].get("critic") or {}).get("scores") or {}
            for d, s in scores.items():
                try:
                    if float(s) < 1.0:
                        fail_dim = d
                        break
                except (TypeError, ValueError):
                    continue
        signals.append(SignalSlice(
            skill=skill, status=status, timestamp=ts,
            source="gcl-trace", fail_dim=fail_dim,
        ))

    # Source 2: explicitly selected golden_eval artifacts.
    seen_golden: set[tuple[str, str, str]] = set()
    for p in golden_files or ():
        try:
            payload = json.loads(Path(p).read_text(encoding="utf-8"))
            ts = datetime.fromtimestamp(Path(p).stat().st_mtime, tz=timezone.utc)
        except (json.JSONDecodeError, OSError):
            continue
        file_skill = payload.get("skill") or ""
        for r in payload.get("results", []):
            scenario = r.get("scenario") or {}
            scenario_id = str(scenario.get("id", "?"))
            skill_name = file_skill or scenario_id.split("-")[0]
            run_id = payload.get("run_id") or r.get("run_id")
            if run_id:
                identity = (skill_name, scenario_id, str(run_id))
            else:
                content = json.dumps(
                    r, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                ).encode("utf-8")
                identity = (skill_name, scenario_id, hashlib.sha256(content).hexdigest())
            if identity in seen_golden:
                continue
            seen_golden.add(identity)
            signals.append(SignalSlice(
                skill=skill_name,
                status="PASS" if r.get("matched_status") else "MISMATCH",
                timestamp=ts,
                source="golden",
                scenario_id=scenario_id,
            ))

    # Source 3: failure-patterns.md (reflexion — count rows with count>=3)
    fp = audit_dir.parent / "docs" / "failure-patterns.md"
    if fp.exists():
        # Only count rows with count >= 3 (high-frequency patterns)
        for line in fp.read_text(encoding="utf-8").splitlines():
            if not line.startswith("|") or "---" in line:
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 6:
                continue
            try:
                cnt = int(cells[5])
            except ValueError:
                continue
            if cnt >= 3:
                # Strip markdown backticks / whitespace from skill column
                skill_cell = cells[0].strip().strip("`").strip()
                signals.append(SignalSlice(
                    skill=skill_cell,
                    status="SAFETY_FAIL",
                    timestamp=datetime.fromtimestamp(fp.stat().st_mtime, tz=timezone.utc),
                    source="reflexion",
                    scenario_id=f"reflexion:{cells[1].strip()}",
                ))
    return signals


# ---------------------------------------------------------------------------
# Computation
# ---------------------------------------------------------------------------

def load_prior_from_timeseries(path: Path, cutoff: datetime) -> dict[str, float]:
    """Latest pass_rate per skill recorded strictly before `cutoff`.

    The CSV is the durable prior source: audit-results/ is pruned/ephemeral,
    so signal-derived priors silently vanish between runs.
    """
    priors: dict[str, tuple[str, float]] = {}
    for r in read_timeseries(path):
        if datetime.strptime(r["timestamp"], "%Y-%m-%d").replace(tzinfo=timezone.utc) >= cutoff:
            continue
        if r["skill"] not in priors or r["timestamp"] > priors[r["skill"]][0]:
            priors[r["skill"]] = (r["timestamp"], float(r["pass_rate"]))
    return {skill: rate for skill, (_ts, rate) in priors.items()}


def compute_dashboard(
    signals: list[SignalSlice],
    window_days: int = 30,
    prior_window_days: int = 30,
    now: datetime | None = None,
    timeseries_prior: dict[str, float] | None = None,
) -> Dashboard:
    """Aggregate signals into a Dashboard over [now-window, now] window."""
    now = now or datetime.now(timezone.utc)
    window_start = now - timedelta(days=window_days)
    prior_start = now - timedelta(days=window_days + prior_window_days)

    in_window: list[SignalSlice] = [s for s in signals if s.timestamp >= window_start]
    in_prior: list[SignalSlice] = [s for s in signals if prior_start <= s.timestamp < window_start]

    # Group by skill
    by_skill_curr: dict[str, list[SignalSlice]] = defaultdict(list)
    by_skill_prior: dict[str, list[SignalSlice]] = defaultdict(list)
    for s in in_window:
        by_skill_curr[s.skill].append(s)
    for s in in_prior:
        by_skill_prior[s.skill].append(s)

    fail_mode_counts: dict[str, int] = defaultdict(int)
    for s in in_window:
        if s.source == "gcl-trace" and s.status in ("SAFETY_FAIL", "MAX_ITER") and s.fail_dim:
            fail_mode_counts[s.fail_dim] += 1

    skills = sorted(set(by_skill_curr) | set(by_skill_prior))
    skill_metrics: list[SkillMetric] = []
    for skill in skills:
        curr = by_skill_curr.get(skill, [])
        prior = by_skill_prior.get(skill, [])
        # Only count PASS/FAIL in current; golden MISMATCH counts as fail too
        def _is_pass(s: SignalSlice) -> bool:
            return (s.status == "PASS") or (s.source == "golden" and s.status == "PASS")

        def _is_fail(s: SignalSlice) -> bool:
            return (s.status in ("SAFETY_FAIL", "MAX_ITER") or
                    (s.source == "golden" and s.status == "MISMATCH"))

        pc = sum(1 for s in curr if _is_pass(s))
        fc = sum(1 for s in curr if _is_fail(s))
        total = pc + fc
        pass_rate = (pc / total) if total > 0 else 0.0
        pp = sum(1 for s in prior if _is_pass(s))
        fp = sum(1 for s in prior if _is_fail(s))
        pt = pp + fp
        if timeseries_prior is not None:
            # CSV wins when supplied: absence of a skill means "no prior", not
            # "same as current".
            prior_pass = timeseries_prior.get(skill)
        else:
            prior_pass = (pp / pt) if pt > 0 else None
        delta = None if prior_pass is None else pass_rate - prior_pass
        reg = bool(delta is not None and delta <= -0.05)
        skill_metrics.append(SkillMetric(
            skill=skill, pass_count=pc, fail_count=fc, total=total,
            pass_rate=pass_rate, prior_pass_rate=prior_pass,
            delta=delta, regression=reg,
        ))

    return Dashboard(
        window_days=window_days,
        prior_window_days=prior_window_days,
        generated_at=now,
        by_skill=skill_metrics,
        by_fail_mode=dict(fail_mode_counts),
        total_signals=len(signals),
        signals_in_window=len(in_window),
    )


def detect_regressions(d: Dashboard, drop_threshold: float = 0.05) -> list[str]:
    """Return skill names whose pass_rate dropped by ≥ drop_threshold vs prior."""
    flagged: list[str] = []
    for m in d.by_skill:
        if m.total == 0 or m.delta is None:
            continue
        if m.delta <= -drop_threshold:
            flagged.append(m.skill)
    return flagged


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_markdown(d: Dashboard) -> str:
    """Render a Dashboard as a 4-section Markdown document."""
    lines: list[str] = []
    lines.append("# Telemetry Dashboard")
    lines.append("")
    lines.append(f"Generated: {d.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}  ")
    lines.append(f"Window: {d.window_days} days (signals: {d.signals_in_window} of {d.total_signals})")
    lines.append("")

    # Overview
    lines.append("## Overview")
    lines.append("")
    lines.append(f"- Skills covered: **{len(d.by_skill)}**")
    flagged = detect_regressions(d)
    if flagged:
        lines.append(f"- Regressions flagged: **{len(flagged)}** ({', '.join(flagged)})")
    else:
        lines.append("- Regressions flagged: 0")
    lines.append("")

    # Per-skill table
    lines.append("## Per-skill pass-rate (last 30 days vs prior 30 days)")
    lines.append("")
    lines.append("| Skill | Pass | Fail | Total | Pass-rate | Prior | Δ | Regression |")
    lines.append("|-------|------|------|-------|-----------|-------|---|------------|")
    for m in d.by_skill:
        if m.total == 0:
            continue
        flag = "🚩" if m.regression else ""
        prior = f"{m.prior_pass_rate:.2f}" if m.prior_pass_rate is not None else "n/a"
        delta = f"{m.delta:+.2f}" if m.delta is not None else "n/a"
        lines.append(
            f"| {m.skill} | {m.pass_count} | {m.fail_count} | {m.total} | "
            f"{m.pass_rate:.2f} | {prior} | "
            f"{delta} | {flag} |"
        )
    lines.append("")
    lines.append("_n/a = no prior-window data; Δ not computable._")
    lines.append("")

    # Fail-mode breakdown
    lines.append("## Fail-mode distribution")
    lines.append("")
    if d.by_fail_mode:
        lines.append("| Dimension | Count |")
        lines.append("|-----------|-------|")
        for dim, count in sorted(d.by_fail_mode.items(), key=lambda x: -x[1]):
            lines.append(f"| {dim} | {count} |")
    else:
        lines.append("_(no GCL failures in window)_")
    lines.append("")

    # Source distribution
    lines.append("## Sources")
    lines.append("")
    lines.append("- gcl-trace: per-run GCL final status (real production traces)")
    lines.append("- golden: per-scenario eval results")
    lines.append("- reflexion: failure patterns with count >= 3")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _emit_alert(d: Dashboard, threshold: float) -> int:
    flagged = detect_regressions(d, drop_threshold=threshold)
    print("## Alerts")
    if not flagged:
        print(f"no regressions (threshold={threshold})")
        return 0
    print(f"threshold: {threshold} (delta ≤ -{threshold})")
    for m in d.by_skill:
        if m.skill not in flagged or m.delta is None:
            continue
        print(f"- **{m.skill}**: pass_rate {m.prior_pass_rate:.2f} -> {m.pass_rate:.2f} "
              f"(Δ{m.delta:+.2f})")
    return 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="telemetry_dashboard")
    sub = ap.add_subparsers(dest="cmd", required=True)

    dash_p = sub.add_parser("dashboard", help="Render Markdown dashboard")
    dash_p.add_argument("--audit-dir", default=str(DEFAULT_AUDIT_DIR))
    dash_p.add_argument("--window-days", type=int, default=30)
    dash_p.add_argument("--out", default="-",
                        help="Output path; '-' for stdout")
    dash_p.add_argument("--timeseries", default=None,
                        help="CSV of historical pass-rates (prior source of truth)")
    dash_p.add_argument("--golden-file", action="append", default=[],
                        type=Path, help="Explicit Golden artifact; repeatable")

    alert_p = sub.add_parser("alert",
                             help="CI alert: exit 1 if any skill regressed")
    alert_p.add_argument("--audit-dir", default=str(DEFAULT_AUDIT_DIR))
    alert_p.add_argument("--window-days", type=int, default=30)
    alert_p.add_argument("--drop-threshold", type=float, default=0.05,
                         help="Pass-rate drop that triggers alert (default 0.05)")
    alert_p.add_argument("--timeseries", default=None,
                         help="CSV of historical pass-rates (prior source of truth)")
    alert_p.add_argument("--golden-file", action="append", default=[],
                         type=Path, help="Explicit Golden artifact; repeatable")

    args = ap.parse_args(argv)
    audit_dir = Path(args.audit_dir)
    signals = load_signals(audit_dir, golden_files=args.golden_file)
    now = datetime.now(timezone.utc)
    prior = None
    if args.timeseries:
        prior = load_prior_from_timeseries(
            Path(args.timeseries), now - timedelta(days=args.window_days),
        )
    dash = compute_dashboard(
        signals, window_days=args.window_days, now=now, timeseries_prior=prior,
    )

    if args.cmd == "dashboard":
        md = render_markdown(dash)
        if args.out == "-":
            sys.stdout.write(md)
        else:
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(md, encoding="utf-8")
            print(f"saved: {out}")
        return 0

    if args.cmd == "alert":
        return _emit_alert(dash, args.drop_threshold)

    ap.error(f"unknown command: {args.cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
