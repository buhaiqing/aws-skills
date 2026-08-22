"""Compat: runtime_safety + _reflexion transparently handle .jsonl via failure_kb."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from _reflexion import FailurePattern, append_or_increment  # noqa: E402
from runtime_safety import load_failure_patterns  # noqa: E402
import failure_kb  # noqa: E402


def _seed_jsonl(path: Path):
    rec = failure_kb.FailureRecord(
        skill="aws-ec2-ops",
        command="aws ec2 terminate-instances",
        error="MissingParameter",
        error_signature="aws-ec2-ops|aws ec2 terminate-instances|MissingParameter",
        root_cause="rc",
        fix="fx",
        count=3,
        first_seen="2026-07-25T00:00:00+00:00",
        last_seen="2026-07-25T00:00:00+00:00",
    )
    failure_kb.append_or_increment(rec, path)


def test_runtime_safety_loads_jsonl(tmp_path: Path):
    p = tmp_path / "kb.jsonl"
    _seed_jsonl(p)
    rows = load_failure_patterns(p)
    assert len(rows) == 1
    r = rows[0]
    assert r["skill"] == "aws-ec2-ops"
    assert r["command"] == "aws ec2 terminate-instances"
    assert r["error"] == "MissingParameter"
    assert r["count"] == "3"


def test_runtime_safety_still_loads_md(tmp_path: Path):
    p = tmp_path / "failure-patterns.md"
    p.write_text(
        "# Failure Patterns\n\n"
        "| skill | command | error | root_cause | fix | count | timestamp |\n"
        "|-------|---------|-------|------------|-----|-------|-----------|\n"
        "| aws-s3-ops | aws s3 rm | NoSuchBucket | rc | fx | 2 | 2026-07-25T00:00:00+00:00 |\n"
    )
    rows = load_failure_patterns(p)
    assert len(rows) == 1
    assert rows[0]["skill"] == "aws-s3-ops"
    assert rows[0]["count"] == 2


def test_reflexion_appends_to_jsonl(tmp_path: Path):
    p = tmp_path / "kb.jsonl"
    pat = FailurePattern(
        skill="aws-s3-ops",
        command="aws s3 rm",
        error="NoSuchBucket",
        root_cause="rc",
        fix="fx",
        timestamp="2026-07-25T00:00:00+00:00",
    )
    result = append_or_increment(p, pat)
    assert result == "appended"
    data = json.loads(p.read_text().strip().splitlines()[0])
    assert data["skill"] == "aws-s3-ops"
    assert data["command"] == "aws s3 rm"


def test_reflexion_still_writes_md(tmp_path: Path):
    p = tmp_path / "failure-patterns.md"
    pat = FailurePattern(
        skill="aws-s3-ops",
        command="aws s3 rm",
        error="NoSuchBucket",
        root_cause="rc",
        fix="fx",
        timestamp="2026-07-25T00:00:00+00:00",
    )
    result = append_or_increment(p, pat)
    assert result == "appended"
    text = p.read_text()
    assert "aws s3 rm" in text
    assert "| skill | command |" in text
