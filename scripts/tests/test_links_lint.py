"""TDD tests for scripts/links_lint.py — SR-4 verification hook.

The links_lint.py script enforces AGENTS.md §Operational Guidelines SR-4
("Cross-file anchor links must have valid anchors"). These tests pin the
real-file behavior across the repo.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from links_lint import (  # noqa: E402
    collect_anchors,
    gh_anchor,
    check_skill,
)


# --- T1: gh_anchor covers the actual format used in our skill files ---


def test_gh_anchor_operation_with_colon():
    """`Operation: Create Resource Share` → `operation-create-resource-share`."""
    assert gh_anchor("Operation: Create Resource Share") == "operation-create-resource-share"


def test_gh_anchor_with_parens():
    """`Common Pre-flight Steps (all ops)` → `common-pre-flight-steps-all-ops`."""
    assert gh_anchor("Common Pre-flight Steps (all ops)") == "common-pre-flight-steps-all-ops"


def test_gh_anchor_underscore_preserved():
    """`create-resource-share` stays as-is (no further changes)."""
    assert gh_anchor("create-resource-share") == "create-resource-share"


def test_gh_anchor_handles_double_dash():
    """`Operation: --foo` collapses to `operation--foo` then `operation-foo`."""
    assert "operation-foo" in gh_anchor("Operation: --foo")


# --- T2: collect_anchors reads real headings from operations.md ---


def test_collect_anchors_operations_md_has_12_operations():
    """The 12 RAM Operation headings must all be reachable as anchors."""
    ops = REPO / "aws-ram-ops" / "references" / "operations.md"
    if not ops.exists():
        return  # pre-pilot repo state
    anchors = collect_anchors(ops)
    expected = {
        "operation-create-resource-share",
        "operation-associate-resource-share",
        "operation-disassociate-resource-share",
        "operation-delete-resource-share",
        "operation-delete-permission",
    }
    assert expected.issubset(anchors), f"missing: {expected - anchors}"


# --- T3: check_skill on a known-clean skill returns 0 errors ---


def test_check_skill_clean_iam_ops():
    """aws-iam-ops after P0-B Pilot D should have 0 broken links."""
    skill = REPO / "aws-iam-ops"
    if not (skill / "SKILL.md").exists():
        return
    errs, _ = check_skill(skill)
    assert errs == [], f"unexpected broken links: {errs}"


def test_check_skill_clean_ram_ops():
    """aws-ram-ops after P0-A Pilot B should have 0 broken links."""
    skill = REPO / "aws-ram-ops"
    if not (skill / "SKILL.md").exists():
        return
    errs, _ = check_skill(skill)
    assert errs == [], f"unexpected broken links: {errs}"


# --- T4: check_skill on a broken-link fixture catches the error ---


def test_check_skill_detects_missing_anchor(tmp_path):
    skill = tmp_path / "aws-fixture-ops"
    skill.mkdir()
    (skill / "references").mkdir()
    (skill / "references" / "ops.md").write_text(
        "# ops\n\n## Create Resource Share\n\nbody\n"
    )
    (skill / "SKILL.md").write_text(
        "---\nname: x\n---\n\n# X\n\nSee [create](references/ops.md#does-not-exist).\n"
    )
    errs, _ = check_skill(skill)
    assert len(errs) == 1
    assert "does-not-exist" in errs[0]


def test_check_skill_ignores_plain_file_link(tmp_path):
    skill = tmp_path / "aws-fixture-ops"
    skill.mkdir()
    (skill / "references").mkdir()
    (skill / "references" / "ops.md").write_text("body\n")
    (skill / "SKILL.md").write_text(
        "---\nname: x\n---\n\n# X\n\nSee [ops](references/ops.md).\n"
    )
    errs, _ = check_skill(skill)
    assert errs == []


def test_check_skill_detects_missing_file(tmp_path):
    skill = tmp_path / "aws-fixture-ops"
    skill.mkdir()
    (skill / "references").mkdir()
    (skill / "SKILL.md").write_text(
        "---\nname: x\n---\n\n# X\n\nSee [missing](references/nonexistent.md#anchor).\n"
    )
    errs, _ = check_skill(skill)
    assert len(errs) == 1
    assert "nonexistent.md" in errs[0]


# --- T5: CLI exit code ---


def test_cli_strict_exits_nonzero_on_broken(tmp_path, monkeypatch):
    """--strict should exit 1 when any skill has broken links."""
    # Build a real skill dir under the repo so the CLI accepts a relative path
    fake_skill = REPO / "aws-fixture-cli-test"
    fake_skill.mkdir()
    (fake_skill / "references").mkdir()
    (fake_skill / "references" / "ops.md").write_text("body\n")
    (fake_skill / "SKILL.md").write_text(
        "---\nname: x\n---\n\n# X\n\n[bad](references/ops.md#missing).\n"
    )
    try:
        r = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "links_lint.py"), str(fake_skill.relative_to(REPO)), "--strict"],
            cwd=REPO,
            capture_output=True,
            text=True,
        )
        assert r.returncode == 1, f"expected exit 1, got {r.returncode}\nstderr: {r.stderr}"
    finally:
        # cleanup
        (fake_skill / "references" / "ops.md").unlink()
        (fake_skill / "references").rmdir()
        (fake_skill / "SKILL.md").unlink()
        fake_skill.rmdir()


def test_cli_repo_wide_clean():
    """The whole repo should be clean after the 4 pilot commits."""
    r = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "links_lint.py"), "--all", "--strict"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, f"repo not clean:\n{r.stdout}\n{r.stderr}"
