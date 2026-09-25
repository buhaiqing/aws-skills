#!/usr/bin/env python3
"""Append-only shadow learning outcome ledger and stdlib CLI."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

EVENT_TYPES = frozenset({"candidate_proposed", "candidate_evaluated", "promotion_recorded", "deployment_observed", "post_deploy_measured", "rollback_recorded"})
CHAIN = ("candidate_proposed", "candidate_evaluated", "promotion_recorded", "deployment_observed", "post_deploy_measured")


def _validate(event: dict) -> None:
    if not isinstance(event, dict) or not isinstance(event.get("event_id"), str) or not event["event_id"]:
        raise ValueError("event_id is required")
    if event.get("event_type") not in EVENT_TYPES:
        raise ValueError("unknown event_type")
    if not isinstance(event.get("candidate_id"), str) or not event["candidate_id"]:
        raise ValueError("candidate_id is required")


def append_event(path: Path, event: dict) -> bool:
    _validate(event)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        for line in path.read_text().splitlines():
            try:
                existing = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError("malformed ledger") from exc
            if existing.get("event_id") == event["event_id"]:
                return False
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
    return True


def verify_ledger(path: Path) -> bool:
    try:
        for line in path.read_text().splitlines():
            _validate(json.loads(line))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return False
    return True


def build_report(events: list[dict]) -> dict:
    for event in events:
        _validate(event)
    counts = Counter(e["event_type"] for e in events)
    candidates = {e["candidate_id"] for e in events if e["event_type"] == "candidate_proposed"}
    complete = {e["candidate_id"] for e in events if e["event_type"] in CHAIN[1:]}
    complete &= candidates
    measured = [e for e in events if e["event_type"] == "post_deploy_measured"]
    rolled = {e["candidate_id"] for e in events if e["event_type"] == "rollback_recorded"}
    return {
        "event_counts": dict(counts),
        "candidate_count": len(candidates),
        "complete_chains": sum(all(any(e["candidate_id"] == cid and e["event_type"] == kind for e in events) for kind in CHAIN) for cid in complete),
        "post_deploy_delta": sum(e.get("delta", 0) for e in measured),
        "rollback_rate": (len(rolled) / len(complete)) if complete else 0.0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("record", "report", "verify"):
        child = sub.add_parser(name)
        child.add_argument("--ledger", type=Path, default=Path("audit-results/rsi-shadow-loop/outcomes.jsonl"))
        if name == "record":
            child.add_argument("event", help="JSON event")
    args = parser.parse_args(argv)
    if args.command == "record":
        try:
            append_event(args.ledger, json.loads(args.event))
        except (ValueError, json.JSONDecodeError) as exc:
            print(json.dumps({"error": str(exc)}), file=sys.stderr)
            return 1
        return 0
    if args.command == "report":
        if not verify_ledger(args.ledger):
            print("malformed ledger", file=sys.stderr)
            return 1
        print(json.dumps(build_report([json.loads(x) for x in args.ledger.read_text().splitlines()]), sort_keys=True))
        return 0
    return 0 if verify_ledger(args.ledger) else 1


if __name__ == "__main__":
    raise SystemExit(main())
