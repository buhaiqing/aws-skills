from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import gcl_runner


def test_normalize_outcome_accepts_five_statuses():
    """ADR M1 unified enum: PASS, SAFETY_FAIL, MAX_ITER, BLOCKED, COMPENSATED."""
    for status in ("PASS", "SAFETY_FAIL", "MAX_ITER", "BLOCKED", "COMPENSATED"):
        assert gcl_runner.normalize_outcome(status) == status
    assert gcl_runner.normalize_outcome("blocked") == "BLOCKED"


def test_normalize_outcome_rejects_unknown():
    with pytest.raises(ValueError, match="unknown outcome"):
        gcl_runner.normalize_outcome("WHO_KNOWS")


def test_critic_context_hides_raw_request_and_user_namespace() -> None:
    captured: list[dict] = []

    def generator(ctx: dict) -> dict:
        return {"command": "aws s3 list-buckets", "args": {}, "exit_code": 0}

    def critic(ctx: dict) -> dict:
        captured.append(ctx)
        return {
            "scores": {
                "correctness": 1,
                "safety": 1,
                "idempotency": 1,
                "traceability": 1,
                "spec_compliance": 1,
            },
            "suggestions": [],
            "blocking": False,
        }

    result = gcl_runner.run_with_callables(
        skill_name="aws-s3-ops",
        request="delete bucket secret-name",
        user_region="us-east-1",
        generator=generator,
        critic=critic,
    )

    assert result["final"]["status"] == "PASS"
    assert result["request"].startswith("<request-sha256:")
    assert captured
    assert "user" not in captured[0]
    assert "secret-name" not in json.dumps(captured[0])
    assert "user" not in captured[0]


def test_critic_feedback_is_passed_to_next_generator_iteration() -> None:
    generator_inputs: list[dict] = []
    calls = 0

    def generator(ctx: dict) -> dict:
        nonlocal calls
        calls += 1
        generator_inputs.append(ctx)
        return {"command": "aws s3 list-buckets", "args": {}, "exit_code": 0}

    def critic(ctx: dict) -> dict:
        if ctx["iter"] == 1:
            return {
                "scores": {
                    "correctness": 0.5,
                    "safety": 1,
                    "idempotency": 0,
                    "traceability": 1,
                    "spec_compliance": 1,
                },
                "suggestions": ["add idempotency evidence"],
                "blocking": False,
            }
        return {
            "scores": {
                "correctness": 1,
                "safety": 1,
                "idempotency": 1,
                "traceability": 1,
                "spec_compliance": 1,
            },
            "suggestions": [],
            "blocking": False,
        }

    result = gcl_runner.run_with_callables(
        skill_name="aws-s3-ops",
        request="list buckets",
        user_region="us-east-1",
        generator=generator,
        critic=critic,
    )

    assert calls == 2
    assert generator_inputs[1]["output"]["critic_feedback"] == [
        "add idempotency evidence"
    ]
    assert result["final"]["status"] == "PASS"


def test_secret_redaction_removes_sensitive_values() -> None:
    value = {
        "Password": "hunter2",
        "nested": {"AWS_SECRET_ACCESS_KEY": "secret-value"},
        "text": "token=abc123 password=hunter2",
    }

    redacted = gcl_runner.redact_sensitive(value)

    assert redacted["Password"] == "***"
    assert redacted["nested"]["AWS_SECRET_ACCESS_KEY"] == "***"
    assert "hunter2" not in json.dumps(redacted)
    assert "abc123" not in json.dumps(redacted)


def test_generator_echo_of_raw_request_is_not_sent_to_critic() -> None:
    captured: list[dict] = []

    def generator(ctx: dict) -> dict:
        return {
            "command": "aws s3 list-buckets",
            "args": {},
            "exit_code": 0,
            "request": ctx["user"]["request"],
        }

    def critic(ctx: dict) -> dict:
        captured.append(ctx)
        return {
            "scores": {dimension: 1 for dimension in (
                "correctness", "safety", "idempotency", "traceability", "spec_compliance",
            )},
            "suggestions": [],
            "blocking": False,
        }

    gcl_runner.run_with_callables(
        "aws-s3-ops", "list buckets private-name", "us-east-1", generator, critic,
    )

    assert "private-name" not in json.dumps(captured[0])


def test_invalid_critic_contract_is_safety_failure() -> None:
    def generator(ctx: dict) -> dict:
        return {"command": "aws s3 list-buckets", "args": {}, "exit_code": 0}

    def critic(ctx: dict) -> dict:
        return {"scores": {"safety": 1}, "suggestions": [], "blocking": False}

    result = gcl_runner.run_with_callables(
        "aws-s3-ops", "list buckets", "us-east-1", generator, critic,
    )

    assert result["final"]["status"] == "SAFETY_FAIL"


def test_critic_confirmation_is_derived_from_generator_trace() -> None:
    captured: list[dict] = []

    def generator(ctx: dict) -> dict:
        return {"command": "aws s3 list-buckets", "args": {}, "exit_code": 0}

    def critic(ctx: dict) -> dict:
        captured.append(ctx)
        return {
            "scores": {dimension: 1 for dimension in (
                "correctness", "safety", "idempotency", "traceability", "spec_compliance",
            )},
            "suggestions": [],
            "blocking": False,
        }

    gcl_runner.run_with_callables(
        "aws-s3-ops", "list buckets", "us-east-1", generator, critic,
        safety_confirm="USER_ONLY_TOKEN",
    )

    assert captured[0]["output"]["safety_confirm_token"] == ""


def test_trust_boundary_error_is_redacted_in_trace() -> None:
    def generator(ctx: dict) -> dict:
        raise RuntimeError("password=hunter2")

    def critic(ctx: dict) -> dict:
        raise AssertionError("critic must not run")

    result = gcl_runner.run_with_callables(
        "aws-s3-ops", "list buckets", "us-east-1", generator, critic,
    )

    assert "hunter2" not in json.dumps(result)
    assert "password=***" in result["final"]["reason"]


def test_confirmation_token_is_not_persisted_in_final_trace() -> None:
    def generator(ctx: dict) -> dict:
        return {
            "command": "aws s3 list-buckets",
            "args": {},
            "exit_code": 0,
            "safety_confirm_token": "CONFIRM REPLAYABLE",
        }

    def critic(ctx: dict) -> dict:
        assert ctx["output"]["safety_confirm_token"] == "CONFIRM REPLAYABLE"
        return {
            "scores": {dimension: 1 for dimension in (
                "correctness", "safety", "idempotency", "traceability", "spec_compliance",
            )},
            "suggestions": [],
            "blocking": False,
        }

    result = gcl_runner.run_with_callables(
        "aws-s3-ops", "list buckets", "us-east-1", generator, critic,
    )

    assert "CONFIRM REPLAYABLE" not in json.dumps(result)


def test_external_command_timeout_is_bounded() -> None:
    with pytest.raises(gcl_runner.CommandTimeout):
        gcl_runner.invoke_json_command(
            [sys.executable, "-c", "import time; time.sleep(1)"],
            {"input": True},
            timeout=0.01,
        )


def test_external_command_rejects_non_object_json() -> None:
    script = "import sys; print('[]')"
    with pytest.raises(gcl_runner.CommandContractError):
        gcl_runner.invoke_json_command(
            [sys.executable, "-c", script],
            {"input": True},
            timeout=1,
        )


def test_trace_paths_are_unique_within_same_second(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(gcl_runner, "AUDIT_DIR", tmp_path)

    first = gcl_runner._trace_path()
    second = gcl_runner._trace_path()

    assert first != second


def test_critic_environment_does_not_inherit_aws_credentials(monkeypatch) -> None:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAEXAMPLE")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("AWS_PROFILE", "production")
    original_home = os.environ.get("HOME", "")

    env = gcl_runner.critic_environment()

    assert "AWS_ACCESS_KEY_ID" not in env
    assert "AWS_SECRET_ACCESS_KEY" not in env
    assert "AWS_PROFILE" not in env
    assert env["AWS_EC2_METADATA_DISABLED"] == "true"
    assert env["AWS_SHARED_CREDENTIALS_FILE"] == os.devnull
    assert env["HOME"] != original_home


def test_critic_invocation_uses_restricted_environment(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def fake_invoke(cmd, payload, timeout=gcl_runner.DEFAULT_COMMAND_TIMEOUT, env=None):
        captured.update(env or {})
        return {"scores": {dimension: 1 for dimension in (
            "correctness", "safety", "idempotency", "traceability", "spec_compliance",
        )}, "suggestions": [], "blocking": False}

    monkeypatch.setattr(gcl_runner, "invoke_json_command", fake_invoke)
    gcl_runner._invoke_critic({}, ["critic"], "rubric")

    assert captured["AWS_EC2_METADATA_DISABLED"] == "true"
