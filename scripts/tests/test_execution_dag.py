"""Tests for scripts/execution_dag.py — ADR-0001 M3 Wave C1."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from execution_dag import (  # noqa: E402
    ExecutionDAG,
    compute_dag_hash,
    make_dag,
    make_node,
    resolve_fail_policy,
    topological_order,
    validate_dag,
)
from execution_plan import make_plan  # noqa: E402


def _pair_nodes():
    a = make_node(
        "deregister",
        skill="aws-elb-ops",
        operation="elbv2 deregister-targets",
        on_fail="compensate",
        compensation="reregister",
    )
    b = make_node(
        "reregister",
        skill="aws-elb-ops",
        operation="elbv2 register-targets",
        on_fail="halt",
    )
    return a, b


def test_dag_hash_stable_and_edge_order_independent():
    a, b = _pair_nodes()
    d1 = make_dag([a, b], edges=[("deregister", "reregister")])
    a2, b2 = _pair_nodes()
    d2 = make_dag([b2, a2], edges=[("deregister", "reregister")])
    assert d1.dag_hash == d2.dag_hash
    assert d1.dag_hash == compute_dag_hash(d1)


def test_dag_hash_changes_when_plan_args_change():
    a, b = _pair_nodes()
    d1 = make_dag([a, b], edges=[("deregister", "reregister")])
    a3 = make_node(
        "deregister",
        plan=make_plan(
            "aws-elb-ops",
            "elbv2 deregister-targets",
            args={"TargetGroupArn": "arn:aws:elasticloadbalancing:…:tg/other"},
        ),
        on_fail="compensate",
        compensation="reregister",
    )
    b3 = make_node(
        "reregister",
        skill="aws-elb-ops",
        operation="elbv2 register-targets",
    )
    d2 = make_dag([a3, b3], edges=[("deregister", "reregister")])
    assert d1.dag_hash != d2.dag_hash


def test_topological_order_respects_edges():
    a, b = _pair_nodes()
    c = make_node("verify", skill="aws-elb-ops", operation="elbv2 describe-target-health")
    dag = make_dag(
        [a, b, c],
        edges=[("deregister", "reregister"), ("reregister", "verify")],
    )
    assert topological_order(dag) == ["deregister", "reregister", "verify"]


def test_cycle_rejected():
    a = make_node("x", skill="aws-ec2-ops", operation="ec2 describe-instances")
    b = make_node("y", skill="aws-ec2-ops", operation="ec2 describe-instances")
    try:
        make_dag([a, b], edges=[("x", "y"), ("y", "x")])
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "cycle" in str(exc).lower() or "invalid" in str(exc).lower()


def test_compensate_requires_compensation_target():
    a = make_node(
        "n1",
        skill="aws-rds-ops",
        operation="rds failover-db-cluster",
        on_fail="compensate",
        compensation=None,
    )
    errors = validate_dag(ExecutionDAG(nodes={"n1": a}, edges=[]))
    assert any("compensation" in e for e in errors)


def test_non_compensable_forces_manual():
    n = make_node(
        "cutover",
        skill="aws-route53-ops",
        operation="route53 change-resource-record-sets",
        on_fail="compensate",
        compensation="rollback-dns",
        non_compensable=True,
    )
    assert resolve_fail_policy(n) == "manual"
    assert n.effective_on_fail() == "manual"


def test_self_check_cli():
    r = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "execution_dag.py"), "self-check"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    assert "dag_hash" in r.stdout
