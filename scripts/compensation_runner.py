#!/usr/bin/env python3
"""Compensation runner — ADR-0001 M3 Wave C2.

On node failure, resolve fail policy and (when ``compensate``) execute the
compensation node through the **same** gates as primary mutation:

    run_shadow → plan-bound token (if destructive) → safe_tool_proxy

No gate bypass. ``non_compensable`` → MANUAL (no mutate). Unit tests inject
``proxy_runner`` / use proxy ``--dry-run``; no live AWS required.
"""
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Literal

from execution_dag import ExecutionDAG, ExecutionNode, resolve_fail_policy
from execution_plan import ExecutionPlan, compute_plan_hash
from runtime_safety import ToolCall, build_plan_bound_token, detect_destructive
from shadow_exec import run_shadow

REPO = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent

CompensateStatus = Literal[
    "COMPENSATED",
    "BLOCKED",
    "MANUAL",
    "HALT",
    "COMPENSATION_FAIL",
]

ProxyRunner = Callable[..., dict[str, Any]]


@dataclass
class CompensateResult:
    status: CompensateStatus
    failed_node_id: str
    compensation_node_id: str | None = None
    plan_hash: str | None = None
    shadow_path: str | None = None
    proxy: dict[str, Any] | None = None
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def plan_to_aws_command(plan: ExecutionPlan) -> list[str]:
    """Build ``aws <svc> <op> …`` argv from an ExecutionPlan."""
    op = (plan.operation or "").strip()
    if op.lower().startswith("aws "):
        parts = op.split()
    else:
        parts = ["aws", *op.split()] if op else ["aws"]
    argv = plan.args.get("argv") if isinstance(plan.args, dict) else None
    if isinstance(argv, list) and all(isinstance(x, str) for x in argv):
        return [*parts, *argv]
    # Fallback: flatten simple string args (no nested structures).
    extra: list[str] = []
    if isinstance(plan.args, dict):
        for key, val in sorted(plan.args.items()):
            if key in ("argv", "scenario_id", "request"):
                continue
            if isinstance(val, str):
                extra.extend([f"--{key.replace('_', '-')}", val])
    if plan.region and "--region" not in extra:
        extra.extend(["--region", plan.region])
    return [*parts, *extra]


def _ensure_plan(node: ExecutionNode) -> ExecutionPlan:
    if node.plan is None:
        raise ValueError(f"node {node.id!r} has no ExecutionPlan")
    if not node.plan.plan_hash:
        node.plan.plan_hash = compute_plan_hash(node.plan)
    return node.plan


def _default_proxy_runner(
    payload: dict[str, Any],
    *,
    shadow_dir: Path,
    patterns: str,
    dry_run: bool,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "safe_tool_proxy.py"),
        "--patterns",
        patterns,
        "--shadow-dir",
        str(shadow_dir),
    ]
    if dry_run:
        cmd.append("--dry-run")
    completed = subprocess.run(
        cmd,
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        env=env,
        cwd=str(REPO),
    )
    try:
        out = json.loads(completed.stdout.strip() or "{}")
    except json.JSONDecodeError:
        out = {
            "decision": "BLOCK",
            "executed": False,
            "reason": f"invalid proxy stdout: {completed.stdout[:200]!r}",
        }
    out["_exit_code"] = completed.returncode
    return out


def run_compensation(
    dag: ExecutionDAG,
    failed_node_id: str,
    *,
    shadow_dir: Path,
    patterns: str = "/dev/null",
    dry_run: bool = True,
    proxy_runner: ProxyRunner | None = None,
    env: dict[str, str] | None = None,
) -> CompensateResult:
    """Execute compensation for ``failed_node_id`` under M2 gates.

    Returns COMPENSATED only when proxy decision is ALLOW (dry-run counts).
    """
    if failed_node_id not in dag.nodes:
        return CompensateResult(
            status="COMPENSATION_FAIL",
            failed_node_id=failed_node_id,
            reason=f"unknown failed node {failed_node_id!r}",
        )

    failed = dag.nodes[failed_node_id]
    policy = resolve_fail_policy(failed)

    if policy == "manual":
        return CompensateResult(
            status="MANUAL",
            failed_node_id=failed_node_id,
            reason="non_compensable or on_fail=manual; halt before mutate",
        )
    if policy == "halt":
        return CompensateResult(
            status="HALT",
            failed_node_id=failed_node_id,
            reason="on_fail=halt; no compensation invoked",
        )
    if policy != "compensate":
        return CompensateResult(
            status="COMPENSATION_FAIL",
            failed_node_id=failed_node_id,
            reason=f"unsupported policy {policy!r}",
        )

    comp_id = failed.compensation
    if not comp_id or comp_id not in dag.nodes:
        return CompensateResult(
            status="COMPENSATION_FAIL",
            failed_node_id=failed_node_id,
            reason="compensation target missing",
        )

    comp_node = dag.nodes[comp_id]
    try:
        plan = _ensure_plan(comp_node)
    except ValueError as exc:
        return CompensateResult(
            status="COMPENSATION_FAIL",
            failed_node_id=failed_node_id,
            compensation_node_id=comp_id,
            reason=str(exc),
        )

    # Always shadow first — compensation must not skip evidence (spec §5).
    shadow = run_shadow(
        plan,
        mode="simulate",
        audit_dir=shadow_dir,
        persist=True,
    )
    if not shadow.ok:
        return CompensateResult(
            status="BLOCKED",
            failed_node_id=failed_node_id,
            compensation_node_id=comp_id,
            plan_hash=plan.plan_hash,
            shadow_path=shadow.path,
            reason=f"shadow failed: {shadow.error}",
        )

    command = plan_to_aws_command(plan)
    tool_name = " ".join(command[:3]) if len(command) >= 3 else " ".join(command)
    call_args = {"argv": command[3:]}
    payload: dict[str, Any] = {
        "command": command,
        "args": call_args,
        "plan_hash": plan.plan_hash,  # always — audit trail even if non-destructive
    }
    if detect_destructive(tool_name):
        call = ToolCall(tool_name=tool_name, args=call_args, plan_hash=plan.plan_hash)
        payload["safety_confirm"] = build_plan_bound_token(call, plan.plan_hash)

    runner = proxy_runner or _default_proxy_runner
    proxy_out = runner(
        payload,
        shadow_dir=shadow_dir,
        patterns=patterns,
        dry_run=dry_run,
        env=env,
    )
    decision = str(proxy_out.get("decision") or "BLOCK")
    allowed = decision == "ALLOW"
    return CompensateResult(
        status="COMPENSATED" if allowed else "BLOCKED",
        failed_node_id=failed_node_id,
        compensation_node_id=comp_id,
        plan_hash=plan.plan_hash,
        shadow_path=shadow.path,
        proxy=proxy_out,
        reason=(
            "compensation ALLOW via safe_tool_proxy"
            if allowed
            else str(proxy_out.get("reason") or f"proxy decision={decision}")
        ),
    )


def main(argv: list[str] | None = None) -> int:
    import argparse

    from execution_dag import make_dag, make_node
    from execution_plan import make_plan

    ap = argparse.ArgumentParser(prog="compensation_runner")
    ap.add_argument("--self-check", action="store_true")
    args = ap.parse_args(argv)
    if not args.self_check:
        ap.error("use --self-check")
        return 2

    shadow_dir = REPO / "audit-results" / "shadow-c2-selfcheck"
    primary = make_node(
        "deregister",
        plan=make_plan(
            "aws-elb-ops",
            "elbv2 deregister-targets",
            args={"argv": ["--target-group-arn", "arn:aws:elasticloadbalancing:us-east-1:1:targetgroup/tg/abc"]},
            region="us-east-1",
            risk="destructive",
        ),
        on_fail="compensate",
        compensation="reregister",
    )
    comp = make_node(
        "reregister",
        plan=make_plan(
            "aws-elb-ops",
            "elbv2 register-targets",
            args={"argv": ["--target-group-arn", "arn:aws:elasticloadbalancing:us-east-1:1:targetgroup/tg/abc"]},
            region="us-east-1",
            risk="write",
        ),
        on_fail="halt",
    )
    dag = make_dag([primary, comp], edges=[("deregister", "reregister")])
    # Self-check uses injectable allow stub (no trusted aws required).
    result = run_compensation(
        dag,
        "deregister",
        shadow_dir=shadow_dir,
        proxy_runner=lambda payload, **kw: {
            "decision": "ALLOW",
            "executed": False,
            "would_execute": True,
            "plan_hash": payload.get("plan_hash"),
        },
    )
    sys.stdout.write(json.dumps(result.to_dict(), indent=2) + "\n")
    return 0 if result.status == "COMPENSATED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
