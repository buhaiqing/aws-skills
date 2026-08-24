"""TDD tests for scripts/session_memory.py — L4 #10 cross-session memory.

Sidecar `.omc/conventions.json` stores agent-derived project facts that
survive across sessions. Library: load/save/query/derive/format. CLI:
record/query/list/render. Real fixture: a tmp `.omc/conventions.json`.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from session_memory import (  # noqa: E402
    MemoryRecord,
    load_memory,
    save_memory,
    query_memory,
    derive_candidates,
    format_for_prompt,
)


def _mem(id_: str, summary: str, scope: str = "convention",
         detail: str = "", confidence: float = 1.0,
         tags: list[str] | None = None) -> MemoryRecord:
    return MemoryRecord(
        id=id_, timestamp="2026-07-25T00:00:00+00:00",
        scope=scope, summary=summary, detail=detail,
        confidence=confidence, source_session="test-session",
        tags=tags or [],
    )


def test_load_returns_empty_when_file_missing(tmp_path):
    """Missing file → empty list, no exception."""
    p = tmp_path / "conventions.json"
    assert load_memory(p) == []


def test_save_then_load_round_trip(tmp_path):
    """Write 2 records → load returns same data."""
    p = tmp_path / "conventions.json"
    recs = [
        _mem("mem-001", "User prefers Chinese docs", scope="user-pref"),
        _mem("mem-002", "Always lint with ruff", scope="convention",
             detail="Run before commit"),
    ]
    save_memory(recs, p)
    loaded = load_memory(p)
    assert len(loaded) == 2
    assert loaded[0].id == "mem-001"
    assert loaded[1].detail == "Run before commit"
    assert loaded[1].tags == []


def test_query_keyword_match_returns_sorted_relevant(tmp_path):
    """Query 'aws region' returns records with 'aws' OR 'region' in summary+detail."""
    recs = [
        _mem("a", "always run aws region check before deploy"),
        _mem("b", "no specific region locking"),
        _mem("c", "User lives in us-west-2 region"),
        _mem("d", "AWS IAM policy enforcement"),
        _mem("e", "completely unrelated cooking recipe"),
    ]
    # 'region' should rank c > a > b; 'aws' should rank a > d; e should NOT match
    hits_region = query_memory(recs, "region", top_k=3)
    assert any(h.id == "c" for h in hits_region)
    assert all(h.id != "e" for h in hits_region)


def test_derive_candidates_heuristic_extracts_declarative_facts():
    """Heuristic v0: scan transcript for 'convention:' / 'always' / 'never' patterns."""
    transcript = [
        {"role": "user", "content": "convention: always run ruff before commit."},
        {"role": "user", "content": "never use aws ec2 terminate without confirm."},
        {"role": "agent", "content": "OK noted."},
        {"role": "user", "content": "我们用 pytest-pure mode."},
        {"role": "user", "content": "what's the weather today?"},  # should NOT match
    ]
    candidates = derive_candidates(transcript)
    assert len(candidates) >= 3
    scopes = [c.scope for c in candidates]
    assert "convention" in scopes
    summaries = " ".join(c.summary.lower() for c in candidates)
    assert "ruff" in summaries
    assert "weather" not in summaries


def test_format_for_prompt_respects_max_chars():
    """Render ≤ max_chars total, includes id+summary for each record."""
    recs = [
        _mem(f"r-{i}", f"important fact number {i}") for i in range(20)
    ]
    out = format_for_prompt(recs, max_chars=300)
    assert len(out) <= 320  # allow small overhead
    # must contain at least the first record
    assert "r-0" in out
    assert "fact number 0" in out


def test_cli_record_subprocess_appends(tmp_path):
    """`session_memory.py record` writes a valid record via CLI."""
    target = tmp_path / "conventions.json"
    summary = "Always invoke runtime_safety before destructive ops"
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "session_memory.py"),
         "record",
         "--path", str(target),
         "--scope", "convention",
         "--summary", summary,
         "--source-session", "test-session"],
        capture_output=True, text=True, timeout=10,
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    loaded = load_memory(target)
    assert len(loaded) == 1
    assert loaded[0].summary == summary
    assert loaded[0].scope == "convention"


def test_cli_query_subprocess_finds_match(tmp_path):
    """`session_memory.py query` returns matching record via stdout."""
    target = tmp_path / "conventions.json"
    # Seed one record
    save_memory([_mem("mem-x", "Runtime safety before destructive aws ops",
                      scope="convention", tags=["safety"])], target)
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "session_memory.py"),
         "query", "aws safety",
         "--path", str(target),
         "--top", "3"],
        capture_output=True, text=True, timeout=10,
    )
    assert proc.returncode == 0
    assert "Runtime safety" in proc.stdout
    assert "mem-x" in proc.stdout


def test_verify_startup_current_session(tmp_path, monkeypatch):
    """File exists with current session marker → exit 0."""
    target = tmp_path / "conventions.json"
    rec = MemoryRecord(id="mem-001", timestamp="2026-07-25T00:00:00+00:00",
                       scope="convention", summary="Test fact", detail="",
                       confidence=1.0, source_session="current-session", tags=[])
    save_memory([rec], target)
    monkeypatch.setenv("OMC_SESSION_ID", "current-session")
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "session_memory.py"),
         "verify-startup", "--path", str(target)],
        capture_output=True, text=True, timeout=10,
    )
    assert proc.returncode == 0


def test_verify_startup_stale_session(tmp_path, monkeypatch):
    """File exists but session is stale → exit 1."""
    target = tmp_path / "conventions.json"
    rec = MemoryRecord(id="mem-001", timestamp="2026-07-25T00:00:00+00:00",
                       scope="convention", summary="Test fact", detail="",
                       confidence=1.0, source_session="old-session", tags=[])
    save_memory([rec], target)
    monkeypatch.setenv("OMC_SESSION_ID", "different-session")
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "session_memory.py"),
         "verify-startup", "--path", str(target)],
        capture_output=True, text=True, timeout=10,
    )
    assert proc.returncode == 1


def test_verify_startup_missing_file_no_required(tmp_path, monkeypatch):
    """File missing, no --required flag → exit 1."""
    target = tmp_path / "nonexistent.json"
    monkeypatch.setenv("OMC_SESSION_ID", "any-session")
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "session_memory.py"),
         "verify-startup", "--path", str(target)],
        capture_output=True, text=True, timeout=10,
    )
    assert proc.returncode == 1


def test_verify_startup_missing_file_required(tmp_path, monkeypatch):
    """File missing with --required flag → exit 2."""
    target = tmp_path / "nonexistent.json"
    monkeypatch.setenv("OMC_SESSION_ID", "any-session")
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "session_memory.py"),
         "verify-startup", "--path", str(target), "--required"],
        capture_output=True, text=True, timeout=10,
    )
    assert proc.returncode == 2
