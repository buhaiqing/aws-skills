"""TDD tests for scripts/_reflexion.py — L4 dim #3 reflexion automation.

Real fixtures: scripts/tests/fixtures/gcl-traces/ (committed; audit-results is gitignored).
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from _reflexion import (  # noqa: E402
    FailurePattern,
    derive_from_trace,
    append_or_increment,
    prune_low_frequency,
)


_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "gcl-traces"
SAFETY_FAIL_TRACE = _FIXTURES / "gcl-trace-20260627-031257.json"
MAX_ITER_TRACE = _FIXTURES / "gcl-trace-20260627-031303.json"


def test_derive_from_pass_trace_returns_empty():
    """PASS status → no patterns (we only reflect on failures)."""
    trace = {"final": {"status": "PASS"}, "iterations": [{"critic": {"scores": {"safety": 1.0}}}]}
    assert derive_from_trace(trace) == []


def test_derive_from_safety_fail_returns_one_pattern():
    """SAFETY_FAIL trace → 1 pattern referencing the failing dimension."""
    trace = json.loads(SAFETY_FAIL_TRACE.read_text())
    patterns = derive_from_trace(trace)
    assert len(patterns) == 1
    p = patterns[0]
    assert p.skill == "aws-s3-ops"
    assert "safety" in p.error
    assert p.command == "aws --self-test"
    # timestamp must be ISO 8601
    parsed_ts = datetime.fromisoformat(p.timestamp)
    assert parsed_ts.tzinfo is not None


def test_derive_from_max_iter_returns_one_pattern():
    """MAX_ITER trace → 1 pattern referencing the failing dimension (idempotency)."""
    trace = json.loads(MAX_ITER_TRACE.read_text())
    patterns = derive_from_trace(trace)
    assert len(patterns) == 1
    p = patterns[0]
    assert p.skill == "aws-s3-ops"
    assert "idempotency" in p.error


def test_append_or_increment_adds_new_row(tmp_path):
    """Empty file → first append creates header + 1 row."""
    target = tmp_path / "failure-patterns.md"
    pat = FailurePattern(
        skill="aws-test-ops", command="aws test",
        error="safety=0.0", root_cause="r", fix="f", timestamp="2026-07-25T00:00:00+00:00",
    )
    result = append_or_increment(target, pat)
    assert result == "appended"
    text = target.read_text()
    assert "aws-test-ops" in text
    assert "safety=0.0" in text
    # Count column = 1
    assert "| 1 |" in text


def test_append_or_increment_dedups_and_increments(tmp_path):
    """Same pattern appended twice → count = 2, only 1 row."""
    target = tmp_path / "failure-patterns.md"
    pat = FailurePattern(
        skill="aws-test-ops", command="aws test",
        error="safety=0.0", root_cause="r", fix="f", timestamp="2026-07-25T00:00:00+00:00",
    )
    append_or_increment(target, pat)
    pat2 = FailurePattern(
        skill="aws-test-ops", command="aws test",
        error="safety=0.0", root_cause="r", fix="f", timestamp="2026-07-25T00:01:00+00:00",
    )
    result = append_or_increment(target, pat2)
    assert result == "incremented"
    text = target.read_text()
    # Only one data row
    data_rows = [ln for ln in text.splitlines() if ln.startswith("| aws-test-ops")]
    assert len(data_rows) == 1
    assert "| 2 |" in text


def test_prune_removes_low_frequency(tmp_path):
    """Prune drops count < min_count."""
    target = tmp_path / "failure-patterns.md"
    target.write_text(
        "# Test\n## Section\n| skill | command | error | root_cause | fix | count | timestamp |\n|-------|---------|-------|------------|-----|-------|-----------|\n"
        "| aws-a | cmd | err-A | rc | fx | 1 | ts |\n"
        "| aws-b | cmd | err-B | rc | fx | 1 | ts |\n"
        "| aws-c | cmd | err-C | rc | fx | 1 | ts |\n"
        "| aws-d | cmd | err-D | rc | fx | 1 | ts |\n"
        "| aws-e | cmd | err-E | rc | fx | 1 | ts |\n"
        "| aws-keep | cmd | err-K | rc | fx | 5 | ts |\n"
    )
    removed = prune_low_frequency(target, min_count=3, max_lines=10)
    assert removed == 5
    text = target.read_text()
    assert "aws-keep" in text
    assert "aws-a" not in text


def test_gcl_runner_self_test_on_fail_appends_to_failure_patterns(tmp_path):
    """End-to-end: gcl_runner.py --self-test --on-fail → appends to failure-patterns.md."""
    target = tmp_path / "failure-patterns.md"
    result = subprocess.run(
        [
            sys.executable, str(SCRIPTS_DIR / "gcl_runner.py"),
            "--skill", "aws-s3-ops",
            "--request", "delete bucket test",  # destructive → safety=0 → SAFETY_FAIL
            "--self-test", "--no-prune", "--on-fail",
            "--failure-patterns", str(target),
        ],
        capture_output=True, text=True, cwd=str(REPO), timeout=60,
    )
    assert target.exists(), f"--on-fail should create file. stdout={result.stdout} stderr={result.stderr}"
    text = target.read_text()
    # --self-test for aws-s3-ops SAFETY_FAIL should append a row
    assert "aws-s3-ops" in text
    # Default SAFETY_FAIL trace has safety=0
    assert "safety" in text


# --- F-23: empty-file presence bug (silent data loss) ---

def test_append_or_increment_recovers_from_empty_existing_file(tmp_path):
    """When failure-patterns.md exists but is empty, append must NOT silently lose data.

    Reproduces: external tooling (touch, git checkout, etc.) leaves a 0-byte
    file. Without this fix, _replace_rows finds no header and writes empty
    content back, losing the new pattern.
    """
    from _reflexion import FailurePattern as FP

    p = tmp_path / "failure-patterns.md"
    p.write_text("")  # exists but empty
    pat = FP(
        skill="aws-ec2-ops",
        command="aws ec2 terminate-instances",
        error="MissingParameter",
        root_cause="no instance ids arg",
        fix="pass --instance-ids",
        timestamp="2026-07-25T00:00:00+00:00",
    )
    result = append_or_increment(p, pat)
    text = p.read_text(encoding="utf-8")
    assert result == "appended"
    # Critical: file MUST now have valid header + 1 data row
    assert text.strip(), "file is empty after append (silent data loss)"
    assert "skill" in text and "command" in text and "count" in text, (
        f"header not restored, got: {text!r}"
    )
    assert "aws ec2 terminate-instances" in text, "data row missing"
    assert p.stat().st_size > 0, "file size still 0"


def test_append_or_increment_recovers_from_corrupted_no_header_file(tmp_path):
    """When failure-patterns.md exists with content but no header row, append rebuilds.

    A file containing only data rows (no `| skill | command | ...` header)
    is treated similarly: `_parse_table_rows` finds 0 rows, dedup loop
    appends a new row, but `_replace_rows` cannot locate the header to
    splice into — so the data row would be silently dropped. Fix should
    detect this case and reseed from scratch.
    """
    from _reflexion import FailurePattern as FP

    p = tmp_path / "failure-patterns.md"
    # Body that LOOKS like a table row but no header above
    p.write_text(
        "| aws-ec2-ops | aws ec2 terminate-instances | MissingParameter | rc | fix | 1 | 2026-07-25T00:00:00+00:00 |\n"
    )
    pat = FP(
        skill="aws-s3-ops",
        command="aws s3 rm",
        error="NoSuchBucket",
        root_cause="x",
        fix="y",
        timestamp="2026-07-25T00:01:00+00:00",
    )
    append_or_increment(p, pat)
    text = p.read_text(encoding="utf-8")
    # New row must be present; fix rebuilds from scratch (replaces file)
    assert "aws s3 rm" in text, "new row missing"
    assert p.stat().st_size > 0, "file should not be empty"
