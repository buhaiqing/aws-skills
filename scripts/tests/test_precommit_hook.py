"""TDD tests for scripts/hooks/pre-commit — L3 §12 automation + L4 #4 hard gate.

Tests run real subprocess against the actual hook script. Use tmp_path
git repos to isolate; the hook accepts REPO_ROOT env var to override the
auto-detected toplevel (for testability).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / "scripts" / "hooks" / "pre-commit"
INSTALL_HOOKS = REPO / "scripts" / "install-hooks.sh"
AGENTS_MD = REPO / "AGENTS.md"


def _init_tmp_repo(tmp_path: Path) -> Path:
    """Initialize a fresh git repo at tmp_path; return it."""
    if (tmp_path / ".git").exists():
        shutil.rmtree(tmp_path / ".git")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    return tmp_path


def _run_hook_in(repo_path: Path, repo_root: Path | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHON_BIN"] = sys.executable
    if repo_root is not None:
        env["REPO_ROOT"] = str(repo_root)
    return subprocess.run(
        ["bash", str(HOOK)],
        capture_output=True, text=True, env=env, cwd=str(repo_path),
        timeout=30,
    )


def test_hook_exits_zero_with_empty_staging(tmp_path):
    """No staged files → hook exits 0."""
    repo = _init_tmp_repo(tmp_path)
    result = _run_hook_in(repo, repo_root=tmp_path)
    assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"


def test_hook_exits_one_when_skill_md_references_missing_dir(tmp_path):
    """SKILL.md with cross_skill_deps: [aws-nonexistent-ops] → exit 1 + mentions missing."""
    repo = _init_tmp_repo(tmp_path)
    bad = repo / "aws-bogus-ops"
    bad.mkdir()
    (bad / "SKILL.md").write_text(
        "---\nname: aws-bogus-ops\nlicense: MIT\ncompatibility: t\nmetadata:\n"
        "  author: t\n  cross_skill_deps:\n    - aws-nonexistent-ops\n---\n# bad\n"
    )
    subprocess.run(["git", "-C", str(repo), "add", "aws-bogus-ops/SKILL.md"], check=True)
    result = _run_hook_in(repo, repo_root=repo)
    assert result.returncode != 0, f"hook should fail; stdout={result.stdout}\nstderr={result.stderr}"
    combined = (result.stdout + result.stderr).lower()
    assert "missing" in combined or "fail" in combined


def test_hook_exits_one_when_skill_md_violates_te_gate_g1(tmp_path):
    """SKILL.md > 120 lines → te_gate G1 fails → hook exits 1."""
    repo = _init_tmp_repo(tmp_path)
    skill = repo / "aws-toolong-ops"
    skill.mkdir()
    lines = ["---\nname: aws-toolong-ops\nlicense: MIT\ncompatibility: t\nmetadata:\n  author: t\n---\n# long"]
    lines += [f"padding line {i}" for i in range(200)]  # total > 120 lines
    (skill / "SKILL.md").write_text("\n".join(lines))
    subprocess.run(["git", "-C", str(repo), "add", "aws-toolong-ops/SKILL.md"], check=True)
    result = _run_hook_in(repo, repo_root=repo)
    assert result.returncode != 0, f"hook should fail; stdout={result.stdout}\nstderr={result.stderr}"


def test_install_hooks_sh_sets_core_hooks_path(tmp_path):
    """scripts/install-hooks.sh must set core.hooksPath to scripts/hooks.

    NOTE: We use a tmp_path git repo because REPO's .git/config may be
    read-only in sandboxed environments. install-hooks.sh logic is identical
    regardless of cwd (it just calls `git config core.hooksPath`).
    """
    repo = _init_tmp_repo(tmp_path)
    orig = subprocess.run(
        ["git", "config", "--get", "core.hooksPath"],
        capture_output=True, text=True, cwd=str(repo),
    ).stdout.strip()
    try:
        result = subprocess.run(
            ["bash", str(INSTALL_HOOKS)], capture_output=True, text=True, cwd=str(repo),
            timeout=10,
        )
        assert result.returncode == 0, f"install failed: {result.stderr}"
        got = subprocess.run(
            ["git", "config", "--get", "core.hooksPath"],
            capture_output=True, text=True, cwd=str(repo),
        ).stdout.strip()
        assert got == "scripts/hooks", f"hooksPath was: {got!r}"
    finally:
        subprocess.run(
            ["git", "config", "--unset", "core.hooksPath"],
            cwd=str(repo), check=False, capture_output=True,
        )
        if orig:
            subprocess.run(
                ["git", "config", "core.hooksPath", orig],
                cwd=str(repo), check=False, capture_output=True,
            )


def test_agents_md_section_12_contains_precommit_hard_gate():
    """AGENTS.md must contain 'Pre-commit Hard Gate' section + hook path reference."""
    text = AGENTS_MD.read_text()
    assert "Pre-commit Hard Gate" in text, "AGENTS.md missing 'Pre-commit Hard Gate' heading"
    assert "scripts/hooks/pre-commit" in text, "AGENTS.md missing hook path reference"


def test_hook_is_idempotent_with_empty_staging(tmp_path):
    """Run hook 2x with empty staging → both exit 0."""
    repo = _init_tmp_repo(tmp_path)
    for _ in range(2):
        result = _run_hook_in(repo, repo_root=repo)
        assert result.returncode == 0, f"stderr: {result.stderr}"


# --- F-2: frontmatter markdown-link parsing ---

def test_hook_detects_markdown_link_dep_to_missing_dir(tmp_path):
    """SKILL.md with `cross_skill_deps:` in markdown-link form must still flag missing dirs.

    Current awk-based parser silently drops `[aws-foo-ops](../aws-foo-ops)`
    because the regex does not match the leading `[`. Fix: extract via
    a Python helper that handles both plain labels and markdown links.
    """
    repo = _init_tmp_repo(tmp_path)
    bad = repo / "aws-bogus-ops"
    bad.mkdir()
    (bad / "SKILL.md").write_text(
        "---\nname: aws-bogus-ops\nlicense: MIT\ncompatibility: t\nmetadata:\n"
        "  author: t\n  cross_skill_deps:\n"
        "    - [aws-nonexistent-ops](../aws-nonexistent-ops)\n---\n# bad\n"
    )
    subprocess.run(["git", "-C", str(repo), "add", "aws-bogus-ops/SKILL.md"], check=True)
    result = _run_hook_in(repo, repo_root=repo)
    assert result.returncode != 0, (
        f"hook should fail on missing markdown-link dep; "
        f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    )


def test_hook_accepts_markdown_link_dep_to_existing_dir(tmp_path):
    """SKILL.md with markdown-link dep to a REAL existing dir must pass (no false fail)."""
    repo = _init_tmp_repo(tmp_path)
    skill = repo / "aws-valid-ops"
    skill.mkdir()
    target = repo / "aws-target-ops"
    target.mkdir()  # real existing dir
    (skill / "SKILL.md").write_text(
        "---\nname: aws-valid-ops\nlicense: MIT\ncompatibility: t\nmetadata:\n"
        "  author: t\n  cross_skill_deps:\n"
        "    - [aws-target-ops](../aws-target-ops)\n---\n# valid\n"
    )
    subprocess.run(["git", "-C", str(repo), "add", "aws-valid-ops/SKILL.md"], check=True)
    result = _run_hook_in(repo, repo_root=repo)
    # Missing only in the marker (good case)
    assert result.returncode == 0, (
        f"hook should accept existing-dir markdown-link dep; "
        f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    )


def test_hook_blocks_on_ruff_error_in_scripts(tmp_path):
    """Layer 1: a ruff error in the linted repo's scripts/ must make the hook exit 1.

    Hermetic: the probe is injected into the SAME tmp repo the hook lints via
    REPO_ROOT, so the test neither mutates the live repo nor contradicts its
    own setup. (Prior version wrote the probe to the live scripts/ but set
    REPO_ROOT to a separate clean tmp repo, so the gate never saw the error.)
    """
    repo = _init_tmp_repo(tmp_path)
    (repo / "scripts").mkdir()
    probe = repo / "scripts" / "_lint_gate_probe.py"
    probe.write_text("x = 1; y = 2\n")  # ruff E702
    try:
        result = _run_hook_in(repo, repo_root=repo)
        assert result.returncode != 0, (
            f"hook should fail on ruff error; stdout={result.stdout!r}\nstderr={result.stderr!r}"
        )
        combined = (result.stdout + result.stderr).lower()
        assert "ruff" in combined, f"failure reason should mention ruff; got: {combined}"
    finally:
        probe.unlink()


def test_hook_passes_when_scripts_clean(tmp_path):
    """Layer 1: clean scripts/ must pass ruff gate (exit 0)."""
    repo = _init_tmp_repo(tmp_path)
    (repo / "scripts").mkdir()
    # No probe -> tmp repo's scripts/ is clean -> gate passes.
    result = _run_hook_in(repo, repo_root=repo)
    assert result.returncode == 0, (
        f"hook should pass on clean scripts; stdout={result.stdout!r}\nstderr={result.stderr!r}"
    )
