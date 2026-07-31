"""M3 C3 — three pilot chains × success|node_fail|comp_fail."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from chain_fixtures import (  # noqa: E402
    all_chain_specs,
    compensation_recovery_rate,
    manual_non_compensable_ok,
    run_all_modes,
    run_chain,
)


@pytest.fixture(scope="module")
def specs():
    return all_chain_specs()


def test_three_pilot_chains_present(specs):
    ids = {s.id for s in specs}
    assert ids == {
        "elb-target-remediation",
        "rds-failover-route53",
        "ecs-deploy-elb-health",
    }


@pytest.mark.parametrize("mode", ["success", "node_fail", "comp_fail"])
@pytest.mark.parametrize(
    "chain_id",
    ["elb-target-remediation", "rds-failover-route53", "ecs-deploy-elb-health"],
)
def test_chain_mode_matches_expectation(specs, chain_id, mode, tmp_path):
    spec = next(s for s in specs if s.id == chain_id)
    result = run_chain(spec, mode, shadow_dir=tmp_path / chain_id / mode)
    if mode == "success":
        assert result.status == "PASS", result
    elif mode == "node_fail":
        assert result.status == spec.expect_on_node_fail, result
    else:
        assert result.status == spec.expect_on_comp_fail, result


def test_matrix_recovery_rate_and_manual_gate(tmp_path):
    results = run_all_modes(shadow_root=tmp_path / "chains")
    assert len(results) == 9  # 3 × 3
    rate = compensation_recovery_rate(results)
    assert rate >= 0.9, rate
    assert manual_non_compensable_ok(results) is True


def test_cli_run_all(tmp_path):
    out = tmp_path / "report.json"
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "chain_fixtures.py"),
            "run",
            "--all",
            "--shadow-root",
            str(tmp_path / "shadow"),
            "--out",
            str(out),
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["count"] == 9
    assert payload["compensation_recovery_rate"] >= 0.9
    assert payload["manual_non_compensable_ok"] is True
