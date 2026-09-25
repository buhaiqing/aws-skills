#!/usr/bin/env python3
"""Append-only shadow learning outcome ledger and stdlib CLI."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

EVENT_TYPES = frozenset({"candidate_proposed", "candidate_evaluated", "promotion_recorded", "deployment_observed", "post_deploy_measured", "rollback_recorded"})
CHAIN = ("candidate_proposed", "candidate_evaluated", "promotion_recorded", "deployment_observed", "post_deploy_measured", "rollback_recorded")


def _validate(event: dict) -> None:
    if not isinstance(event, dict) or not isinstance(event.get("event_id"), str) or not event["event_id"]:
        raise ValueError("event_id is required")
    if event.get("event_type") not in EVENT_TYPES:
        raise ValueError("unknown event_type")
    if not isinstance(event.get("candidate_id"), str) or not event["candidate_id"]:
        raise ValueError("candidate_id is required")
    if event["event_type"] == "post_deploy_measured":
        delta = event.get("delta")
        if isinstance(delta, bool) or not isinstance(delta, (int, float)):
            raise ValueError("post_deploy delta must be numeric")


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
                if existing != event:
                    raise ValueError(f"event_id conflict: {event['event_id']}")
                return False
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
    return True


def verify_ledger(path: Path) -> bool:
    try:
        seen: set[str] = set()
        for line in path.read_text().splitlines():
            event = json.loads(line)
            _validate(event)
            if event["event_id"] in seen:
                return False
            seen.add(event["event_id"])
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return False
    return True


def record_queue(queue_path: Path, ledger_path: Path) -> int:
    """Record proposed/evaluated events for a harvested candidate queue."""
    payload = json.loads(queue_path.read_text(encoding="utf-8"))
    candidates = payload.get("candidates", []) if isinstance(payload, dict) else []
    recorded = 0
    for candidate in candidates:
        candidate_id = str(candidate.get("id", ""))
        if not candidate_id:
            raise ValueError("candidate id is required")
        for event_type in ("candidate_proposed", "candidate_evaluated"):
            event = {
                "event_id": f"{event_type}:{candidate_id}",
                "event_type": event_type,
                "candidate_id": candidate_id,
                "status": candidate.get("status", "unknown"),
            }
            if append_event(ledger_path, event):
                recorded += 1
    return recorded


def build_report(events: list[dict]) -> dict:
    seen_ids: set[str] = set()
    for event in events:
        _validate(event)
        if event["event_id"] in seen_ids:
            raise ValueError(f"duplicate event_id: {event['event_id']}")
        seen_ids.add(event["event_id"])
    counts = Counter(e["event_type"] for e in events)
    candidates = {e["candidate_id"] for e in events if e["event_type"] == "candidate_proposed"}
    seen: dict[str, set[str]] = {}
    for event in events:
        candidate_id = event["candidate_id"]
        event_type = event["event_type"]
        prior = seen.setdefault(candidate_id, set())
        if event_type in CHAIN[1:] and not set(CHAIN[:CHAIN.index(event_type)]).issubset(prior):
            raise ValueError("candidate event chain is out of order")
        prior.add(event_type)
    complete = {
        candidate_id for candidate_id in candidates
        if set(CHAIN).issubset(seen.get(candidate_id, set()))
    }
    measured = [e for e in events if e["event_type"] == "post_deploy_measured"]
    rolled = {e["candidate_id"] for e in events if e["event_type"] == "rollback_recorded"}
    return {
        "event_counts": dict(counts),
        "candidate_count": len(candidates),
        "complete_chains": len(complete),
        "post_deploy_delta": sum(e["delta"] for e in measured),
        "rollback_rate": (len(rolled & complete) / len(complete)) if complete else 0.0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("record", "record-queue", "report", "verify"):
        child = sub.add_parser(name)
        child.add_argument("--ledger", type=Path, default=Path("audit-results/rsi-shadow-loop/outcomes.jsonl"))
        if name == "record":
            child.add_argument("event", help="JSON event")
        if name == "record-queue":
            child.add_argument("--queue", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "record":
        try:
            append_event(args.ledger, json.loads(args.event))
        except (ValueError, json.JSONDecodeError) as exc:
            print(json.dumps({"error": str(exc)}), file=sys.stderr)
            return 1
        return 0
    if args.command == "record-queue":
        try:
            recorded = record_queue(args.queue, args.ledger)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(json.dumps({"error": str(exc)}), file=sys.stderr)
            return 1
        print(json.dumps({"recorded": recorded}))
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
