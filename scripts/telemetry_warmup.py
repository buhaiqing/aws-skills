#!/usr/bin/env python3
"""M1 telemetry warm-up clock — calendar hygiene only.

Does NOT mark ADR 满窗 complete. closeout-check fails until day >= 30.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_START = date(2026, 7, 31)
WINDOW_DAYS = 30
CALENDAR_DOC = REPO / "docs" / "telemetry" / "m1-warmup-calendar.md"


def _parse_start(s: str) -> date:
    return date.fromisoformat(s)


def status(
    *,
    start: date = DEFAULT_START,
    today: date | None = None,
    window_days: int = WINDOW_DAYS,
) -> dict:
    today = today or datetime.now(timezone.utc).date()
    elapsed = (today - start).days
    remaining = max(0, window_days - elapsed)
    eligible = elapsed >= window_days
    return {
        "warm_up_start": start.isoformat(),
        "today_utc": today.isoformat(),
        "window_days": window_days,
        "days_elapsed": elapsed,
        "days_remaining": remaining,
        "full_window_eligible": eligible,
        "target_closeout": (start.toordinal() + window_days),
        "target_closeout_date": date.fromordinal(start.toordinal() + window_days).isoformat(),
        "auto_heal_unlocked": False,  # hard: never auto-unlock via this tool
        "calendar_doc": str(CALENDAR_DOC.relative_to(REPO)),
    }


def closeout_check(
    *,
    start: date = DEFAULT_START,
    today: date | None = None,
    window_days: int = WINDOW_DAYS,
) -> tuple[int, dict]:
    """Exit 0 only when calendar eligible; still does not expand AUTO_HEAL."""
    st = status(start=start, today=today, window_days=window_days)
    st["adr_checkbox_allowed"] = bool(st["full_window_eligible"])
    st["note"] = (
        "Eligible to *review* ADR checkbox; AUTO_HEAL still manual."
        if st["full_window_eligible"]
        else "Too early — refuse closeout."
    )
    return (0 if st["full_window_eligible"] else 1), st


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="telemetry_warmup")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("status", "closeout-check"):
        p = sub.add_parser(name)
        p.add_argument("--start", default=DEFAULT_START.isoformat())
        p.add_argument("--today", default="")
        p.add_argument("--window-days", type=int, default=WINDOW_DAYS)
        p.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    start = _parse_start(args.start)
    today = _parse_start(args.today) if args.today else None

    if args.cmd == "status":
        st = status(start=start, today=today, window_days=args.window_days)
        print(json.dumps(st, indent=2) if args.json else (
            f"M1 warm-up: day {st['days_elapsed']}/{st['window_days']} "
            f"(remaining={st['days_remaining']}) "
            f"eligible={st['full_window_eligible']} "
            f"target={st['target_closeout_date']} "
            f"AUTO_HEAL_unlocked=false"
        ))
        return 0

    code, st = closeout_check(start=start, today=today, window_days=args.window_days)
    print(json.dumps(st, indent=2) if args.json else st["note"])
    return code


if __name__ == "__main__":
    raise SystemExit(main())
