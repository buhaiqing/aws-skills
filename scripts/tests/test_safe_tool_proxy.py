from __future__ import annotations

import json
import os
import subprocess
import sys

from runtime_safety import ToolCall, build_confirmation_token


def run_proxy(
    payload: dict, dry_run: bool = False, env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, "scripts/safe_tool_proxy.py", "--patterns", "/dev/null"]
    if dry_run:
        command.append("--dry-run")
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


def test_proxy_executes_destructive_plan_only_with_exact_confirmation(tmp_path):
    command = [
        "aws", "ec2", "terminate-instances", "--instance-ids", "i-123",
        "--region", "us-east-1",
    ]
    args = {"argv": command[3:]}
    call = ToolCall(
        tool_name="aws ec2 terminate-instances",
        args=args,
    )
    result = run_proxy({
        "command": command,
        "safety_confirm": build_confirmation_token(call),
    }, dry_run=True, env=fake_aws_env(tmp_path))

    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output["decision"] == "ALLOW"
    assert output["executed"] is False
    assert output["would_execute"] is True


def test_proxy_binds_confirmation_to_actual_command_arguments(tmp_path):
    approved = ["--instance-ids", "i-123", "--region", "us-east-1"]
    call = ToolCall(tool_name="aws ec2 terminate-instances", args={"argv": approved})
    result = run_proxy({
        "command": [
            "aws", "ec2", "terminate-instances", "--instance-ids", "i-999",
            "--region", "us-east-1",
        ],
        "safety_confirm": build_confirmation_token(call),
    }, dry_run=True, env=fake_aws_env(tmp_path))

    assert result.returncode == 1
    assert json.loads(result.stdout)["executed"] is False
