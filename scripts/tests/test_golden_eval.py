"""TDD tests for scripts/golden_eval.py — L4 #7 Eval-Driven Dev.

Golden suite + regression detection. The runner shells out to
`scripts/gcl_runner.py --self-test` per scenario, which avoids real AWS.
Real fixtures: tiny YAML files with ≥3 scenarios each.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from golden_eval import (  # noqa: E402
    Scenario,
    ScenarioResult,
    load_scenarios,
    run_scenario,
    compare_to_baseline,
)


def _write_scenarios_yaml(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "scenarios.yaml"
    p.write_text(body)
    return p


def _minimal_scenarios_yaml(rows: list[dict]) -> str:
    """Build a minimal but valid scenarios YAML — 1 skill, N scenarios."""
    lines = ["---", "skill: aws-x-ops", "scenarios:"]
    for r in rows:
        lines.append(f"  - id: {r['id']}")
        lines.append(f"    description: {r.get('description', '')}")
        lines.append(f"    request: {r.get('request', 'do ' + r['id'])}")
        lines.append(f"    expected_status: {r['expected_status']}")
        if r.get("user_region"):
            lines.append(f"    user_region: {r['user_region']}")
        if r.get("safety_confirm"):
            lines.append(f"    safety_confirm: \"{r['safety_confirm']}\"")
    return "\n".join(lines) + "\n"


def test_load_scenarios_parses_yaml(tmp_path):
    """Happy path: 3 minimal scenarios → list[Scenario] with required fields."""
    yaml = _minimal_scenarios_yaml([
        {"id": "scn-1-list", "expected_status": "PASS"},
        {"id": "scn-2-write", "expected_status": "PASS",
         "user_region": "us-east-1"},
        {"id": "scn-3-destructive", "expected_status": "SAFETY_FAIL",
         "safety_confirm": ""},
    ])
    p = _write_scenarios_yaml(tmp_path, yaml)
    scenarios = load_scenarios(p)
    assert len(scenarios) == 3
    assert scenarios[0].id == "scn-1-list"
    assert scenarios[0].expected_status == "PASS"
    assert scenarios[1].user_region == "us-east-1"
    assert scenarios[2].expected_status == "SAFETY_FAIL"


def test_load_scenarios_rejects_unknown_status(tmp_path):
    """Bad status value (not in {PASS, SAFETY_FAIL, MAX_ITER}) → ValueError."""
    yaml = (
        "---\n"
        "skill: aws-x-ops\n"
        "scenarios:\n"
        "  - id: bad\n"
        "    request: r\n"
        "    expected_status: WHO_KNOWS\n"
    )
    p = _write_scenarios_yaml(tmp_path, yaml)
    try:
        load_scenarios(p)
        raise AssertionError("should have raised ValueError for unknown status")
    except ValueError as exc:
        assert "WHO_KNOWS" in str(exc) or "expected_status" in str(exc)


def test_run_scenario_invokes_gcl_runner_and_matches_pass(tmp_path, monkeypatch):
    """Mock gcl_runner subprocess to return a known PASS trace; verify match."""
    scn = Scenario(
        id="scn-pass",
        description="happy read path",
        request="list things",
        expected_status="PASS",
        user_region="us-east-1",
    )

    fake_trace = {
        "skill": "aws-x-ops",
        "request": "list things",
        "iterations": [
            {"iter": 1, "generator": {"command": "aws x list"},
             "critic": {"scores": {
                 "correctness": 1.0, "safety": 1.0,
                 "idempotency": 1.0, "traceability": 1.0,
                 "spec_compliance": 1.0
             }}}
        ],
        "final": {"status": "PASS", "iter": 1},
    }

    # Subprocess wrapper is patched inside run_scenario; provide fake returncode
    class _FakeProc:
        returncode = 0
        stdout = json.dumps(fake_trace)
        stderr = ""

    def fake_run(*a, **k):
        return _FakeProc()
    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_scenario(scn, skill="aws-x-ops",
                          gcl_runner_path=SCRIPTS_DIR / "gcl_runner.py")
    assert isinstance(result, ScenarioResult)
    assert result.actual_status == "PASS"
    assert result.matched_status is True
    assert result.actual_scores["correctness"] == 1.0


def test_run_scenario_reports_safety_fail_mismatch(tmp_path, monkeypatch):
    """Scenario expects PASS but gcl_runner reports SAFETY_FAIL → matched=False."""
    scn = Scenario(
        id="scn-mismatch",
        description="",
        request="terminate i-x",
        expected_status="PASS",  # we expect it to pass (we'll provide confirm)
        user_region="us-east-1",
        safety_confirm="CONFIRM",
    )

    fake_trace = {
        "skill": "aws-x-ops", "request": "terminate i-x",
        "iterations": [{"iter": 1,
                        "critic": {"scores": {"safety": 0}}}],
        "final": {"status": "SAFETY_FAIL", "iter": 1},
    }

    class _FakeProc:
        returncode = 1
        stdout = json.dumps(fake_trace)
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _FakeProc())

    result = run_scenario(scn, skill="aws-x-ops",
                          gcl_runner_path=SCRIPTS_DIR / "gcl_runner.py")
    assert result.actual_status == "SAFETY_FAIL"
    assert result.matched_status is False


def test_compare_to_baseline_detects_regression():
    """Scenario passed in baseline, fails now → regressions contains its id."""
    scn = Scenario(id="X", description="", request="r",
                   expected_status="PASS")
    baseline = [ScenarioResult(
        scenario=scn, actual_status="PASS",
        actual_scores={"correctness": 1.0}, matched_status=True,
        score_deltas={})]
    current = [ScenarioResult(
        scenario=scn, actual_status="SAFETY_FAIL",
        actual_scores={"correctness": 0.0}, matched_status=False,
        score_deltas={"correctness": -1.0})]

    report = compare_to_baseline(current, baseline)
    assert "X" in report.regressions
    assert "X" not in report.fixed
    assert report.unchanged == []


def test_compare_to_baseline_detects_fix():
    """Scenario failed in baseline, passes now → fixed contains its id."""
    scn = Scenario(id="Y", description="", request="r",
                   expected_status="PASS")
    baseline = [ScenarioResult(
        scenario=scn, actual_status="SAFETY_FAIL",
        actual_scores={"safety": 0}, matched_status=False, score_deltas={})]
    current = [ScenarioResult(
        scenario=scn, actual_status="PASS",
        actual_scores={"safety": 1.0}, matched_status=True, score_deltas={})]

    report = compare_to_baseline(current, baseline)
    assert "Y" in report.fixed
    assert "Y" not in report.regressions


def test_cli_run_subprocess_writes_json(tmp_path):
    """End-to-end CLI: invoke as subprocess with --self-test, parse JSON output."""
    yaml = _minimal_scenarios_yaml([
        {"id": "scn-cli-1", "expected_status": "PASS"},
    ])
    scn_file = tmp_path / "scn.yaml"
    scn_file.write_text(yaml)
    out_file = tmp_path / "results.json"

    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "golden_eval.py"),
         "run", "--skill", "aws-x-ops", "--scenarios", str(scn_file),
         "--out", str(out_file)],
        capture_output=True, text=True, timeout=60,
    )
    # Either 0 (all PASS) or 1 (some failed) — both acceptable; we just want JSON
    assert result.returncode in (0, 1), f"unexpected exit {result.returncode}: {result.stderr}"
    data = json.loads(out_file.read_text())
    assert "results" in data
    assert len(data["results"]) == 1
    assert data["results"][0]["scenario"]["id"] == "scn-cli-1"
    assert "actual_status" in data["results"][0]
