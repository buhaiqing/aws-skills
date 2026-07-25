"""TDD tests for scripts/cross_runtime_lint.py — L4 #11 portability.

Static linter: scans SKILL.md content for runtime-specific hardcodes
(paths to ~/.codex, ~/.claude, /Users/, etc.) and reports a
portability score per skill.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from cross_runtime_lint import (  # noqa: E402
    detect_runtime_coupling,
    score_portability,
    lint_repo,
)


def _write_skill(tmp_path: Path, name: str, body: str) -> Path:
    skill_dir = tmp_path / name
    skill_dir.mkdir(exist_ok=True)
    p = skill_dir / "SKILL.md"
    p.write_text(body)
    return p


def test_detect_finds_codex_specific_path(tmp_path):
    """Mention of `~/.codex/` triggers a CouplingHit with runtime='codex'."""
    skill = _write_skill(tmp_path, "x", (
        "---\nname: x\n---\n\n"
        "Configure hook in `~/.codex/config.toml`.\n"
    ))
    hits = detect_runtime_coupling(skill)
    assert any(h.runtime == "codex" for h in hits)
    codex_hits = [h for h in hits if h.runtime == "codex"]
    assert "~/.codex/" in codex_hits[0].pattern


def test_detect_finds_multiple_runtimes_in_same_skill(tmp_path):
    """Skill mentioning codex + claude + cursor → 3 separate hits."""
    body = (
        "Use `~/.codex/config.toml`, `~/.claude/settings.json`, "
        "and `~/.cursor/settings.json` for hooks.\n"
    )
    skill = _write_skill(tmp_path, "multi", body)
    hits = detect_runtime_coupling(skill)
    runtimes = {h.runtime for h in hits}
    assert runtimes >= {"codex", "claude", "cursor"}


def test_score_perfect_for_clean_skill(tmp_path):
    """Skill without any runtime-specific pattern → score 1.0."""
    skill = _write_skill(tmp_path, "clean", (
        "# Portable skill\n"
        "Run `aws s3 ls` to list objects.\n"
        "Use `python3 scripts/runtime_safety.py` to validate.\n"
    ))
    score = score_portability(skill)
    assert score >= 0.95


def test_score_drops_with_home_path_hits(tmp_path):
    """Skill with /Users/ in content → score drops below 1.0."""
    skill = _write_skill(tmp_path, "hostpath", (
        "Run `python3 /Users/me/projects/aws-skills/scripts/runtime_safety.py`\n"
    ))
    score = score_portability(skill)
    assert score < 1.0
    assert score >= 0.0


def test_lint_repo_returns_dict_with_all_skills(tmp_path, monkeypatch):
    """lint_repo on a tmp repo with 3 skills → dict of 3 reports."""
    # Create a sandboxed fake repo
    fake_repo = tmp_path / "aws-fake"
    fake_repo.mkdir()
    for s in ("aws-a-ops", "aws-b-ops", "aws-c-ops"):
        (fake_repo / s).mkdir()
        (fake_repo / s / "SKILL.md").write_text(
            f"# {s}\nNo runtime-specific paths.\n"
        )
    monkeypatch.setattr("cross_runtime_lint.REPO", fake_repo)
    reports = lint_repo(repo=fake_repo)
    # 3 skills (also AGENTS.md is a special dir-name but not aws-*-ops)
    skill_reports = {k: v for k, v in reports.items() if k.startswith("aws-")}
    assert len(skill_reports) >= 3


def test_cli_lint_subprocess_writes_markdown(tmp_path, monkeypatch):
    """`cross_runtime_lint.py lint --skill X` exits 0 + writes Markdown."""
    skill = _write_skill(tmp_path, "x", "# x\nPortable.\n")
    fake_repo = tmp_path / "fake"
    fake_repo.mkdir()
    skill_in_fake = fake_repo / "aws-x-ops"
    skill_in_fake.mkdir()
    (skill_in_fake / "SKILL.md").write_text(skill.read_text())
    # Pass fake repo via REPO env (simplest approach for CLI)
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "cross_runtime_lint.py"),
         "lint", "--skill", "aws-x-ops", "--repo", str(fake_repo),
         "--json"],
        capture_output=True, text=True, timeout=15,
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    payload = json.loads(proc.stdout)
    assert "aws-x-ops" in payload
    r = payload["aws-x-ops"]
    assert "score" in r
    assert "hits" in r
    assert r["score"] >= 0.95
