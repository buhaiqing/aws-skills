"""RED tests for composite_lint.py — P0 L2.2 closure.

Verifies composite/orchestrator-meta skills' delegate: blocks:
- target dir exists
- operations are in target's provides: (or accepts:)

Per AGENTS.md §13 CADL: tests FAIL before impl exists.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from composite_lint import (  # noqa: E402
    lint_composite,
    lint_repo,
)


# ---------- Fixtures ----------

@pytest.fixture
def composite_repo(tmp_path: Path) -> Path:
    """Build a self-contained repo with 4 skills for testing.

    Layout:
      aws-aiops-copilot/SKILL.md       (composite, valid)
      aws-aiops-cruise/SKILL.md        (target, provides rca/health-check)
      aws-aiops-orchestrator/SKILL.md  (target, provides cross-service-rca)
      aws-broken-composite/SKILL.md    (composite, target dir missing)
      aws-mismatch-op/SKILL.md         (composite, op not in target.provides)
      aws-empty-delegate/SKILL.md      (composite, empty delegate — score 1.0)
    """
    repo = tmp_path

    def _w(rel: str, content: str) -> None:
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    # Valid composite
    _w("aws-aiops-copilot/SKILL.md", _fm(
        type_="composite",
        provides=["aiops-rca"],
        delegate={
            "aws-aiops-cruise": ["rca", "health-check"],
            "aws-aiops-orchestrator": ["cross-service-rca"],
        },
    ))

    # Targets with proper provides
    _w("aws-aiops-cruise/SKILL.md", _fm(
        type_="cross-product-aiops-cruise",
        provides=["rca", "health-check", "pre-flight-check"],
    ))
    _w("aws-aiops-orchestrator/SKILL.md", _fm(
        type_="orchestrator-meta",
        provides=["cross-service-rca", "capacity-forecast"],
    ))

    # Broken: target dir missing
    _w("aws-broken-composite/SKILL.md", _fm(
        type_="composite",
        provides=["x"],
        delegate={"aws-does-not-exist": ["y"]},
    ))

    # Mismatch: target exists but operation not in provides
    _w("aws-mismatch-op/SKILL.md", _fm(
        type_="composite",
        provides=["x"],
        delegate={"aws-aiops-cruise": ["rca", "ghost-op"]},
    ))

    # Empty delegate
    _w("aws-empty-delegate/SKILL.md", _fm(
        type_="composite",
        provides=["x"],
        delegate={},
    ))

    return repo


def _fm(type_: str, provides: list[str], delegate: dict | None = None) -> str:
    """Build a minimal SKILL.md frontmatter with `delegate:` under `metadata:`."""
    delegate_block = ""
    if delegate is not None:
        # Indent: delegate under metadata (2 spaces), target under delegate (4 spaces),
        # ops under target (6 spaces) — mirrors real skill frontmatter.
        delegate_block = "  delegate:\n"
        for tgt, ops in delegate.items():
            delegate_block += f"    {tgt}:\n"
            for op in ops:
                delegate_block += f"      - {op}\n"
    return (
        f"---\n"
        f"name: test-skill\n"
        f"description: test\n"
        f"license: MIT\n"
        f"compatibility: test\n"
        f"metadata:\n"
        f"  type: {type_}\n"
        f"  provides:\n"
        + "".join(f"  - {p}\n" for p in provides)
        + delegate_block
        + "---\n\n# Test\n"
    )


# ---------- Test 1: valid composite → score 1.0 ----------

def test_valid_composite_returns_perfect_score(composite_repo: Path) -> None:
    report = lint_composite(
        composite_repo / "aws-aiops-copilot" / "SKILL.md",
        repo=composite_repo,
    )
    assert report.score == 1.0
    assert report.issues == []
    # 3 delegate refs (2 to cruise + 1 to orch)
    assert len(report.refs) == 3
    targets = {(r.target, r.operation) for r in report.refs}
    assert ("aws-aiops-cruise", "rca") in targets
    assert ("aws-aiops-cruise", "health-check") in targets
    assert ("aws-aiops-orchestrator", "cross-service-rca") in targets


# ---------- Test 2: missing target dir → issue ----------

def test_missing_target_dir_creates_issue(composite_repo: Path) -> None:
    report = lint_composite(
        composite_repo / "aws-broken-composite" / "SKILL.md",
        repo=composite_repo,
    )
    assert report.score < 1.0
    assert len(report.issues) == 1
    issue = report.issues[0]
    assert issue.issue == "target_dir_missing"
    assert issue.target == "aws-does-not-exist"
    assert issue.operation == "y"


# ---------- Test 3: operation not in target's provides → issue ----------

def test_operation_not_provided_creates_issue(composite_repo: Path) -> None:
    report = lint_composite(
        composite_repo / "aws-mismatch-op" / "SKILL.md",
        repo=composite_repo,
    )
    assert report.score < 1.0
    issues_by_op = {(i.target, i.operation): i.issue for i in report.issues}
    assert ("aws-aiops-cruise", "rca") not in issues_by_op  # this is valid
    assert ("aws-aiops-cruise", "ghost-op") in issues_by_op
    assert issues_by_op[("aws-aiops-cruise", "ghost-op")] == "operation_not_provided"


# ---------- Test 4: empty delegate → score 1.0 ----------

def test_empty_delegate_block_scores_perfect(composite_repo: Path) -> None:
    """Edge case: composite with no delegate refs. Vacuously clean."""
    report = lint_composite(
        composite_repo / "aws-empty-delegate" / "SKILL.md",
        repo=composite_repo,
    )
    assert report.score == 1.0
    assert report.issues == []
    assert report.refs == []


# ---------- Test 5: lint_repo returns dict for all composites ----------

def test_lint_repo_returns_all_composites(composite_repo: Path) -> None:
    """lint_repo must walk the repo and return one report per composite skill."""
    reports = lint_repo(composite_repo)
    parents = set(reports.keys())
    assert "aws-aiops-copilot" in parents
    assert "aws-broken-composite" in parents
    assert "aws-mismatch-op" in parents
    assert "aws-empty-delegate" in parents
    # Targets are NOT composite (they're base/orchestrator-meta/cruise)
    assert "aws-aiops-cruise" not in parents
    # aws-aiops-orchestrator IS in lint output (orchestrator-meta ∈ composite_types)


# ---------- Test 6: composite with accepts: style target (aiops-cruise) ----------


def _w_at(repo: Path, rel: str, content: str) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
def test_composite_lint_accepts_accepts_style(composite_repo: Path) -> None:
    """Some targets like aws-aiops-cruise use `delegate.accepts:` instead of
    `metadata.provides:`. Lint must check BOTH sources.
    """
    # Modify cruise to use accepts style only
    cruise_fm = _fm(
        type_="cross-product-aiops-cruise",
        provides=[],
        delegate={"accepts": ["rca", "health-check"]},
    )
    _w_at(composite_repo, "aws-aiops-cruise/SKILL.md", cruise_fm)
    report = lint_composite(
        composite_repo / "aws-aiops-copilot" / "SKILL.md",
        repo=composite_repo,
    )
    # All 3 ops should now be found via accepts: source
    issues = {(i.target, i.operation) for i in report.issues}
    assert issues == set(), f"unexpected issues: {issues}"
    assert report.score == 1.0


# ---------- Test 7: non-composite skill is skipped by lint_repo ----------

def test_lint_repo_skips_base_skills(composite_repo: Path, tmp_path: Path) -> None:
    """A base skill (no composite type) should NOT appear in lint_repo output."""
    # Add a base skill that happens to be in the repo
    _w_at(composite_repo, "aws-base-skill/SKILL.md", _fm(
        type_="base",
        provides=["ec2-describe"],
        delegate={"aws-iam-ops": ["get-role"]},
    ))
    reports = lint_repo(composite_repo)
    assert "aws-base-skill" not in reports


# ---------- Test 8: CLI exits 0 on clean, 1 on dirty ----------

def test_cli_exit_code_reflects_issues(composite_repo: Path) -> None:
    """Real CLI invocation: --all on a dirty repo (broken + mismatch) should exit 1.
    This is the regression-guard for the CI gate (L2.1 / L4.1 closure)."""
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "composite_lint.py"),
         "lint", "--all", "--repo", str(composite_repo)],
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 1, (
        f"expected exit 1 (broken/mismatch composites present), "
        f"got {result.returncode}; stderr={result.stderr}"
    )
    assert "target_dir_missing" in result.stdout
    assert "operation_not_provided" in result.stdout
