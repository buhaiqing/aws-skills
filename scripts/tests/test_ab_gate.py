"""TDD tests for scripts/ab_gate.py — L4 #9 A/B Test Hard Gate.

A/B gate wraps golden_eval: compares two pre-computed results JSON
(baseline vs candidate) and exits 1 if any scenario regressed.

Cascade detection reads `metadata.cross_skill_deps` from a SKILL.md
frontmatter (L2 composite skills).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from ab_gate import (  # noqa: E402
    ABReport,
    run_ab_gate,
    cascaded_skills,
)


def _write_run_result(tmp_path: Path, subname: str, rows: list[dict], skill: str = "X") -> Path:
    """Helper: write a minimal results JSON to a subname-suffixed path."""
    p = tmp_path / f"{subname}.json"
    p.write_text(json.dumps({"skill": skill, "results": rows}))
    return p


def _sr(scenario_id: str, matched_status: bool) -> dict:
    """Single scenario result dict (matches ScenarioResult.asdict shape)."""
    return {
        "scenario": {
            "id": scenario_id, "description": "", "request": "r",
            "expected_status": "PASS", "user_region": "",
            "safety_confirm": "",
        },
        "actual_status": "PASS" if matched_status else "SAFETY_FAIL",
        "actual_scores": {}, "matched_status": matched_status,
        "score_deltas": {},
    }


def test_run_ab_gate_no_regression_passes(tmp_path):
    """Identical baseline+candidate → regressions empty, has_regression=False."""
    b = _write_run_result(tmp_path, "X-baseline", [_sr("X-1", True), _sr("X-2", True)], skill="X")
    c = _write_run_result(tmp_path, "X-candidate", [_sr("X-1", True), _sr("X-2", True)], skill="X")
    report = run_ab_gate(b, c)
    assert isinstance(report, ABReport)
    assert report.regressions == []
    assert report.has_regression is False
    assert report.exit_code == 0


def test_run_ab_gate_detects_regression(tmp_path):
    """scenario passed in baseline, fails in candidate → regressions contains id."""
    b = _write_run_result(tmp_path, "X-baseline", [_sr("X-1", True), _sr("X-2", True)], skill="X")
    c = _write_run_result(tmp_path, "X-candidate", [_sr("X-1", True), _sr("X-2", False)], skill="X")
    report = run_ab_gate(b, c)
    assert "X-2" in report.regressions
    assert report.has_regression is True
    assert report.exit_code == 1


def test_run_ab_gate_rejects_missing_baseline(tmp_path):
    """Non-existent baseline file → exit_code 2, clear error message."""
    missing = tmp_path / "no-such.json"
    c = _write_run_result(tmp_path, "X-candidate", [_sr("X-1", True)], skill="X")
    report = run_ab_gate(missing, c)
    assert report.exit_code == 2
    assert "no-such" in str(report.baseline_path) or "missing" in report.regressions


def test_cascaded_skills_reads_cross_skill_deps():
    """Extracts `metadata.cross_skill_deps` from real aws-aiops-copilot/SKILL.md."""
    skills = cascaded_skills("aws-aiops-copilot", repo=REPO)
    # aws-aiops-copilot declares aws-aiops-cruise + aws-aiops-orchestrator as deps
    assert "aws-aiops-cruise" in skills
    assert "aws-aiops-orchestrator" in skills


def test_cli_gate_subprocess_exit_codes(tmp_path):
    """End-to-end CLI: baseline + candidate files → process exits per regression."""
    b = _write_run_result(tmp_path, "Y-baseline", [_sr("Y-1", True)], skill="Y")
    c_good = _write_run_result(tmp_path, "Y-good", [_sr("Y-1", True)], skill="Y")
    c_bad = _write_run_result(tmp_path, "Y-bad", [_sr("Y-1", False)], skill="Y")

    # No regression: exit 0
    proc0 = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "ab_gate.py"),
         "gate", "--baseline", str(b), "--candidate", str(c_good)],
        capture_output=True, text=True, timeout=30,
    )
    assert proc0.returncode == 0, f"stdout={proc0.stdout} stderr={proc0.stderr}"

    # With regression: exit 1
    proc1 = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "ab_gate.py"),
         "gate", "--baseline", str(b), "--candidate", str(c_bad)],
        capture_output=True, text=True, timeout=30,
    )
    assert proc1.returncode == 1, f"stdout={proc1.stdout} stderr={proc1.stderr}"
    assert "Y-1" in proc1.stdout or "Y-1" in proc1.stderr


def test_cli_gate_json_output(tmp_path):
    """`--json` flag emits parseable JSON to stdout."""
    b = _write_run_result(tmp_path, "Z-baseline", [_sr("Z-1", True)], skill="Z")
    c = _write_run_result(tmp_path, "Z-candidate", [_sr("Z-1", False)], skill="Z")
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "ab_gate.py"),
         "gate", "--baseline", str(b), "--candidate", str(c), "--json"],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["exit_code"] == 1
    assert "Z-1" in payload["regressions"]


def test_cli_cascade_lists_deps():
    """`ab_gate.py cascade --skill aws-aiops-copilot` lists cascade deps."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "ab_gate.py"),
         "cascade", "--skill", "aws-aiops-copilot"],
        capture_output=True, text=True, timeout=10,
    )
    assert proc.returncode == 0
    combined = (proc.stdout + proc.stderr).lower()
    assert "aws-aiops-cruise" in combined or "aws-aiops-orchestrator" in combined
