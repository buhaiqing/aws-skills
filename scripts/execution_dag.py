#!/usr/bin/env python3
"""ExecutionDAG — ADR-0001 M3 Wave C1.

Declarative multi-node plans with fail policy. No AWS calls; C2 wires
compensation through shadow + safe_tool_proxy.

Standalone stdlib + ``execution_plan`` only (no circular imports with
runtime_safety / safe_tool_proxy).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

from execution_plan import ExecutionPlan, compute_plan_hash, make_plan

OnFail = Literal["compensate", "halt", "manual"]
VALID_ON_FAIL: frozenset[str] = frozenset({"compensate", "halt", "manual"})


@dataclass
class ExecutionNode:
    """One step in a transactional DAG (spec §3 ExecutionNode)."""

    id: str
    skill: str = ""
    operation: str = ""
    plan: ExecutionPlan | None = None
    precondition: list[str] = field(default_factory=list)
    postcondition: list[str] = field(default_factory=list)
    compensation: str | None = None  # node id | null (inline plan deferred to C2)
    non_compensable: bool = False
    on_fail: OnFail = "halt"

    def effective_on_fail(self) -> OnFail:
        """``non_compensable`` forces MANUAL before mutate (spec §5)."""
        if self.non_compensable:
            return "manual"
        return self.on_fail


@dataclass
class ExecutionDAG:
    """Cross-skill orchestration graph (spec §3 ExecutionDAG)."""

    dag_id: str = ""
    nodes: dict[str, ExecutionNode] = field(default_factory=dict)
    edges: list[tuple[str, str]] = field(default_factory=list)  # (from, to)
    verify: list[str] = field(default_factory=list)
    dag_hash: str = ""  # filled by compute_dag_hash; excluded from digest


def _node_canonical(node: ExecutionNode) -> dict[str, Any]:
    plan = node.plan
    plan_hash = ""
    if plan is not None:
        plan_hash = plan.plan_hash or compute_plan_hash(plan)
    return {
        "id": node.id.strip(),
        "skill": (node.skill or (plan.skill if plan else "")).strip().lower(),
        "operation": (node.operation or (plan.operation if plan else "")).strip().lower(),
        "plan_hash": plan_hash,
        "precondition": list(node.precondition or []),
        "postcondition": list(node.postcondition or []),
        "compensation": node.compensation,
        "non_compensable": bool(node.non_compensable),
        "on_fail": node.effective_on_fail(),
    }


def _canonical_dag_payload(dag: ExecutionDAG) -> dict[str, Any]:
    node_ids = sorted(dag.nodes.keys())
    edges = sorted((str(a), str(b)) for a, b in dag.edges)
    return {
        "nodes": [_node_canonical(dag.nodes[nid]) for nid in node_ids],
        "edges": [{"from": a, "to": b} for a, b in edges],
        "verify": list(dag.verify or []),
    }


def compute_dag_hash(dag: ExecutionDAG) -> str:
    """SHA256 hex over canonical nodes+edges (excludes dag_id / dag_hash)."""
    canonical = json.dumps(
        _canonical_dag_payload(dag),
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_dag(dag: ExecutionDAG) -> list[str]:
    """Return structural problems (empty = valid). Does not mutate."""
    errors: list[str] = []
    if not dag.nodes:
        errors.append("dag has no nodes")
        return errors

    for nid, node in dag.nodes.items():
        if not nid or not str(nid).strip():
            errors.append("empty node id")
        if node.id != nid:
            errors.append(f"node key {nid!r} != node.id {node.id!r}")
        if node.on_fail not in VALID_ON_FAIL:
            errors.append(f"node {nid}: invalid on_fail {node.on_fail!r}")
        if node.effective_on_fail() == "compensate":
            if not node.compensation:
                errors.append(f"node {nid}: on_fail=compensate requires compensation")
            elif node.compensation not in dag.nodes:
                errors.append(
                    f"node {nid}: compensation {node.compensation!r} not in dag"
                )

    known = set(dag.nodes)
    for a, b in dag.edges:
        if a not in known:
            errors.append(f"edge from unknown node {a!r}")
        if b not in known:
            errors.append(f"edge to unknown node {b!r}")

    try:
        topological_order(dag)
    except ValueError as exc:
        errors.append(str(exc))

    return errors


def topological_order(dag: ExecutionDAG) -> list[str]:
    """Kahn topological sort; raises ValueError on cycles or missing nodes."""
    indeg: dict[str, int] = {nid: 0 for nid in dag.nodes}
    adj: dict[str, list[str]] = {nid: [] for nid in dag.nodes}
    for a, b in dag.edges:
        if a not in indeg or b not in indeg:
            raise ValueError(f"edge references missing node: {(a, b)}")
        adj[a].append(b)
        indeg[b] += 1

    # Stable: process ready set in sorted id order.
    ready = sorted(nid for nid, d in indeg.items() if d == 0)
    order: list[str] = []
    while ready:
        nid = ready.pop(0)
        order.append(nid)
        for nxt in sorted(adj[nid]):
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                ready.append(nxt)
                ready.sort()

    if len(order) != len(dag.nodes):
        raise ValueError("dag contains a cycle")
    return order


def resolve_fail_policy(node: ExecutionNode) -> OnFail:
    """Public helper: effective fail policy for a node."""
    if node.on_fail not in VALID_ON_FAIL:
        raise ValueError(f"invalid on_fail {node.on_fail!r}")
    return node.effective_on_fail()


def make_node(
    node_id: str,
    *,
    skill: str = "",
    operation: str = "",
    plan: ExecutionPlan | None = None,
    precondition: list[str] | None = None,
    postcondition: list[str] | None = None,
    compensation: str | None = None,
    non_compensable: bool = False,
    on_fail: OnFail = "halt",
) -> ExecutionNode:
    if plan is None and skill and operation:
        plan = make_plan(skill, operation)
    elif plan is not None and not plan.plan_hash:
        plan.plan_hash = compute_plan_hash(plan)
    return ExecutionNode(
        id=node_id,
        skill=skill or (plan.skill if plan else ""),
        operation=operation or (plan.operation if plan else ""),
        plan=plan,
        precondition=list(precondition or []),
        postcondition=list(postcondition or []),
        compensation=compensation,
        non_compensable=non_compensable,
        on_fail=on_fail,
    )


def make_dag(
    nodes: list[ExecutionNode] | dict[str, ExecutionNode],
    edges: list[tuple[str, str]] | None = None,
    *,
    verify: list[str] | None = None,
    dag_id: str = "",
) -> ExecutionDAG:
    """Build DAG, validate, and set dag_hash / dag_id."""
    if isinstance(nodes, dict):
        node_map = dict(nodes)
    else:
        node_map = {n.id: n for n in nodes}
    dag = ExecutionDAG(
        dag_id=dag_id or str(uuid.uuid4()),
        nodes=node_map,
        edges=list(edges or []),
        verify=list(verify or []),
    )
    problems = validate_dag(dag)
    if problems:
        raise ValueError("invalid dag: " + "; ".join(problems))
    dag.dag_hash = compute_dag_hash(dag)
    return dag


def main(argv: list[str] | None = None) -> int:
    """CLI: ``hash`` demo with two linked nodes (fixture-style)."""
    parser = argparse.ArgumentParser(prog="execution_dag")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("self-check", help="Build a tiny DAG and print dag_hash")
    args = parser.parse_args(argv)

    if args.cmd == "self-check":
        n1 = make_node("a", skill="aws-elb-ops", operation="elbv2 deregister-targets")
        n2 = make_node(
            "b",
            skill="aws-elb-ops",
            operation="elbv2 register-targets",
            on_fail="halt",
        )
        n1.on_fail = "compensate"
        n1.compensation = "b"
        dag = make_dag([n1, n2], edges=[("a", "b")])
        sys.stdout.write(
            json.dumps(
                {
                    "dag_id": dag.dag_id,
                    "dag_hash": dag.dag_hash,
                    "order": topological_order(dag),
                },
                indent=2,
            )
            + "\n"
        )
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
