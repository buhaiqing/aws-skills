"""TDD tests for scripts/runtime_safety.py — L4 dim #6 runtime guardrail.

The runtime guardrail is invoked BEFORE a destructive AWS op executes.
It cross-references the call against the historical failure-pattern library
(failure-patterns.md, written by _reflexion.py) and returns a decision:
ALLOW / WARN / BLOCK.

Real fixtures: a tmp failure-patterns.md with known count distributions.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from runtime_safety import (  # noqa: E402
    ToolCall,
    build_confirmation_token,
    load_failure_patterns,
    check_tool_call,
)


def _make_pattern_file(tmp_path: Path, rows: list[dict]) -> Path:
    """Build a failure-patterns.md fixture with given table rows."""
    p = tmp_path / "failure-patterns.md"
    p.write_text(
        "# Failure Patterns (test fixture)\n\n"
        "## CLI Parameter Errors\n\n"
        "| skill | command | error | root_cause | fix | count | timestamp |\n"
        "|-------|---------|-------|------------|-----|-------|-----------|\n"
        + "\n".join(
            f"| {r.get('skill', 'aws-x')} | {r.get('command', 'aws x')} | "
            f"{r.get('error', 'e=0')} | {r.get('root_cause', 'rc')} | "
            f"{r.get('fix', 'fx')} | {r.get('count', 1)} | "
            f"{r.get('timestamp', '2026-07-25T00:00:00+00:00')} |"
            for r in rows
        )
        + "\n"
    )
    return p


def test_load_patterns_parses_markdown(tmp_path):
    """Real-style markdown table → list of dicts with required fields."""
    p = _make_pattern_file(tmp_path, [
        {"skill": "aws-ec2-ops", "command": "aws ec2 terminate-instances",
         "error": "MissingParameter=--instance-ids", "count": 5},
        {"skill": "aws-s3-ops", "command": "aws s3 rm",
         "error": "NoSuchBucket", "count": 2},
    ])
    patterns = load_failure_patterns(p)
    assert len(patterns) == 2
    assert patterns[0]["skill"] == "aws-ec2-ops"
    assert patterns[0]["count"] == 5
    assert patterns[1]["skill"] == "aws-s3-ops"


def test_check_call_allow_for_readonly():
    """Non-destructive op → ALLOW, no need to check patterns."""
    call = ToolCall(tool_name="aws s3 ls", args={}, is_destructive=False)
    result = check_tool_call(call, patterns=[])
    assert result.decision == "ALLOW"
    assert result.matched_patterns == []


def test_check_call_block_for_destructive_without_confirm(tmp_path):
    """Destructive op + no exact confirmation → BLOCK."""
    p = _make_pattern_file(tmp_path, [])  # empty pattern file
    call = ToolCall(
        tool_name="aws ec2 terminate-instances",
        args={"instance_ids": ["i-123"]},
        is_destructive=True,
        safety_confirm="",
    )
    result = check_tool_call(call, patterns=load_failure_patterns(p))
    assert result.decision == "BLOCK"
    assert "confirm" in result.reason.lower()


def test_check_call_allow_with_confirm_and_no_pattern(tmp_path):
    """Destructive op + safety_confirm + no matching pattern → ALLOW."""
    p = _make_pattern_file(tmp_path, [
        {"skill": "aws-s3-ops", "command": "aws s3 rm", "count": 5},
    ])
    call = ToolCall(
        tool_name="aws ec2 terminate-instances",
        args={"instance_ids": ["i-123"]},
        is_destructive=True,
        safety_confirm="",
    )
    call.safety_confirm = build_confirmation_token(call)
    result = check_tool_call(call, patterns=load_failure_patterns(p))
    assert result.decision == "ALLOW"
    assert result.matched_patterns == []


def test_check_call_block_when_matches_high_freq_pattern(tmp_path):
    """Destructive op matches a count>=3 pattern → BLOCK even with confirm."""
    p = _make_pattern_file(tmp_path, [
        {"skill": "aws-ec2-ops", "command": "aws ec2 terminate-instances",
         "error": "MissingParameter=--instance-ids", "count": 5},
    ])
    call = ToolCall(
        tool_name="aws ec2 terminate-instances",
        args={},  # missing --instance-ids!
        is_destructive=True,
        safety_confirm="CONFIRM",  # even with confirm, block on high-freq match
    )
    result = check_tool_call(call, patterns=load_failure_patterns(p))
    assert result.decision == "BLOCK"
    assert len(result.matched_patterns) == 1
    assert result.matched_patterns[0]["count"] == 5


def test_check_call_warn_with_low_freq_pattern_match(tmp_path):
    """Destructive op matches count<3 pattern → WARN (suggest more confirm)."""
    p = _make_pattern_file(tmp_path, [
        {"skill": "aws-ec2-ops", "command": "aws ec2 terminate-instances",
         "error": "MissingParameter=--instance-ids", "count": 1},
    ])
    call = ToolCall(
        tool_name="aws ec2 terminate-instances",
        args={},
        is_destructive=True,
        safety_confirm="",
    )
    call.safety_confirm = build_confirmation_token(call)
    result = check_tool_call(call, patterns=load_failure_patterns(p))
    # Low-freq match → WARN after exact confirmation.
    assert result.decision == "WARN"
    assert len(result.matched_patterns) == 1


def test_cli_stdin_stdout_e2e(tmp_path):
    """End-to-end: feed JSON via stdin, parse JSON from stdout, check exit code."""
    p = _make_pattern_file(tmp_path, [
        {"skill": "aws-ec2-ops", "command": "aws ec2 terminate-instances",
         "error": "MissingParameter=--instance-ids", "count": 5},
    ])
    call_json = json.dumps({
        "tool_name": "aws ec2 terminate-instances",
        "args": {},
        "is_destructive": True,
        "safety_confirm": "",
    })
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "runtime_safety.py"),
         "--patterns", str(p)],
        input=call_json, capture_output=True, text=True, timeout=10,
    )
    # BLOCK → exit 1
    assert result.returncode == 1, f"stderr: {result.stderr}"
    parsed = json.loads(result.stdout)
    assert parsed["decision"] == "BLOCK"
    assert "terminate-instances" in parsed["reason"]
    assert len(parsed["matched_patterns"]) >= 1


# --- F-3: token-level matching (security hardening) ---

def test_match_rejects_service_only_pattern(tmp_path):
    """Pattern with only `aws <svc>` (no op) must NOT match any op of that service.

    Rationale: a service-only pattern would over-match (BLOCK all rds ops, etc).
    The fix is to require both service AND op tokens.
    """
    p = _make_pattern_file(tmp_path, [
        {"skill": "aws-rds-ops", "command": "aws rds",
         "error": "service-only-pattern", "count": 5},
    ])
    call = ToolCall(
        tool_name="aws rds delete-db-instance",
        args={"db_instance_identifier": "x"},
        is_destructive=True,
        safety_confirm="",
    )
    call.safety_confirm = build_confirmation_token(call)
    result = check_tool_call(call, patterns=load_failure_patterns(p))
    # service-only pattern (no op) → no match → ALLOW despite high count
    assert result.decision == "ALLOW", (
        f"service-only pattern must not match; got {result.decision} "
        f"(reason: {result.reason})"
    )


def test_match_rejects_different_op_same_service(tmp_path):
    """Pattern `aws rds describe-db-instances` must NOT match `aws rds delete-db-instance`.

    Defends against F-3 (over-matching): a pattern targeting an op must not
    block sibling ops on the same service.
    """
    p = _make_pattern_file(tmp_path, [
        {"skill": "aws-rds-ops", "command": "aws rds describe-db-instances",
         "error": "highfreq", "count": 5},
    ])
    call = ToolCall(
        tool_name="aws rds delete-db-instance",
        args={"db_instance_identifier": "prod-x"},
        is_destructive=True,
        safety_confirm="",
    )
    call.safety_confirm = build_confirmation_token(call)
    result = check_tool_call(call, patterns=load_failure_patterns(p))
    # Different op → no match → ALLOW (warn gate would also be acceptable)
    assert result.decision in ("ALLOW", "WARN"), (
        f"different op must not BLOCK; got {result.decision} "
        f"(reason: {result.reason})"
    )
    if result.decision == "BLOCK":
        raise AssertionError(
            f"different op triggered BLOCK: {result.reason}"
        )


def test_match_rejects_different_service(tmp_path):
    """Pattern `aws ec2 terminate-instances` must NOT match `aws s3 rm`."""
    p = _make_pattern_file(tmp_path, [
        {"skill": "aws-ec2-ops", "command": "aws ec2 terminate-instances",
         "error": "x", "count": 5},
    ])
    call = ToolCall(
        tool_name="aws s3 rm",
        args={"--recursive": True},
        is_destructive=True,
        safety_confirm="",
    )
    call.safety_confirm = build_confirmation_token(call)
    result = check_tool_call(call, patterns=load_failure_patterns(p))
    assert result.decision == "ALLOW", (
        f"different service must not BLOCK; got {result.decision}"
    )


def test_match_handles_boto3_dotted_method_via_fallback(tmp_path):
    """Non-AWS-CLI commands (e.g. boto3 dotted methods) fall through to substring match.

    The token-level matcher only fires for `aws <svc> <op> [args]` syntax.
    boto3 dotted methods (`ec2.terminate_instances`) keep the legacy
    case-insensitive substring behavior.
    """
    p = _make_pattern_file(tmp_path, [
        {"skill": "aws-ec2-ops", "command": "ec2.terminate_instances",
         "error": "x", "count": 5},
    ])
    call = ToolCall(
        tool_name="boto3.ec2.terminate_instances",
        args={"InstanceIds": ["i-xxx"]},
        is_destructive=True,
        safety_confirm="",
    )
    call.safety_confirm = build_confirmation_token(call)
    result = check_tool_call(call, patterns=load_failure_patterns(p))
    # Both are boto3 dotted methods → substring fallback matches → BLOCK (high-freq)
    assert result.decision == "BLOCK", (
        f"boto3 substring fallback should match; got {result.decision} "
        f"(reason: {result.reason})"
    )
# --- P0-1: reflexion-on-block path ---



def test_reflect_block_appends_to_failure_patterns_md(tmp_path):
    # Build a minimal failure-patterns.md with one existing pattern
    fp = tmp_path / "failure-patterns.md"
    fp.write_text(
        "# Failure Patterns\n\n"
        "| skill | command | error | root_cause | fix | count | timestamp |\n"
        "|-------|---------|-------|------------|-----|-------|-----------|\n"
        "| ec2-ops | terminate-instances | MissingParameter | Missing `--instance-ids` | --instance-ids i-xxx | 4 | 2026-07-27T00:00:00+00:00 |\n"
    )
    initial_lines = fp.read_text().count("\n")

    call_json = json.dumps({
        "tool_name": "aws ec2 terminate-instances",
        "args": {"instance_ids": ["i-xxx"]},
        "is_destructive": True,
        "safety_confirm": "CONFIRM-X",
    })
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "runtime_safety.py"),
         "--patterns", str(fp), "--reflect-on-block"],
        input=call_json, capture_output=True, text=True, timeout=10,
    )
    # BLOCK → exit 1
    assert result.returncode == 1, f"expected BLOCK (exit 1), got {result.returncode}\nstderr: {result.stderr}"
    parsed = json.loads(result.stdout)
    assert parsed["decision"] == "BLOCK"

    # failure-patterns.md should have one new row appended
    new_content = fp.read_text()
    assert new_content.count("\n") > initial_lines, "no new row appended"
    assert "BLOCK: high-freq pattern matched" in new_content


def test_reflect_block_increments_existing_row(tmp_path):
    """Second BLOCK for same command increments the count (dedup by skill+command+error)."""
    fp = tmp_path / "failure-patterns.md"
    # Start with an existing reflexion entry (count=3, high-freq → BLOCK)
    fp.write_text(
        "# Failure Patterns\n\n"
        "| skill | command | error | root_cause | fix | count | timestamp |\n"
        "|-------|---------|-------|------------|-----|-------|-----------|\n"
        "| ec2-ops | terminate-instances | BLOCK: high-freq pattern matched (count=3) "
        "| root cause placeholder | fix placeholder | 3 | 2026-07-27T00:00:00+00:00 |\n"
    )

    call_json = json.dumps({
        "tool_name": "aws ec2 terminate-instances",
        "args": {"instance_ids": ["i-yyy"]},
        "is_destructive": True,
        "safety_confirm": "CONFIRM-Y",
    })
    # Run once — BLOCK
    r1 = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "runtime_safety.py"),
         "--patterns", str(fp), "--reflect-on-block"],
        input=call_json, capture_output=True, text=True, timeout=10,
    )
    assert r1.returncode == 1

    # Count how many "BLOCK: high-freq" rows exist now
    content = fp.read_text()
    count = content.count("BLOCK: high-freq pattern matched")
    # append_or_increment deduplicates by skill|command|error → 1 row
    assert count == 1, f"expected 1 deduped row, got {count}"
    # The count column of the reflexion row should have incremented from 3 → 4
    import re
    m = re.search(r"BLOCK: high-freq.*?\| (\d+) \|", content)
    assert m and int(m.group(1)) >= 4, f"count did not increment: {m.group(1) if m else 'no match'}"

def test_reflect_block_noop_without_flag(tmp_path):
    """Without --reflect-on-block, failure-patterns.md is not modified."""
    fp = tmp_path / "failure-patterns.md"
    fp.write_text(
        "# Failure Patterns\n\n"
        "| skill | command | error | root_cause | fix | count | timestamp |\n"
        "|-------|---------|-------|------------|-----|-------|-----------|\n"
        "| ec2-ops | terminate-instances | MissingParameter | Missing `--instance-ids` | --instance-ids i-xxx | 4 | 2026-07-27T00:00:00+00:00 |\n"
    )
    initial = fp.read_text()

    call_json = json.dumps({
        "tool_name": "aws ec2 terminate-instances",
        "args": {"instance_ids": ["i-xxx"]},
        "is_destructive": True,
        "safety_confirm": "CONFIRM-X",
    })
    r = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "runtime_safety.py"),
         "--patterns", str(fp)],   # NO --reflect-on-block flag
        input=call_json, capture_output=True, text=True, timeout=10,
    )
    assert r.returncode == 1  # BLOCK, but no reflexion
    assert fp.read_text() == initial, "failure-patterns.md was modified without --reflect-on-block"
# --- P0-1 boundary: reflexion failure modes ---

def test_reflect_block_silent_on_unreadable_path(tmp_path):
    """BLOCK decision returns exit 1 even when patterns_path is not writable."""
    fp = tmp_path / "failure-patterns.md"
    fp.write_text(
        "# Failure Patterns\n\n"
        "| skill | command | error | root_cause | fix | count | timestamp |\n"
        "|-------|---------|-------|------------|-----|-------|-----------|\n"
        "| ec2-ops | terminate-instances | MissingParameter | Missing `--instance-ids` | --instance-ids i-xxx | 4 | 2026-07-27T00:00:00+00:00 |\n"
    )
    fp.chmod(0o000)   # make unreadable/unwritable
    try:
        call_json = json.dumps({
            "tool_name": "aws ec2 terminate-instances",
            "args": {"instance_ids": ["i-xxx"]},
            "is_destructive": True,
            "safety_confirm": "CONFIRM-X",
        })
        r = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "runtime_safety.py"),
             "--patterns", str(fp), "--reflect-on-block"],
            input=call_json, capture_output=True, text=True, timeout=10,
        )
        # Must still exit 1 (BLOCK) even though reflexion failed silently
        assert r.returncode == 1, (
            f"BLOCK should still exit 1 when reflexion fails; got {r.returncode}\n"
            f"stderr: {r.stderr}"
        )
    finally:
        fp.chmod(0o644)   # restore so tmp_path cleanup can delete it


def test_reflect_block_silent_when_reflexion_mod_missing(tmp_path):
    """BLOCK exits 1 even when _reflexion.py is absent from scripts/."""
    rx_path = SCRIPTS_DIR / "_reflexion.py"
    bak = SCRIPTS_DIR / "_reflexion.py.bak"
    assert rx_path.exists(), "_reflexion.py must exist for this test to be meaningful"
    rx_path.rename(bak)
    try:
        fp = tmp_path / "failure-patterns.md"
        fp.write_text(
            "# Failure Patterns\n\n"
            "| skill | command | error | root_cause | fix | count | timestamp |\n"
            "|-------|---------|-------|------------|-----|-------|-----------|\n"
            "| ec2-ops | terminate-instances | MissingParameter | Missing `--instance-ids` | --instance-ids i-xxx | 4 | 2026-07-27T00:00:00+00:00 |\n"
        )
        call_json = json.dumps({
            "tool_name": "aws ec2 terminate-instances",
            "args": {"instance_ids": ["i-xxx"]},
            "is_destructive": True,
            "safety_confirm": "CONFIRM-X",
        })
        r = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "runtime_safety.py"),
             "--patterns", str(fp), "--reflect-on-block"],
            input=call_json, capture_output=True, text=True, timeout=10,
        )
        assert r.returncode == 1, (
            f"BLOCK should exit 1 when _reflexion.py is absent; got {r.returncode}\n"
            f"stderr: {r.stderr}"
        )
    finally:
        bak.rename(rx_path)   # restore
