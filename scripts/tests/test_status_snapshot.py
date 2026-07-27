"""TDD tests for scripts/status_snapshot.py — Layer 3 evidence snapshot."""
from __future__ import annotations

import subprocess

import status_snapshot as ss


def _cp(stdout: str, stderr: str = "", returncode: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode,
                                        stdout=stdout, stderr=stderr)


def test_collect_pytest_green():
    import status_snapshot as mod

    real = mod._run
    mod._run = lambda cmd: _cp("111 passed in 2.60s\n")
    try:
        r = mod.collect_pytest()
    finally:
        mod._run = real
    assert r == {"passed": 111, "failed": 0, "error": 0, "ok": True}


def test_collect_pytest_red():
    import status_snapshot as mod

    real = mod._run
    mod._run = lambda cmd: _cp("1 failed, 110 passed in 2.76s\n", returncode=1)
    try:
        r = mod.collect_pytest()
    finally:
        mod._run = real
    assert r["failed"] == 1
    assert r["ok"] is False


def test_collect_ruff_clean():
    import status_snapshot as mod

    real = mod._run
    mod._run = lambda cmd: _cp("All checks passed!\n", returncode=0)
    try:
        r = mod.collect_ruff()
    finally:
        mod._run = real
    assert r == {"errors": 0, "ok": True}


def test_collect_ruff_errors():
    import status_snapshot as mod

    real = mod._run
    mod._run = lambda cmd: _cp("Found 5 errors.\n", returncode=1)
    try:
        r = mod.collect_ruff()
    finally:
        mod._run = real
    assert r == {"errors": 5, "ok": False}


def test_collect_composite_lint():
    import status_snapshot as mod

    real = mod._run
    mod._run = lambda cmd: _cp("", returncode=0)
    try:
        assert mod.collect_composite_lint() == {"ok": True}
    finally:
        mod._run = real


def test_collect_self_review_stale_p0():
    import status_snapshot as mod

    real = mod._run
    mod._run = lambda cmd: _cp("open=1 fixed=5 accepted=1 stale_p0=2\n")
    try:
        r = mod.collect_self_review()
    finally:
        mod._run = real
    assert r == {"stale_p0": 2, "ok": False}


def test_snapshot_all_ok_false_when_any_red():
    snap = ss.Snapshot(
        generated_at="2026-07-27",
        pytest={"passed": 1, "failed": 1, "error": 0, "ok": False},
        ruff={"errors": 0, "ok": True},
        composite_lint={"ok": True},
        self_review={"stale_p0": 0, "ok": True},
    )
    assert snap.all_ok is False
    assert "GATE RED" in snap.to_markdown()


def test_snapshot_all_ok_true_when_green():
    snap = ss.Snapshot(
        generated_at="2026-07-27",
        pytest={"passed": 111, "failed": 0, "error": 0, "ok": True},
        ruff={"errors": 0, "ok": True},
        composite_lint={"ok": True},
        self_review={"stale_p0": 0, "ok": True},
    )
    assert snap.all_ok is True
    md = snap.to_markdown()
    assert "ALL GREEN" in md
    assert "auto-generated" in md


def test_build_snapshot_composes_gates():
    """Integration: build_snapshot composes the collectors and all_ok is the AND of oks."""
    import status_snapshot as mod

    real = mod._run
    mod._run = lambda cmd: (
        _cp("111 passed in 2.60s\n")
        if "pytest" in cmd
        else _cp("All checks passed!\n")
        if "ruff" in cmd
        else _cp("")
        if "composite_lint" in cmd
        else _cp("open=0 fixed=5 accepted=1 stale_p0=0\n")
    )
    try:
        snap = mod.build_snapshot()
    finally:
        mod._run = real
    assert set(snap.pytest) == {"passed", "failed", "error", "ok"}
    assert set(snap.ruff) == {"errors", "ok"}
    assert snap.composite_lint == {"ok": True}
    assert snap.self_review == {"stale_p0": 0, "ok": True}
    assert snap.all_ok is True


def test_build_snapshot_red_when_ruff_fails():
    import status_snapshot as mod

    real = mod._run
    mod._run = lambda cmd: (
        _cp("111 passed in 2.60s\n")
        if "pytest" in cmd
        else _cp("Found 3 errors.\n", returncode=1)
        if "ruff" in cmd
        else _cp("")
        if "composite_lint" in cmd
        else _cp("stale_p0=0\n")
    )
    try:
        snap = mod.build_snapshot()
    finally:
        mod._run = real
    assert snap.ruff == {"errors": 3, "ok": False}
    assert snap.all_ok is False
