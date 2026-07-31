"""TDD tests for scripts/execution_plan.py — ADR-0001 M2 Wave 1."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from execution_plan import (  # noqa: E402
    ExecutionPlan,
    assert_plan_matches_call,
    compute_plan_hash,
    detect_plan_drift,
    make_plan,
)


def test_same_plan_same_hash():
    p1 = ExecutionPlan(
        skill="aws-ec2-ops",
        operation="ec2 terminate-instances",
        args={"instance_ids": ["i-abc"]},
        region="us-east-1",
    )
    p2 = ExecutionPlan(
        skill="aws-ec2-ops",
        operation="ec2 terminate-instances",
        args={"instance_ids": ["i-abc"]},
        region="us-east-1",
    )
    assert compute_plan_hash(p1) == compute_plan_hash(p2)


def test_key_order_change_same_hash():
    a = ExecutionPlan(
        skill="aws-s3-ops",
        operation="s3 delete-object",
        args={"Bucket": "b", "Key": "k"},
    )
    b = ExecutionPlan(
        skill="aws-s3-ops",
        operation="s3 delete-object",
        args={"Key": "k", "Bucket": "b"},
    )
    assert compute_plan_hash(a) == compute_plan_hash(b)


def test_arg_value_change_different_hash():
    base = ExecutionPlan(
        skill="aws-ec2-ops",
        operation="ec2 terminate-instances",
        args={"instance_ids": ["i-aaa"]},
    )
    changed = ExecutionPlan(
        skill="aws-ec2-ops",
        operation="ec2 terminate-instances",
        args={"instance_ids": ["i-bbb"]},
    )
    assert compute_plan_hash(base) != compute_plan_hash(changed)


def test_detect_plan_drift_false_when_match():
    plan = make_plan(
        skill="aws-iam-ops",
        operation="iam delete-user",
        args={"UserName": "alice"},
        region="us-west-2",
    )
    assert detect_plan_drift(plan.plan_hash, plan) is False
    assert detect_plan_drift(
        plan.plan_hash,
        {
            "skill": "aws-iam-ops",
            "operation": "iam delete-user",
            "args": {"UserName": "alice"},
            "region": "us-west-2",
        },
    ) is False


@pytest.mark.parametrize(
    "kwargs,drifted",
    [
        (
            {"skill": "aws-rds-ops", "operation": "rds delete-db-instance",
             "args": {"DBInstanceIdentifier": "prod-db"}},
            {"skill": "aws-rds-ops", "operation": "rds delete-db-instance",
             "args": {"DBInstanceIdentifier": "other-db"}},
        ),
        (
            {"skill": "aws-ec2-ops", "operation": "ec2 terminate-instances",
             "args": {"instance_ids": ["i-1"]}, "region": "us-east-1"},
            {"skill": "aws-ec2-ops", "operation": "ec2 terminate-instances",
             "args": {"instance_ids": ["i-1"]}, "region": "eu-west-1"},
        ),
        (
            {"skill": "aws-kms-ops", "operation": "kms schedule-key-deletion",
             "args": {}, "resource_ids": ["key-aaa"]},
            {"skill": "aws-kms-ops", "operation": "kms schedule-key-deletion",
             "args": {}, "resource_ids": ["key-bbb"]},
        ),
        (
            {"skill": "aws-ec2-ops", "operation": "ec2 terminate-instances",
             "args": {"instance_ids": ["i-1"]}},
            {"skill": "aws-ec2-ops", "operation": "ec2 stop-instances",
             "args": {"instance_ids": ["i-1"]}},
        ),
    ],
)
def test_detect_plan_drift_true_on_field_change(kwargs, drifted):
    plan = make_plan(**kwargs)
    assert detect_plan_drift(plan.plan_hash, drifted) is True


def test_assert_plan_matches_call_ok_and_raises():
    plan = make_plan(
        skill="aws-ec2-ops",
        operation="ec2 terminate-instances",
        args={"instance_ids": ["i-ok"]},
        region="ap-northeast-1",
    )
    assert_plan_matches_call(plan, plan)
    with pytest.raises(ValueError, match="plan drift"):
        assert_plan_matches_call(
            plan,
            {
                "skill": "aws-ec2-ops",
                "tool_name": "ec2 terminate-instances",
                "args": {"instance_ids": ["i-bad"]},
                "region": "ap-northeast-1",
            },
        )


def test_plan_hash_excluded_from_digest():
    """plan_hash / plan_id must not feed into the digest."""
    a = ExecutionPlan(skill="x", operation="y", args={}, plan_id="id-1", plan_hash="dead")
    b = ExecutionPlan(skill="x", operation="y", args={}, plan_id="id-2", plan_hash="beef")
    assert compute_plan_hash(a) == compute_plan_hash(b)


def test_cli_hash(tmp_path):
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "execution_plan.py"),
            "hash",
            "--skill", "aws-ec2-ops",
            "--op", "ec2 terminate-instances",
            "--args", '{"instance_ids":["i-xyz"]}',
            "--region", "us-east-1",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    digest = proc.stdout.strip()
    assert len(digest) == 64
    expected = compute_plan_hash(
        ExecutionPlan(
            skill="aws-ec2-ops",
            operation="ec2 terminate-instances",
            args={"instance_ids": ["i-xyz"]},
            region="us-east-1",
        )
    )
    assert digest == expected
