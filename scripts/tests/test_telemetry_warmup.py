"""M1 warm-up calendar clock — refuse early closeout."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))

from telemetry_warmup import closeout_check, status  # noqa: E402


def test_status_day0():
    st = status(start=date(2026, 7, 31), today=date(2026, 7, 31))
    assert st["days_elapsed"] == 0
    assert st["days_remaining"] == 30
    assert st["full_window_eligible"] is False
    assert st["auto_heal_unlocked"] is False


def test_status_day30_eligible_but_no_auto_heal():
    st = status(start=date(2026, 7, 31), today=date(2026, 8, 30))
    assert st["full_window_eligible"] is True
    assert st["auto_heal_unlocked"] is False


def test_closeout_refuses_early():
    code, st = closeout_check(start=date(2026, 7, 31), today=date(2026, 8, 1))
    assert code == 1
    assert st["adr_checkbox_allowed"] is False


def test_closeout_ok_on_day30():
    code, st = closeout_check(start=date(2026, 7, 31), today=date(2026, 8, 30))
    assert code == 0
    assert st["adr_checkbox_allowed"] is True


def test_cli_status():
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "telemetry_warmup.py"), "status",
         "--start", "2026-07-31", "--today", "2026-08-01", "--json"],
        cwd=str(REPO), capture_output=True, text=True, check=False,
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert data["days_elapsed"] == 1
    assert data["full_window_eligible"] is False
