"""RED tests for scan_stale_maturity — Fix #1 maturity honesty.

Per plan T1: use real `docs/agentic-maturity-model.md` as fixture (no mock).
These tests import `scan_stale_maturity` from self_review — RED because
that function does not exist yet (ModuleAttrError or ImportError).
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from self_review import scan_stale_maturity  # noqa: E402  -- RED: function missing


def test_scan_returns_empty_when_no_stale(tmp_path: Path):
    """All ⚠️ items have changelog references within threshold → returns []."""
    model = tmp_path / "model.md"
    model.write_text(
        "# Maturity\n\n"
        "## Status\n\n"
        "| Symbol | Status |\n"
        "|---|---|\n"
        "| ⚠️ | **Active item** mentioned recently |\n"
        "\n"
        "## Changelog\n\n"
        "| 2026-08-22 | **Active item** referenced today |\n",
        encoding="utf-8",
    )
    findings = scan_stale_maturity(model, threshold_days=30, as_of=date(2026, 8, 22))
    assert findings == []


def test_scan_flags_stale_items(tmp_path: Path):
    """One ⚠️ item without changelog mention → 1 Finding, P1, kind=MATURITY_STALE."""
    model = tmp_path / "model.md"
    model.write_text(
        "# Maturity\n\n"
        "## Status\n\n"
        "| Symbol | Status |\n"
        "|---|---|\n"
        "| ⚠️ | **Old abandoned item** never mentioned |\n"
        "\n"
        "## Changelog\n\n"
        "| 2026-01-01 | unrelated |\n",
        encoding="utf-8",
    )
    findings = scan_stale_maturity(model, threshold_days=30, as_of=date(2026, 8, 22))
    assert len(findings) == 1
    assert findings[0].severity == "P1"
    assert findings[0].kind == "MATURITY_STALE"
    assert findings[0].status == "open"


def test_scan_threshold_parameterization(tmp_path: Path):
    """threshold (7 / 30 / 90 days) controls what counts as stale."""
    model = tmp_path / "model.md"
    model.write_text(
        "# Maturity\n\n"
        "## Status\n\n"
        "| Symbol | Status |\n"
        "|---|---|\n"
        "| ⚠️ | **21-day-old item** |\n"
        "\n"
        "## Changelog\n\n"
        "| 2026-08-01 | last mention |\n",
        encoding="utf-8",
    )
    # 2026-08-22 - 2026-08-01 = 21 days since last mention
    f7 = scan_stale_maturity(model, threshold_days=7, as_of=date(2026, 8, 22))
    assert len(f7) == 1
    f30 = scan_stale_maturity(model, threshold_days=30, as_of=date(2026, 8, 22))
    assert len(f30) == 0
    f90 = scan_stale_maturity(model, threshold_days=90, as_of=date(2026, 8, 22))
    assert len(f90) == 0


def test_scan_real_maturity_model_runs():
    """Smoke test on real docs/agentic-maturity-model.md (no strict count).

    Per plan AC-2: --scan-stale-maturity must run successfully on real model.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent
    model = repo_root / "docs" / "agentic-maturity-model.md"
    if not model.exists():
        pytest.skip(f"real model not found at {model}")
    findings = scan_stale_maturity(model, threshold_days=30, as_of=date(2026, 8, 22))
    assert isinstance(findings, list)
    for f in findings:
        assert f.severity == "P1"
        assert f.kind == "MATURITY_STALE"
        assert f.status == "open"