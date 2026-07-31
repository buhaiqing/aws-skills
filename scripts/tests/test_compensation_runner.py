"""Tests for scripts/compensation_runner.py — ADR-0001 M3 Wave C2."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from compensation_runner import (  # noqa: E402
    plan_to_aws_command,
    run_compensation,
)
from execution_dag import make_dag, make_node  # noqa: E402
from execution_plan import make_plan  # noqa: E402
from runtime_safety import ToolCall, build_plan_bound_token, detect_destructive  # noqa: E402


def _elb_dag(*, non_compensable: bool = False, on_fail: str = "compensate"):
    primary = make_node(
        "deregister",
        plan=make_plan(
            "aws-elb-ops",
            "elbv2 deregister-targets",
            args={
                "argv": [
                    "--target-group-arn",
                    "arn:aws:elasticloadbalancing:us-east-1:1:targetgroup/tg/abc",
                    "--targets",
                    "Id=i-abc",
                ],
            },
            region="us-east-1",
            resource_ids=["i-abc"],
            risk="destructive",
        ),
        on_fail=on_fail,  # type: ignore[arg-type]
        compensation="reregister",
        non_compensable=non_compensable,
    )
    comp = make_node(
        "reregister",
        plan=make_plan(
            "aws-elb-ops",
            "elbv2 register-targets",
            args={
                "argv": [
                    "--target-group-arn",
                    "arn:aws:elasticloadbalancing:us-east-1:1:targetgroup/tg/abc",
                    "--targets",
                    "Id=i-abc",
                ],
            },
            region="us-east-1",
            resource_ids=["i-abc"],
            risk="write",
        ),
        on_fail="halt",
    )
    return make_dag([primary, comp], edges=[("deregister", "reregister")])


def _allow_runner(payload, **_kw):
    return {
        "decision": "ALLOW",
        "executed": False,
        "would_execute": True,
        "plan_hash": payload.get("plan_hash"),
        "command": payload.get("command"),
    }


def _block_runner(payload, **_kw):
    return {
        "decision": "BLOCK",
        "executed": False,
        "reason": "injected block",
        "plan_hash": payload.get("plan_hash"),
    }


def test_plan_to_aws_command_uses_argv():
    plan = make_plan(
        "aws-ec2-ops",
        "ec2 terminate-instances",
        args={"argv": ["--instance-ids", "i-1"]},
        region="us-east-1",
    )
    assert plan_to_aws_command(plan) == [
        "aws", "ec2", "terminate-instances", "--instance-ids", "i-1",
    ]


def test_manual_when_non_compensable(tmp_path: Path):
    dag = _elb_dag(non_compensable=True)
    result = run_compensation(
        dag, "deregister", shadow_dir=tmp_path / "shadow", proxy_runner=_allow_runner,
    )
    assert result.status == "MANUAL"
    assert result.proxy is None


def test_halt_when_on_fail_halt(tmp_path: Path):
    dag = _elb_dag(on_fail="halt")
    # compensate target still present structurally via make_node default; override
    dag.nodes["deregister"].on_fail = "halt"
    dag.nodes["deregister"].compensation = None
    result = run_compensation(
        dag, "deregister", shadow_dir=tmp_path / "shadow", proxy_runner=_allow_runner,
    )
    assert result.status == "HALT"


def test_compensate_success_via_shadow_and_proxy(tmp_path: Path):
    dag = _elb_dag()
    shadow_dir = tmp_path / "shadow"
    calls: list[dict] = []

    def capturing_runner(payload, **kw):
        calls.append(payload)
        return _allow_runner(payload, **kw)

    result = run_compensation(
        dag, "deregister", shadow_dir=shadow_dir, proxy_runner=capturing_runner,
    )
    assert result.status == "COMPENSATED"
    assert result.compensation_node_id == "reregister"
    assert result.plan_hash
    assert result.shadow_path and Path(result.shadow_path).exists()
    assert calls, "proxy must be invoked (no gate bypass)"
    assert calls[0]["command"][0] == "aws"
    assert "register-targets" in calls[0]["command"]


def test_compensate_blocked_when_proxy_blocks(tmp_path: Path):
    dag = _elb_dag()
    result = run_compensation(
        dag, "deregister", shadow_dir=tmp_path / "shadow", proxy_runner=_block_runner,
    )
    assert result.status == "BLOCKED"
    assert result.proxy and result.proxy["decision"] == "BLOCK"


def test_destructive_compensation_requires_plan_bound_token_path(tmp_path: Path):
    """Compensation node that is destructive must include plan_hash + token."""
    primary = make_node(
        "delete",
        plan=make_plan(
            "aws-s3-ops",
            "s3api delete-bucket",
            args={"argv": ["--bucket", "b1"]},
            region="us-east-1",
            risk="destructive",
        ),
        on_fail="compensate",
        compensation="recreate-stub",
    )
    # Destructive-looking compensation (delete-object) to force token path.
    comp = make_node(
        "recreate-stub",
        plan=make_plan(
            "aws-s3-ops",
            "s3api delete-object",
            args={"argv": ["--bucket", "b1", "--key", "x"]},
            region="us-east-1",
            risk="destructive",
        ),
    )
    dag = make_dag([primary, comp])
    seen: list[dict] = []

    def runner(payload, **_kw):
        seen.append(payload)
        # Verify token would match if we built it ourselves.
        cmd = payload["command"]
        tool = " ".join(cmd[:3])
        assert detect_destructive(tool)
        assert payload.get("plan_hash")
        assert payload.get("safety_confirm")
        call = ToolCall(
            tool_name=tool,
            args={"argv": cmd[3:]},
            plan_hash=payload["plan_hash"],
        )
        assert payload["safety_confirm"] == build_plan_bound_token(
            call, payload["plan_hash"],
        )
        return _allow_runner(payload)

    result = run_compensation(
        dag, "delete", shadow_dir=tmp_path / "shadow", proxy_runner=runner,
    )
    assert result.status == "COMPENSATED"
    assert seen


def test_real_proxy_dry_run_compensation_non_destructive(tmp_path: Path):
    """End-to-end: compensation_runner → real safe_tool_proxy --dry-run."""
    dag = _elb_dag()
    fake_aws = tmp_path / "bin"
    fake_aws.mkdir()
    aws = fake_aws / "aws"
    aws.write_text("#!/bin/sh\nprintf 'ok\\n'\n")
    aws.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{fake_aws}:{env.get('PATH', '')}"

    result = run_compensation(
        dag,
        "deregister",
        shadow_dir=tmp_path / "shadow",
        dry_run=True,
        env=env,
    )
    # register-targets is typically non-destructive → ALLOW with dry-run
    assert result.status == "COMPENSATED", result
    assert result.proxy and result.proxy.get("decision") == "ALLOW"


def test_cli_self_check():
    r = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "compensation_runner.py"), "--self-check"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    payload = json.loads(r.stdout)
    assert payload["status"] == "COMPENSATED"
