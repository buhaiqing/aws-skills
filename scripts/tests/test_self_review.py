"""RED tests for self_review.py — Self-Reflection Protocol (P3.4).

Per AGENTS.md §13 CADL: tests must FAIL before impl exists. These tests import
from `self_review` (does not exist yet) → ModuleNotFoundError at collection.
"""
from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

# Add scripts/ to sys.path so `import self_review` resolves to scripts/self_review.py
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from self_review import (  # noqa: E402
    KNOBS,
    VerifyReport,
    generate_report,
    list_findings,
    record_finding,
    verify_findings,
)


# ---------- Fixtures ----------

@pytest.fixture
def tmp_findings_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolated repo with empty findings dir. monkeypatch KNOBS so we do not
    write to the real repo by accident."""
    findings = tmp_path / KNOBS["findings_dir"]
    findings.mkdir(parents=True, exist_ok=True)
    monkeypatch.setitem(KNOBS, "findings_dir", str(findings.relative_to(tmp_path)))
    return tmp_path


@pytest.fixture
def seeded_repo(tmp_findings_repo: Path) -> Path:
    """Pre-seed 4 findings covering each severity/status combo:
    F-001 P1 accepted  (F-1 from real self-review)
    F-002 P0 fixed     (F-2 from real self-review)
    F-003 P0 fixed     (F-3 from real self-review)
    F-004 P2 open      (F-23 from real self-review — kept open for verify test)
    """
    repo = tmp_findings_repo
    fd = repo / KNOBS["findings_dir"]
    today = date.today().isoformat()
    seeds = [
        ("001", "P1", "multi-replace state desync", "accepted", "l3-closure"),
        ("002", "P0", "pre-commit frontmatter parser", "fixed", "l3-closure"),
        ("003", "P0", "runtime_safety substring matcher", "fixed", "l3-closure"),
        ("004", "P2", "reflexion empty-file append", "open", "l4-closure"),
    ]
    for num, sev, title, status, phase in seeds:
        (fd / f"F-{num}-{title.replace(chr(32), '-')}.md").write_text(
            f"""---
id: F-{num}
severity: {sev}
title: {title}
status: {status}
added: {today}
closed: {today if status != 'open' else ''}
phase: {phase}
---

## Root cause

seeded for test

## Fix

seeded for test

## Lesson

seeded for test
""",
            encoding="utf-8",
        )
    return repo


# ---------- Test 1: record creates a valid file with auto-incremented id ----------

def test_record_finding_creates_file_and_returns_next_id(
    tmp_findings_repo: Path,
) -> None:
    """Recording F-001 in empty dir → file exists, id returned = 'F-001'."""
    fid = record_finding(
        repo=tmp_findings_repo,
        severity="P0",
        title="my first finding",
        root_cause="because",
        fix="the fix",
        lesson="the lesson",
    )
    assert fid == "F-001", f"expected F-001, got {fid}"
    files = list((tmp_findings_repo / KNOBS["findings_dir"]).iterdir())
    assert len(files) == 1
    content = files[0].read_text(encoding="utf-8")
    # Real frontmatter — not just a placeholder
    assert "id: F-001" in content
    assert "severity: P0" in content
    assert "status: open" in content
    assert "title: my first finding" in content


# ---------- Test 2: record auto-increments past existing max ----------

def test_record_finding_auto_increments(seeded_repo: Path) -> None:
    """Seeded dir has F-001..F-004 → next id must be F-005."""
    fid = record_finding(
        repo=seeded_repo,
        severity="P1",
        title="another finding",
        root_cause="r",
        fix="f",
        lesson="l",
    )
    assert fid == "F-005", f"expected F-005 after seeded max F-004, got {fid}"


# ---------- Test 3: list_findings filters by severity ----------

def test_list_findings_filters_by_severity(seeded_repo: Path) -> None:
    p0 = list_findings(seeded_repo, severity="P0")
    assert len(p0) == 2
    assert {f.id for f in p0} == {"F-002", "F-003"}
    p1 = list_findings(seeded_repo, severity="P1")
    assert len(p1) == 1
    assert p1[0].id == "F-001"
    all_f = list_findings(seeded_repo)
    assert len(all_f) == 4


# ---------- Test 4: verify_findings returns stale_p0 = [] when all fixed ----------

def test_verify_findings_stale_p0_is_empty_when_fixed(seeded_repo: Path) -> None:
    """Seeded P0 findings (F-002, F-003) are both 'fixed' → stale_p0 should
    be empty list, not None and not containing them."""
    report = verify_findings(seeded_repo)
    assert isinstance(report, VerifyReport)
    assert report.stale_p0 == []
    assert report.fixed_count == 2
    assert report.accepted_count == 1
    assert report.open_count == 1


# ---------- Test 5: verify_findings detects stale P0 (regression guard) ----------

def test_verify_findings_flags_unfixed_p0(tmp_findings_repo: Path) -> None:
    """Write a single P0 finding with status=open → verify must flag it as stale.
    This is the actual regression-guard for F-2 / F-3 — if someone fixes the
    code but forgets to update finding status, this test fails."""
    fd = tmp_findings_repo / KNOBS["findings_dir"]
    today = date.today().isoformat()
    (fd / "F-001-stale-p0.md").write_text(
        f"""---
id: F-001
severity: P0
title: stale p0
status: open
added: {today}
closed:
phase: l4-closure
---

## Root cause

stale

## Fix

stale

## Lesson

stale
""",
        encoding="utf-8",
    )
    report = verify_findings(tmp_findings_repo)
    assert len(report.stale_p0) == 1
    assert report.stale_p0[0].id == "F-001"
    assert report.stale_p0[0].status == "open"


# ---------- Test 6: generate_report produces phase markdown with counts ----------

def test_generate_report_contains_findings_and_counts(seeded_repo: Path) -> None:
    """Report must be valid Markdown with table of findings and counts."""
    md = generate_report(seeded_repo, phase_id="l4-closure")
    assert "# Self-Review Report — l4-closure" in md
    # All 4 finding IDs should appear
    for fid in ("F-001", "F-002", "F-003", "F-004"):
        assert fid in md
    # Count summary
    assert "Total: 4" in md
    assert "P0: 2" in md
    assert "P1: 1" in md
    assert "P2: 1" in md


# ---------- Test 7: edge — invalid severity rejected ----------

def test_record_finding_rejects_invalid_severity(tmp_findings_repo: Path) -> None:
    """Protocol integrity: only P0/P1/P2 accepted, anything else raises.
    Catches the case where a future contributor typos 'P9' or 'critical'."""
    with pytest.raises(ValueError, match="severity"):
        record_finding(
            repo=tmp_findings_repo,
            severity="P9",  # invalid
            title="bad",
            root_cause="r",
            fix="f",
            lesson="l",
        )
    # And nothing was written
    assert list((tmp_findings_repo / KNOBS["findings_dir"]).iterdir()) == []


# ---------- Test 8: CLI smoke — `python3 scripts/self_review.py list` ----------

def test_cli_list_subcommand_runs(tmp_findings_repo: Path) -> None:
    """The CLI is the agent-facing surface. Ensure `list` exits 0 and prints
    Markdown table even when dir is empty (with friendly 'no findings' line).
    """
    repo = tmp_findings_repo
    scripts_dir = SCRIPTS_DIR
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "self_review.py"),
         "list", "--repo", str(repo)],
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert "no findings" in result.stdout.lower() or "F-" in result.stdout
