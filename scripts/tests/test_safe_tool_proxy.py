from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from execution_plan import make_plan
from runtime_safety import ToolCall, build_confirmation_token, build_plan_bound_token
from shadow_exec import run_shadow


def run_proxy(
    payload: dict,
    dry_run: bool = False,
    env: dict[str, str] | None = None,
    shadow_dir: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, "scripts/safe_tool_proxy.py", "--patterns", "/dev/null"]
    if dry_run:
        command.append("--dry-run")
    if shadow_dir is not None:
        command.extend(["--shadow-dir", str(shadow_dir)])
    return subprocess.run(
        command,
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def fake_aws_env(tmp_path) -> dict[str, str]:
    fake_aws = tmp_path / "aws"
    fake_aws.write_text("#!/bin/sh\nprintf 'ok\\n'\n")
    fake_aws.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{tmp_path}:{env.get('PATH', '')}"
    return env


def _destructive_fixture(tmp_path, instance_id: str = "i-123"):
    """Plan + simulate shadow + plan-bound token for terminate-instances."""
    shadow_dir = tmp_path / "shadow"
    plan = make_plan(
        "aws-ec2-ops",
        "ec2 terminate-instances",
        args={"argv": ["--instance-ids", instance_id, "--region", "us-east-1"]},
        region="us-east-1",
        resource_ids=[instance_id],
        risk="destructive",
    )
    run_shadow(plan, mode="simulate", audit_dir=shadow_dir, persist=True)
    command = [
        "aws", "ec2", "terminate-instances", "--instance-ids", instance_id,
        "--region", "us-east-1",
    ]
    call = ToolCall(
        tool_name="aws ec2 terminate-instances",
        args={"argv": command[3:]},
        plan_hash=plan.plan_hash,
    )
    token = build_plan_bound_token(call, plan.plan_hash)
    return plan, shadow_dir, command, call, token


def test_proxy_executes_read_only_aws_command(tmp_path):
    env = fake_aws_env(tmp_path)
    result = run_proxy({"command": ["aws", "s3api", "list-buckets"]}, env=env)

    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output["decision"] == "ALLOW"
    assert output["exit_code"] == 0
    assert output["stdout"] == "ok\n"


def test_proxy_blocks_non_aws_executable():
    result = run_proxy({"command": [sys.executable, "-c", "print('no')"]})

    assert result.returncode == 1
    output = json.loads(result.stdout)
    assert output["decision"] == "BLOCK"
    assert output["executed"] is False


def test_proxy_blocks_aws_lookalike_outside_trusted_path(tmp_path):
    fake_aws = tmp_path / "aws"
    fake_aws.write_text("#!/bin/sh\nprintf 'pwned\\n'\n")
    fake_aws.chmod(0o755)

    result = run_proxy({"command": [str(fake_aws), "s3api", "list-buckets"]})

    assert result.returncode == 1
    output = json.loads(result.stdout)
    assert output["decision"] == "BLOCK"
    assert output["executed"] is False


def test_proxy_blocks_destructive_command_without_exact_confirmation():
    result = run_proxy({
        "command": ["aws", "ec2", "terminate-instances", "--instance-ids", "i-123"],
        "safety_confirm": "random",
    })

    assert result.returncode == 1
    output = json.loads(result.stdout)
    assert output["decision"] == "BLOCK"
    assert output["executed"] is False


def test_proxy_blocks_destructive_without_plan_hash(tmp_path):
    """Legacy call-only token is insufficient for proxy destructive path (M2)."""
    command = [
        "aws", "ec2", "terminate-instances", "--instance-ids", "i-123",
        "--region", "us-east-1",
    ]
    call = ToolCall(tool_name="aws ec2 terminate-instances", args={"argv": command[3:]})
    result = run_proxy({
        "command": command,
        "safety_confirm": build_confirmation_token(call),
    }, dry_run=True, env=fake_aws_env(tmp_path), shadow_dir=tmp_path / "empty-shadow")

    assert result.returncode == 1
    output = json.loads(result.stdout)
    assert output["decision"] == "BLOCK"
    assert output["executed"] is False
    assert "plan_hash" in output["reason"]


def test_proxy_blocks_destructive_missing_shadow_evidence(tmp_path):
    plan, shadow_dir, command, call, token = _destructive_fixture(tmp_path)
    # Point at empty dir → evidence missing
    empty = tmp_path / "no-shadow"
    empty.mkdir()
    result = run_proxy({
        "command": command,
        "plan_hash": plan.plan_hash,
        "safety_confirm": token,
    }, dry_run=True, env=fake_aws_env(tmp_path), shadow_dir=empty)

    assert result.returncode == 1
    output = json.loads(result.stdout)
    assert output["decision"] == "BLOCK"
    assert "ShadowEvidence" in output["reason"]


def test_proxy_executes_destructive_with_plan_bound_token_and_shadow(tmp_path):
    plan, shadow_dir, command, call, token = _destructive_fixture(tmp_path)
    result = run_proxy({
        "command": command,
        "plan_hash": plan.plan_hash,
        "safety_confirm": token,
    }, dry_run=True, env=fake_aws_env(tmp_path), shadow_dir=shadow_dir)

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["decision"] == "ALLOW"
    assert output["executed"] is False
    assert output["would_execute"] is True


def test_proxy_blocks_plan_drift_on_resource_id(tmp_path):
    plan, shadow_dir, command, call, token = _destructive_fixture(tmp_path, "i-123")
    drifted = [
        "aws", "ec2", "terminate-instances", "--instance-ids", "i-999",
        "--region", "us-east-1",
    ]
    result = run_proxy({
        "command": drifted,
        "plan_hash": plan.plan_hash,
        "safety_confirm": token,  # bound to i-123 argv
    }, dry_run=True, env=fake_aws_env(tmp_path), shadow_dir=shadow_dir)

    assert result.returncode == 1
    assert json.loads(result.stdout)["executed"] is False


def test_proxy_blocks_plan_drift_on_region(tmp_path):
    plan, shadow_dir, command, call, token = _destructive_fixture(tmp_path, "i-123")
    drifted = [
        "aws", "ec2", "terminate-instances", "--instance-ids", "i-123",
        "--region", "eu-west-1",
    ]
    result = run_proxy({
        "command": drifted,
        "plan_hash": plan.plan_hash,
        "safety_confirm": token,  # bound to us-east-1 argv
    }, dry_run=True, env=fake_aws_env(tmp_path), shadow_dir=shadow_dir)

    assert result.returncode == 1
    assert json.loads(result.stdout)["executed"] is False


def test_proxy_blocks_legacy_token_even_with_shadow(tmp_path):
    plan, shadow_dir, command, call, _token = _destructive_fixture(tmp_path)
    legacy = build_confirmation_token(call)
    result = run_proxy({
        "command": command,
        "plan_hash": plan.plan_hash,
        "safety_confirm": legacy,
    }, dry_run=True, env=fake_aws_env(tmp_path), shadow_dir=shadow_dir)

    assert result.returncode == 1
    output = json.loads(result.stdout)
    assert output["decision"] == "BLOCK"
    assert output["executed"] is False
