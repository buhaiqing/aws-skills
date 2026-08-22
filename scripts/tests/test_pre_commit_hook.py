"""TDD tests for Fix #4 — CodeGraph pre-commit hard-fail + --no-codegraph flag.

Per `docs/superpowers/specs/2026-08-22-maturity-honesty-debt-design.md` §4.4 and
plan T4: hook entry must `command -v codegraph` check; missing + no flag →
exit 1; missing + --no-codegraph → exit 0 + warn; present → run sync.

Tests run the real bash hook via subprocess with PATH/REPO_ROOT env
manipulation, NOT a re-implementation. The hermetic test repo lives in
tmp_path; the hook lints that tmp_path via REPO_ROOT.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "hooks" / "pre-commit"


def _init_tmp_repo(tmp_path: Path) -> Path:
    if (tmp_path / ".git").exists():
        shutil.rmtree(tmp_path / ".git")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    return tmp_path


def _make_fake_codegraph(tmp_path: Path, exit_code: int) -> Path:
    """Write a fake `codegraph` binary in tmp_path/fakebin that exits given code."""
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir(exist_ok=True)
    cg = bin_dir / "codegraph"
    cg.write_text(f"#!/bin/bash\nexit {exit_code}\n")
    cg.chmod(0o755)
    return bin_dir


def _run_hook(
    repo: Path,
    *,
    path: str | None = None,
    args: list[str] | None = None,
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHON_BIN"] = sys.executable
    env["REPO_ROOT"] = str(repo)
    if path is not None:
        env["PATH"] = path
    return subprocess.run(
        ["bash", str(HOOK), *(args or [])],
        capture_output=True, text=True, env=env, cwd=str(repo), timeout=30,
    )


def _stage_clean_py(repo: Path) -> None:
    """Stage a ruff-clean .py file so the hook's codegraph branch fires."""
    (repo / "x.py").write_text("# empty\n")
    subprocess.run(["git", "-C", str(repo), "add", "x.py"], check=True)


# --- RED: 4 tests covering the 4 paths in spec §4.4 ---


def test_missing_codegraph_default_exits_1(tmp_path):
    """codegraph NOT on PATH + no flag → hook exits 1 + stderr mentions install."""
    repo = _init_tmp_repo(tmp_path)
    _stage_clean_py(repo)
    result = _run_hook(repo, path="/usr/bin:/bin")
    assert result.returncode == 1, (
        f"expected exit 1; got {result.returncode}\n"
        f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    )
    assert "codegraph not installed" in result.stderr.lower(), (
        f"stderr should mention 'codegraph not installed'; got: {result.stderr!r}"
    )


def test_missing_codegraph_with_flag_exits_0(tmp_path):
    """codegraph NOT on PATH + --no-codegraph flag → hook exits 0 + stderr warns."""
    repo = _init_tmp_repo(tmp_path)
    _stage_clean_py(repo)
    result = _run_hook(repo, path="/usr/bin:/bin", args=["--no-codegraph"])
    assert result.returncode == 0, (
        f"expected exit 0 with --no-codegraph; got {result.returncode}\n"
        f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    )
    combined = (result.stdout + result.stderr).lower()
    assert "--no-codegraph" in combined, (
        f"stderr should mention --no-codegraph flag; got: {combined!r}"
    )


def test_present_codegraph_sync_success_exits_0(tmp_path):
    """codegraph present + sync exit 0 → hook exits 0."""
    repo = _init_tmp_repo(tmp_path)
    _stage_clean_py(repo)
    fakebin = _make_fake_codegraph(tmp_path, exit_code=0)
    result = _run_hook(repo, path=f"{fakebin}:/usr/bin:/bin")
    assert result.returncode == 0, (
        f"expected exit 0 when codegraph sync ok; got {result.returncode}\n"
        f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    )


def test_present_codegraph_sync_failure_exits_1(tmp_path):
    """codegraph present + sync exit 1 → hook exits 1."""
    repo = _init_tmp_repo(tmp_path)
    _stage_clean_py(repo)
    fakebin = _make_fake_codegraph(tmp_path, exit_code=1)
    result = _run_hook(repo, path=f"{fakebin}:/usr/bin:/bin")
    assert result.returncode == 1, (
        f"expected exit 1 when codegraph sync fails; got {result.returncode}\n"
        f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    )
