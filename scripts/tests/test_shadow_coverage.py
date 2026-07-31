"""Tests for scripts/shadow_coverage.py — ADR-0001 M2 Wave 4.

No live AWS. Coverage uses local simulate shadows only.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from execution_plan import make_plan  # noqa: E402
from runtime_safety import (  # noqa: E402
    ToolCall,
    build_plan_bound_token,
    check_tool_call,
)
from shadow_coverage import (  # noqa: E402
    check_destructive_shadow_coverage,
    false_block_rate,
    iter_destructive_scenarios,
    plan_from_scenario,
)
from shadow_exec import run_shadow  # noqa: E402


def test_all_high_risk_destructive_get_shadow_evidence(tmp_path: Path) -> None:
    report = check_destructive_shadow_coverage(shadow_dir=tmp_path / "shadow")
    assert report.destructive_total > 0
    assert report.covered == report.destructive_total
    assert not report.failed
    for row in report.results:
        assert row.plan_hash
        assert row.ok is True
        assert row.path is not None
        assert Path(row.path).exists()


def test_cli_check_all_high_risk(tmp_path: Path) -> None:
    out = tmp_path / "coverage.json"
    shadow = tmp_path / "shadow-m2"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "shadow_coverage.py"),
            "check",
            "--all-high-risk",
            "--shadow-dir",
            str(shadow),
            "--out",
            str(out),
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert out.exists()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["covered"] == payload["destructive_total"]
    assert payload["destructive_total"] >= 20  # 5 skills, multi destructive each


def test_drift_region_or_resource_blocks_via_token_mismatch() -> None:
    plan = make_plan(
        "aws-ec2-ops",
        "ec2 terminate-instances",
        args={"instance_ids": ["i-aaa"]},
        region="us-east-1",
        resource_ids=["i-aaa"],
        risk="destructive",
    )
    call_ok = ToolCall(
        tool_name="aws ec2 terminate-instances",
        args={"instance_ids": ["i-aaa"], "region": "us-east-1"},
        plan_hash=plan.plan_hash,
    )
    token = build_plan_bound_token(call_ok, plan.plan_hash)

    drifted = ToolCall(
        tool_name="aws ec2 terminate-instances",
        args={"instance_ids": ["i-bbb"], "region": "us-west-2"},
        plan_hash=plan.plan_hash,
        safety_confirm=token,  # token bound to original call → mismatch
    )
    result = check_tool_call(drifted, patterns=[])
    assert result.decision == "BLOCK"


def test_confirmed_plan_bound_path_allows() -> None:
    plan = make_plan(
        "aws-ec2-ops",
        "ec2 terminate-instances",
        args={"instance_ids": ["i-happy"]},
        region="us-east-1",
        resource_ids=["i-happy"],
        risk="destructive",
    )
    call = ToolCall(
        tool_name="aws ec2 terminate-instances",
        args={"instance_ids": ["i-happy"], "region": "us-east-1"},
        plan_hash=plan.plan_hash,
    )
    call.safety_confirm = build_plan_bound_token(call, plan.plan_hash)
    result = check_tool_call(call, patterns=[])
    assert result.decision == "ALLOW"


def test_redaction_no_plaintext_secret_access_key_in_shadow_json(tmp_path: Path) -> None:
    plan = make_plan(
        "aws-iam-ops",
        "iam create-access-key",
        args={"user": "alice"},
        region="us-east-1",
        risk="destructive",
        expected_diff={
            "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "AccessKeyId": "AKIAEXAMPLE",
        },
    )
    result = run_shadow(plan, mode="simulate", audit_dir=tmp_path, persist=True)
    assert result.ok
    assert result.path is not None
    raw = Path(result.path).read_text(encoding="utf-8")
    assert "wJalrXUtnFEMI" not in raw
    assert "SecretAccessKey" in raw
    loaded = json.loads(raw)
    assert str(loaded["evidence"]["expected_diff"]["SecretAccessKey"]).startswith("***")


def test_false_block_fixture_zero_on_happy_confirmed_set() -> None:
    """Confirmed destructive with matching plan+token must ALLOW (≤0 false blocks)."""
    happy = [
        ("i-1", "us-east-1"),
        ("i-2", "us-east-1"),
        ("i-3", "eu-west-1"),
    ]
    blocked_but_should_allow = 0
    for rid, region in happy:
        plan = make_plan(
            "aws-ec2-ops",
            "ec2 terminate-instances",
            args={"instance_ids": [rid], "region": region},
            region=region,
            resource_ids=[rid],
            risk="destructive",
        )
        call = ToolCall(
            tool_name="aws ec2 terminate-instances",
            args={"instance_ids": [rid], "region": region},
            plan_hash=plan.plan_hash,
        )
        call.safety_confirm = build_plan_bound_token(call, plan.plan_hash)
        decision = check_tool_call(call, patterns=[]).decision
        if decision != "ALLOW":
            blocked_but_should_allow += 1
    rate = false_block_rate(blocked_but_should_allow, len(happy))
    assert blocked_but_should_allow == 0
    assert rate == 0.0


def test_iter_destructive_matches_risk_field() -> None:
    rows = iter_destructive_scenarios()
    assert len(rows) >= 20
    assert all(s.risk.lower() == "destructive" for _, s in rows)
    skills = {skill for skill, _ in rows}
    assert skills == {
        "aws-ec2-ops",
        "aws-s3-ops",
        "aws-iam-ops",
        "aws-rds-ops",
        "aws-kms-ops",
    }
    skill, scn = rows[0]
    plan = plan_from_scenario(skill, scn)
    assert plan.plan_hash
    assert plan.risk == "destructive"
