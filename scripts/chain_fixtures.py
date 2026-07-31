#!/usr/bin/env python3
"""M3 C3 chain fixtures — ELB / RDS+Route53 / ECS+ELB.

Builds ExecutionDAGs and simulates three modes per chain (no live AWS):

- ``success`` — topo walk; shadow each node; stub ALLOW
- ``node_fail`` — fail primary; ``run_compensation`` (ALLOW stub) → COMPENSATED|MANUAL|HALT
- ``comp_fail`` — fail primary; compensation proxy BLOCKs → BLOCKED

CLI::

    python3 scripts/chain_fixtures.py list
    python3 scripts/chain_fixtures.py run --all
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal

from compensation_runner import run_compensation
from execution_dag import ExecutionDAG, make_dag, make_node, topological_order
from execution_plan import make_plan
from shadow_exec import run_shadow

REPO = Path(__file__).resolve().parents[1]
_REGION = "us-east-1"

ChainMode = Literal["success", "node_fail", "comp_fail"]
ChainStatus = Literal[
    "PASS", "COMPENSATED", "BLOCKED", "MANUAL", "HALT", "NODE_FAIL", "ERROR",
]

ProxyRunner = Callable[..., dict[str, Any]]

_COMP_STATUS: dict[str, ChainStatus] = {
    "COMPENSATED": "COMPENSATED",
    "BLOCKED": "BLOCKED",
    "MANUAL": "MANUAL",
    "HALT": "HALT",
    "COMPENSATION_FAIL": "ERROR",
}


@dataclass
class ChainSpec:
    """One pilot chain + which node fails in failure modes."""

    id: str
    description: str
    dag: ExecutionDAG
    fail_node_id: str
    expect_on_node_fail: ChainStatus  # ALLOW-stub compensation outcome
    expect_on_comp_fail: ChainStatus  # BLOCK-stub compensation outcome


@dataclass
class ChainRunResult:
    chain_id: str
    mode: ChainMode
    status: ChainStatus
    dag_hash: str
    order: list[str] = field(default_factory=list)
    compensate: dict[str, Any] | None = None
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _stub_proxy(decision: str, payload: dict[str, Any] | None = None, **_kw: Any) -> dict[str, Any]:
    out: dict[str, Any] = {
        "decision": decision,
        "executed": False,
        "plan_hash": (payload or {}).get("plan_hash"),
    }
    if decision == "ALLOW":
        out["would_execute"] = True
    else:
        out["reason"] = "fixture compensation block"
    return out


def _allow(payload: dict[str, Any] | None = None, **kw: Any) -> dict[str, Any]:
    return _stub_proxy("ALLOW", payload, **kw)


def _block(payload: dict[str, Any] | None = None, **kw: Any) -> dict[str, Any]:
    return _stub_proxy("BLOCK", payload, **kw)


def _plan(
    skill: str,
    operation: str,
    argv: list[str],
    *,
    resource_ids: list[str] | None = None,
    risk: str = "write",
):
    return make_plan(
        skill,
        operation,
        args={"argv": argv},
        region=_REGION,
        resource_ids=resource_ids,
        risk=risk,
    )


# --- Builders (ADR pilot chains) ---

_TG_APP = "arn:aws:elasticloadbalancing:us-east-1:1:targetgroup/app/abc"
_TG_API = "arn:aws:elasticloadbalancing:us-east-1:1:targetgroup/api/xyz"


def build_elb_target_remediation() -> ChainSpec:
    dereg = make_node(
        "deregister",
        plan=_plan(
            "aws-elb-ops",
            "elbv2 deregister-targets",
            ["--target-group-arn", _TG_APP, "--targets", "Id=i-unhealthy1"],
            resource_ids=["i-unhealthy1"],
            risk="destructive",
        ),
        on_fail="compensate",
        compensation="reregister",
        precondition=["target unhealthy"],
        postcondition=["target draining"],
    )
    rereg = make_node(
        "reregister",
        plan=_plan(
            "aws-elb-ops",
            "elbv2 register-targets",
            ["--target-group-arn", _TG_APP, "--targets", "Id=i-unhealthy1"],
            resource_ids=["i-unhealthy1"],
        ),
        on_fail="halt",
        postcondition=["target healthy"],
    )
    return ChainSpec(
        id="elb-target-remediation",
        description="deregister unhealthy → compensate re-register",
        dag=make_dag([dereg, rereg], edges=[("deregister", "reregister")]),
        fail_node_id="deregister",
        expect_on_node_fail="COMPENSATED",
        expect_on_comp_fail="BLOCKED",
    )


def build_rds_route53() -> ChainSpec:
    failover = make_node(
        "rds-failover",
        plan=_plan(
            "aws-rds-ops",
            "rds failover-db-cluster",
            ["--db-cluster-identifier", "prod-aurora"],
            resource_ids=["prod-aurora"],
            risk="destructive",
        ),
        on_fail="halt",
        precondition=["cluster multi-AZ"],
        postcondition=["writer flipped"],
    )
    # DNS cutover is non_compensable → MANUAL on failure (ADR exit criterion).
    dns = make_node(
        "dns-cutover",
        plan=_plan(
            "aws-route53-ops",
            "route53 change-resource-record-sets",
            ["--hosted-zone-id", "Z001", "--change-batch", "file://cutover.json"],
            resource_ids=["Z001", "db.example.com"],
            risk="destructive",
        ),
        on_fail="compensate",
        compensation="dns-rollback",
        non_compensable=True,
        precondition=["failover complete"],
        postcondition=["DNS points to new writer"],
    )
    rollback = make_node(
        "dns-rollback",
        plan=_plan(
            "aws-route53-ops",
            "route53 change-resource-record-sets",
            ["--hosted-zone-id", "Z001", "--change-batch", "file://rollback.json"],
            resource_ids=["Z001"],
            risk="destructive",
        ),
        on_fail="halt",
    )
    return ChainSpec(
        id="rds-failover-route53",
        description="RDS failover → DNS cutover (non_compensable MANUAL)",
        dag=make_dag([failover, dns, rollback], edges=[("rds-failover", "dns-cutover")]),
        fail_node_id="dns-cutover",
        expect_on_node_fail="MANUAL",
        expect_on_comp_fail="MANUAL",  # never reaches proxy when non_compensable
    )


def build_ecs_elb_health() -> ChainSpec:
    update = make_node(
        "ecs-update",
        plan=_plan(
            "aws-ecs-ops",
            "ecs update-service",
            ["--cluster", "prod", "--service", "api", "--task-definition", "api:42"],
            resource_ids=["api", "api:42"],
        ),
        on_fail="compensate",
        compensation="ecs-rollback",
        precondition=["task def registered"],
        postcondition=["deployment started"],
    )
    health = make_node(
        "elb-health-wait",
        plan=_plan(
            "aws-elb-ops",
            "elbv2 describe-target-health",
            ["--target-group-arn", _TG_API],
            risk="read-only",
        ),
        on_fail="halt",
        postcondition=["all targets healthy"],
    )
    rollback = make_node(
        "ecs-rollback",
        plan=_plan(
            "aws-ecs-ops",
            "ecs update-service",
            ["--cluster", "prod", "--service", "api", "--task-definition", "api:41"],
            resource_ids=["api", "api:41"],
        ),
        on_fail="halt",
    )
    return ChainSpec(
        id="ecs-deploy-elb-health",
        description="ECS update → ELB health; compensate rollback task def",
        dag=make_dag([update, health, rollback], edges=[("ecs-update", "elb-health-wait")]),
        fail_node_id="ecs-update",
        expect_on_node_fail="COMPENSATED",
        expect_on_comp_fail="BLOCKED",
    )


def all_chain_specs() -> list[ChainSpec]:
    return [
        build_elb_target_remediation(),
        build_rds_route53(),
        build_ecs_elb_health(),
    ]


# --- Simulator ---


def _shadow_all_nodes(dag: ExecutionDAG, shadow_dir: Path) -> list[str]:
    """Persist simulate shadows for every node with a plan; return errors."""
    errors: list[str] = []
    for nid in topological_order(dag):
        node = dag.nodes[nid]
        if node.plan is None:
            continue
        result = run_shadow(node.plan, mode="simulate", audit_dir=shadow_dir, persist=True)
        if not result.ok:
            errors.append(f"{nid}: {result.error}")
    return errors


def run_chain(
    spec: ChainSpec,
    mode: ChainMode,
    *,
    shadow_dir: Path,
) -> ChainRunResult:
    """Simulate one chain × mode. No live AWS."""
    dag = spec.dag
    base = ChainRunResult(
        chain_id=spec.id,
        mode=mode,
        status="ERROR",
        dag_hash=dag.dag_hash,
        order=topological_order(dag),
    )

    errs = _shadow_all_nodes(dag, shadow_dir)
    if errs:
        base.reason = "; ".join(errs)
        return base

    if mode == "success":
        base.status = "PASS"
        base.reason = "topo walk + shadow ok (stub execution)"
        return base

    runner: ProxyRunner = _allow if mode == "node_fail" else _block
    comp = run_compensation(
        dag, spec.fail_node_id, shadow_dir=shadow_dir, proxy_runner=runner,
    )
    base.compensate = comp.to_dict()
    base.status = _COMP_STATUS.get(comp.status, "ERROR")
    base.reason = comp.reason
    return base


def run_all_modes(
    specs: list[ChainSpec] | None = None,
    *,
    shadow_root: Path,
) -> list[ChainRunResult]:
    specs = specs or all_chain_specs()
    results: list[ChainRunResult] = []
    for spec in specs:
        for mode in ("success", "node_fail", "comp_fail"):
            shadow_dir = shadow_root / spec.id / mode
            results.append(run_chain(spec, mode, shadow_dir=shadow_dir))  # type: ignore[arg-type]
    return results


def compensation_recovery_rate(results: list[ChainRunResult]) -> float:
    """Among node_fail runs that expected COMPENSATED, fraction that got it.

    ADR: compensable failure auto-recovery ≥90% (fixture metric).
    """
    specs = {s.id: s for s in all_chain_specs()}
    eligible = [
        r for r in results
        if r.mode == "node_fail" and specs[r.chain_id].expect_on_node_fail == "COMPENSATED"
    ]
    if not eligible:
        return 1.0
    return sum(1 for r in eligible if r.status == "COMPENSATED") / len(eligible)


def manual_non_compensable_ok(results: list[ChainRunResult]) -> bool:
    """All node_fail/comp_fail on chains expecting MANUAL must be MANUAL."""
    specs = {s.id: s for s in all_chain_specs()}
    for r in results:
        if r.mode not in ("node_fail", "comp_fail"):
            continue
        if specs[r.chain_id].expect_on_node_fail != "MANUAL":
            continue
        if r.status != "MANUAL":
            return False
    return True


def _expected_status(spec: ChainSpec, mode: ChainMode) -> ChainStatus | None:
    if mode == "success":
        return "PASS"
    if mode == "node_fail":
        return spec.expect_on_node_fail
    if mode == "comp_fail":
        return spec.expect_on_comp_fail
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="chain_fixtures")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="Print chain ids")
    run_p = sub.add_parser("run", help="Run all chain×mode fixtures")
    run_p.add_argument("--all", action="store_true", required=True)
    run_p.add_argument(
        "--shadow-root",
        default=str(REPO / "audit-results" / "chains"),
    )
    run_p.add_argument("--out", default="")
    args = ap.parse_args(argv)

    if args.cmd == "list":
        for s in all_chain_specs():
            print(f"{s.id}\t{s.description}\tdag_hash={s.dag.dag_hash[:16]}…")
        return 0

    if args.cmd == "run":
        results = run_all_modes(shadow_root=Path(args.shadow_root))
        rate = compensation_recovery_rate(results)
        payload = {
            "results": [r.to_dict() for r in results],
            "compensation_recovery_rate": rate,
            "manual_non_compensable_ok": manual_non_compensable_ok(results),
            "count": len(results),
        }
        text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
        if args.out:
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8")
            print(f"saved: {out}")
        else:
            sys.stdout.write(text)
        specs = {s.id: s for s in all_chain_specs()}
        mismatches = [
            r for r in results
            if r.status != _expected_status(specs[r.chain_id], r.mode)
        ]
        if mismatches or rate < 0.9 or not payload["manual_non_compensable_ok"]:
            print(
                f"FAIL: mismatches={len(mismatches)} rate={rate:.0%} "
                f"manual_ok={payload['manual_non_compensable_ok']}",
                file=sys.stderr,
            )
            return 1
        print(f"OK: {len(results)} runs rate={rate:.0%}")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
