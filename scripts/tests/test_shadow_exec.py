"""Unit tests for scripts/shadow_exec.py — ADR-0001 M2 Wave 2.

No live AWS: simulate path is local; dry-run/describe use injectable stubs.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from shadow_exec import (  # noqa: E402
    ShadowResult,
    persist_shadow,
    redact_evidence,
    run_shadow,
)


PLAN_HASH = "a" * 64  # sha256-shaped stand-in


def test_redact_masks_sensitive_keys() -> None:
    payload = {
        "KeyMaterial": "-----BEGIN RSA PRIVATE KEY-----",
        "PasswordData": "hunter2",
        "UserData": "#!/bin/bash\necho secret",
        "SecretAccessKey": "AKIAEXAMPLE",
        "Plaintext": "raw-secret",
        "nested": {"MasterUserPassword": "db-pass"},
        "safe": "instance-id",
        "text": "password=leaked token=abc123",
    }

    redacted = redact_evidence(payload)

    assert redacted["KeyMaterial"].startswith("***")
    assert "BEGIN RSA" not in redacted["KeyMaterial"]
    assert redacted["PasswordData"].startswith("***")
    assert "hunter2" not in redacted["PasswordData"]
    assert redacted["UserData"].startswith("***")
    assert redacted["SecretAccessKey"].startswith("***")
    assert redacted["Plaintext"].startswith("***")
    assert redacted["nested"]["MasterUserPassword"].startswith("***")
    assert redacted["safe"] == "instance-id"
    assert "leaked" not in redacted["text"]
    assert "abc123" not in redacted["text"]
    assert "hunter2" not in json.dumps(redacted)


def test_simulate_mode_ok_without_aws(tmp_path: Path) -> None:
    plan = {
        "plan_hash": PLAN_HASH,
        "operation": "ec2 terminate-instances",
        "resource_ids": ["i-abc"],
        "region": "us-east-1",
        "expected_diff": {"state": {"before": "running", "after": "terminated"}},
    }

    result = run_shadow(plan, mode="simulate", audit_dir=tmp_path)

    assert isinstance(result, ShadowResult)
    assert result.ok is True
    assert result.error is None
    assert result.mode == "simulate"
    assert isinstance(result.evidence, dict)
    assert result.evidence["strategy"] == "simulate"
    assert result.evidence["expected_diff"]["state"]["after"] == "terminated"
    assert "no AWS" in result.evidence["note"]


def test_persist_writes_file(tmp_path: Path) -> None:
    plan = {"plan_hash": PLAN_HASH, "operation": "s3 delete-bucket", "expected_diff": {}}

    result = run_shadow(plan, mode="simulate", audit_dir=tmp_path)

    assert result.path is not None
    path = Path(result.path)
    assert path.exists()
    assert path.parent == tmp_path
    assert path.name.startswith("shadow-")
    assert PLAN_HASH[:16] in path.name
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["plan_hash"] == PLAN_HASH
    assert loaded["ok"] is True
    assert loaded["mode"] == "simulate"


def test_plan_hash_echoed_in_result(tmp_path: Path) -> None:
    result = run_shadow(
        None,
        mode="simulate",
        plan_hash=PLAN_HASH,
        audit_dir=tmp_path,
    )
    assert result.plan_hash == PLAN_HASH


def test_dry_run_uses_injectable_runner(tmp_path: Path) -> None:
    calls: list[tuple] = []

    def stub(plan_map, mode):
        calls.append((plan_map["operation"], mode))
        return {
            "DryRun": True,
            "KeyMaterial": "should-be-masked",
            "InstanceId": "i-xyz",
        }

    plan = {
        "plan_hash": PLAN_HASH,
        "operation": "ec2 terminate-instances",
        "resource_ids": ["i-xyz"],
    }
    result = run_shadow(plan, mode="dry-run", runner=stub, audit_dir=tmp_path)

    assert result.ok is True
    assert calls == [("ec2 terminate-instances", "dry-run")]
    assert result.evidence["InstanceId"] == "i-xyz"
    assert result.evidence["KeyMaterial"].startswith("***")
    assert "should-be-masked" not in json.dumps(result.evidence)


def test_describe_uses_injectable_runner(tmp_path: Path) -> None:
    def stub(plan_map, mode):
        return {"Reservations": [{"Instances": [{"InstanceId": "i-1", "State": "running"}]}]}

    result = run_shadow(
        {"plan_hash": PLAN_HASH, "operation": "ec2 terminate-instances"},
        mode="describe",
        runner=stub,
        audit_dir=tmp_path,
    )
    assert result.ok is True
    assert result.evidence["Reservations"][0]["Instances"][0]["State"] == "running"


def test_dry_run_without_runner_does_not_call_aws(tmp_path: Path) -> None:
    result = run_shadow(
        {"plan_hash": PLAN_HASH, "operation": "ec2 terminate-instances"},
        mode="dry-run",
        audit_dir=tmp_path,
    )
    assert result.ok is False
    assert result.error is not None
    assert "not configured" in result.error or "allowlist" in result.error


def test_persist_shadow_creates_dir(tmp_path: Path) -> None:
    nested = tmp_path / "shadow-out"
    result = ShadowResult(
        plan_hash=PLAN_HASH,
        mode="simulate",
        ok=True,
        evidence={"note": "x"},
        timestamp="2026-07-31T12:00:00Z",
    )
    path = persist_shadow(result, audit_dir=nested)
    assert path.exists()
    assert nested.is_dir()
    assert result.path == str(path)
