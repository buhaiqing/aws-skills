"""Tests for migrate_failure_patterns.py — TDD required by task."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from migrate_failure_patterns import normalize_to_records, parse_sections  # noqa: E402


def _md_text() -> str:
    return (REPO / "docs" / "failure-patterns.md").read_text(encoding="utf-8")


def test_parse_sections_extracts_all():
    sections = parse_sections(_md_text())
    assert len(sections) >= 6
    for k in ["1", "1.5", "2", "3", "4", "5"]:
        assert k in sections
        assert len(sections[k]) >= 1
    total = sum(len(v) for v in sections.values())
    assert total >= 15


def test_parse_section1_schema():
    sections = parse_sections(_md_text())
    rows = sections["1"]
    assert len(rows) == 6
    first = rows[0]
    # header names are preserved as in markdown
    assert "Skill" in first or "skill" in first
    assert first.get("Skill") or first.get("skill")
    # check columns count via keys
    # Headers normalized to lowercase+underscores by parse_sections
    expected_keys = {"skill", "command", "error", "root_cause", "fix", "count", "timestamp"}
    assert expected_keys.issubset(set(first.keys()))


def test_parse_section1_5_chinese_headers():
    sections = parse_sections(_md_text())
    rows = sections["1.5"]
    assert len(rows) >= 1
    first = rows[0]
    # Chinese headers must be mapped to English
    assert "scene" in first
    assert "error_mode" in first
    assert "root_cause" in first
    assert "fix" in first
    assert "count" in first
    # original Chinese keys must NOT remain
    assert "场景" not in first
    assert "错误模式" not in first


def test_normalize_assigns_categories():
    sections = parse_sections(_md_text())
    records = normalize_to_records(sections)
    cats = {r.category for r in records}
    expected = {"cli_parameter", "query_miss", "skill_generation", "cross_skill", "runtime", "token_efficiency"}
    assert expected == cats or expected.issubset(cats)


def test_normalize_fills_defaults():
    sections = parse_sections(_md_text())
    records = normalize_to_records(sections)
    assert len(records) >= 15
    for r in records:
        assert r.count >= 1
        assert r.first_seen  # non-empty date
        assert r.last_seen
        assert r.source == "manual"
        assert r.id.startswith("fp-")
        assert len(r.id) == 9
        assert r.id[3:].isdigit()


def test_normalize_preserves_existing_data():
    sections = parse_sections(_md_text())
    records = normalize_to_records(sections)
    # Section 1 first row has ec2-ops / MissingParameter / count 4
    cli = [r for r in records if r.category == "cli_parameter"]
    assert any("ec2" in r.skill and r.count == 4 for r in cli)
    # Section 3 elb-ops -> ec2-ops with count 3
    cross = [r for r in records if r.category == "cross_skill"]
    assert any("elb" in r.skill and r.count == 3 for r in cross)
    # Section 4 has runtime without count column -> defaults to 1
    runtime = [r for r in records if r.category == "runtime"]
    assert all(r.count >= 1 for r in runtime)
    # Section 2 frequency 10x should be parsed as 10
    skill_gen = [r for r in records if r.category == "skill_generation"]
    assert any(r.count == 10 for r in skill_gen)
    assert any(r.first_seen == "2026-06" for r in skill_gen)


def test_idempotent_skips(tmp_path: Path):
    out = tmp_path / "out.jsonl"
    md = REPO / "docs" / "failure-patterns.md"
    # first run
    result1 = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "migrate_failure_patterns.py"), "--input", str(md), "--output", str(out)],
        capture_output=True, text=True,
    )
    assert result1.returncode == 0
    mtime1 = out.stat().st_mtime
    content1 = out.read_text(encoding="utf-8")
    time.sleep(0.05)
    # ensure input is older than output
    # second run should skip
    result2 = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "migrate_failure_patterns.py"), "--input", str(md), "--output", str(out)],
        capture_output=True, text=True,
    )
    assert result2.returncode == 0
    assert "skip" in result2.stdout.lower()
    assert out.read_text(encoding="utf-8") == content1
    assert out.stat().st_mtime == mtime1


def test_cli_entry(tmp_path: Path):
    out = tmp_path / "test.jsonl"
    md = REPO / "docs" / "failure-patterns.md"
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "migrate_failure_patterns.py"), "--input", str(md), "--output", str(out)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert out.exists()
    lines = [line for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) >= 15
    for line in lines:
        data = json.loads(line)
        assert "id" in data
        assert "category" in data
        assert data["category"] in {"cli_parameter", "query_miss", "skill_generation", "cross_skill", "runtime", "token_efficiency"}
