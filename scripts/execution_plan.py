#!/usr/bin/env python3
"""ExecutionPlan — deterministic plan hashing for ADR-0001 M2 shadow gate.

Standalone (stdlib only). Importable by runtime_safety / safe_tool_proxy
without circular imports — this module must not import those modules.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from dataclasses import dataclass, field
from typing import Any, Mapping, Union


@dataclass
class ExecutionPlan:
    """Structured intent before shadow / mutation (spec §4)."""

    skill: str
    operation: str
    args: dict = field(default_factory=dict)
    region: str = ""
    resource_ids: list[str] = field(default_factory=list)
    risk: str = ""  # mode hint: read-only | write | destructive | …
    mode: str = ""  # extra mode hint (optional)
    plan_id: str = ""
    preconditions: list[str] = field(default_factory=list)
    expected_diff: dict = field(default_factory=dict)
    confirmation_op: str = ""
    verify: list[str] = field(default_factory=list)
    compensation: str | None = None  # M3 placeholder
    plan_hash: str = ""  # filled by compute_plan_hash; never hashed into itself


PlanOrCall = Union["ExecutionPlan", Mapping[str, Any]]


def _normalize_operation(operation: str) -> str:
    return " ".join(operation.strip().lower().replace("_", "-").split())


def _canonical_payload(plan: ExecutionPlan) -> dict:
    """Fields that identify the plan. Excludes plan_hash / plan_id / metadata."""
    return {
        "skill": plan.skill.strip().lower(),
        "operation": _normalize_operation(plan.operation),
        "args": plan.args or {},
        "region": (plan.region or "").strip().lower(),
        "resource_ids": sorted(str(r) for r in (plan.resource_ids or [])),
    }


def compute_plan_hash(plan: ExecutionPlan) -> str:
    """SHA256 hex digest over canonical JSON of skill+operation+normalized args (+ region/ids)."""
    canonical = json.dumps(
        _canonical_payload(plan),
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def make_plan(
    skill: str,
    operation: str,
    args: dict | None = None,
    *,
    region: str = "",
    resource_ids: list[str] | None = None,
    risk: str = "",
    mode: str = "",
    **kwargs: Any,
) -> ExecutionPlan:
    """Build an ExecutionPlan and set plan_hash / plan_id."""
    plan = ExecutionPlan(
        skill=skill,
        operation=operation,
        args=dict(args or {}),
        region=region,
        resource_ids=list(resource_ids or []),
        risk=risk,
        mode=mode,
        plan_id=str(kwargs.pop("plan_id", "") or uuid.uuid4()),
        preconditions=list(kwargs.pop("preconditions", []) or []),
        expected_diff=dict(kwargs.pop("expected_diff", {}) or {}),
        confirmation_op=str(kwargs.pop("confirmation_op", "") or ""),
        verify=list(kwargs.pop("verify", []) or []),
        compensation=kwargs.pop("compensation", None),
    )
    plan.plan_hash = compute_plan_hash(plan)
    return plan


def _as_plan(plan_or_call: PlanOrCall) -> ExecutionPlan:
    if isinstance(plan_or_call, ExecutionPlan):
        return plan_or_call
    data = dict(plan_or_call)
    operation = str(data.get("operation") or data.get("tool_name") or "")
    return ExecutionPlan(
        skill=str(data.get("skill", "") or ""),
        operation=operation,
        args=dict(data.get("args", {}) or {}),
        region=str(data.get("region", "") or ""),
        resource_ids=list(data.get("resource_ids", []) or []),
    )


def detect_plan_drift(expected_hash: str, plan_or_call: PlanOrCall) -> bool:
    """Return True if plan_or_call's hash differs from expected_hash (drift)."""
    return compute_plan_hash(_as_plan(plan_or_call)) != expected_hash


def assert_plan_matches_call(plan: ExecutionPlan, call: PlanOrCall) -> None:
    """Raise ValueError when call drifts from plan (region / resource / op / args)."""
    expected = plan.plan_hash or compute_plan_hash(plan)
    if detect_plan_drift(expected, call):
        raise ValueError(
            f"plan drift: expected_hash={expected[:16]}… "
            f"got={compute_plan_hash(_as_plan(call))[:16]}…"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="execution_plan",
        description="Deterministic ExecutionPlan hashing (ADR-0001 M2).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    hash_p = sub.add_parser("hash", help="Print plan_hash for skill/op/args")
    hash_p.add_argument("--skill", required=True)
    hash_p.add_argument("--op", required=True, dest="operation")
    hash_p.add_argument("--args", default="{}", help="JSON object of args")
    hash_p.add_argument("--region", default="")
    hash_p.add_argument(
        "--resource-ids", default="[]",
        help="JSON array of resource ids",
    )

    args = parser.parse_args(argv)
    if args.cmd == "hash":
        try:
            plan_args = json.loads(args.args)
            resource_ids = json.loads(args.resource_ids)
        except json.JSONDecodeError as exc:
            sys.stderr.write(f"error: invalid JSON: {exc}\n")
            return 2
        if not isinstance(plan_args, dict):
            sys.stderr.write("error: --args must be a JSON object\n")
            return 2
        if not isinstance(resource_ids, list):
            sys.stderr.write("error: --resource-ids must be a JSON array\n")
            return 2
        plan = make_plan(
            skill=args.skill,
            operation=args.operation,
            args=plan_args,
            region=args.region,
            resource_ids=resource_ids,
        )
        sys.stdout.write(plan.plan_hash + "\n")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
