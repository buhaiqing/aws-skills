"""Tests for scripts/links_lint.py — SR-4 anchor verification."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from links_lint import (  # noqa: E402
    check_skill,
    collect_anchors,
    gh_anchor,
    lint,
    main,
)


def _make_skill(root: Path, name: str, skill_md: str, refs: dict[str, str]) -> Path:
    skill = root / name
    skill.mkdir()
    refs_dir = skill / "references"
    refs_dir.mkdir()
    for fname, body in refs.items():
        (refs_dir / fname).write_text(body, encoding="utf-8")
    (skill / "SKILL.md").write_text(skill_md, encoding="utf-8")
    return skill


# --- gh_anchor ---


def test_gh_anchor_colon_and_spaces():
    assert gh_anchor("Operation: Create Resource Share") == (
        "operation-create-resource-share"
    )


def test_gh_anchor_strips_parens():
    assert gh_anchor("Common Pre-flight Steps (all ops)") == (
        "common-pre-flight-steps-all-ops"
    )


def test_gh_anchor_collapses_double_dash():
    assert gh_anchor("Operation: --foo") == "operation-foo"


# --- fixture: ok + broken ---


def test_check_skill_ok_anchor(tmp_path):
    skill = _make_skill(
        tmp_path,
        "aws-ok-ops",
        "---\nname: ok\n---\n\nSee [x](references/ops.md#create-share).\n",
        {"ops.md": "# ops\n\n## Create Share\n\nbody\n"},
    )
    assert check_skill(skill) == []


def test_check_skill_broken_anchor(tmp_path):
    skill = _make_skill(
        tmp_path,
        "aws-broken-ops",
        "---\nname: b\n---\n\nSee [x](references/ops.md#does-not-exist).\n",
        {"ops.md": "# ops\n\n## Create Share\n\nbody\n"},
    )
    errs = check_skill(skill)
    assert len(errs) == 1
    assert "does-not-exist" in errs[0]


def test_check_skill_plain_file_link_ignored(tmp_path):
    skill = _make_skill(
        tmp_path,
        "aws-plain-ops",
        "---\nname: p\n---\n\nSee [ops](references/ops.md).\n",
        {"ops.md": "body\n"},
    )
    assert check_skill(skill) == []


def test_check_skill_missing_file(tmp_path):
    skill = _make_skill(
        tmp_path,
        "aws-miss-ops",
        "---\nname: m\n---\n\nSee [x](references/gone.md#a).\n",
        {},
    )
    errs = check_skill(skill)
    assert len(errs) == 1
    assert "gone.md" in errs[0]


def test_collect_anchors_from_fixture(tmp_path):
    skill = _make_skill(
        tmp_path,
        "aws-col-ops",
        "---\nname: c\n---\n",
        {"ops.md": "## Operation: Create\n\n## Delete (force)\n"},
    )
    anchors = collect_anchors(skill / "references" / "ops.md")
    assert "operation-create" in anchors
    assert "delete-force" in anchors


def test_lint_exit_codes(tmp_path):
    _make_skill(
        tmp_path,
        "aws-ok-ops",
        "---\nname: ok\n---\n\n[ok](references/ops.md#create-share).\n",
        {"ops.md": "## Create Share\n"},
    )
    _make_skill(
        tmp_path,
        "aws-bad-ops",
        "---\nname: bad\n---\n\n[bad](references/ops.md#missing).\n",
        {"ops.md": "## Create Share\n"},
    )
    code_ok, errs_ok = lint(tmp_path, skill="aws-ok-ops")
    assert code_ok == 0 and errs_ok == []
    code_bad, errs_bad = lint(tmp_path, skill="aws-bad-ops")
    assert code_bad == 1 and len(errs_bad) == 1


def test_cli_lint_skill_broken(tmp_path):
    _make_skill(
        tmp_path,
        "aws-cli-ops",
        "---\nname: c\n---\n\n[bad](references/ops.md#nope).\n",
        {"ops.md": "## Exists\n"},
    )
    assert main(["lint", "--repo", str(tmp_path), "--skill", "aws-cli-ops"]) == 1


def test_cli_lint_all_default_ok(tmp_path):
    _make_skill(
        tmp_path,
        "aws-only-ops",
        "---\nname: o\n---\n\n[ok](references/ops.md#exists).\n",
        {"ops.md": "## Exists\n"},
    )
    assert main(["lint", "--repo", str(tmp_path)]) == 0
    assert main(["lint", "--repo", str(tmp_path), "--all"]) == 0


def test_cli_subprocess_exits_int():
    """CLI must run against the live repo and print a status line."""
    r = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "links_lint.py"), "lint", "--all"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert "OK:" in r.stdout or "TOTAL:" in r.stdout or "SUMMARY:" in r.stdout
    assert r.returncode in (0, 1)
