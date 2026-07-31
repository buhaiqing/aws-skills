"""ADR-0001 M4 — governed_learning harvest / evaluate / approve."""
from __future__ import annotations

import inspect
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))

from governed_learning import (  # noqa: E402
    CandidateRule,
    approve_candidate,
    auto_promotion_rate,
    evaluate_candidate,
    evaluate_queue,
    harvest,
    harvest_compensation_failure,
    harvest_from_trace,
    load_queue,
    main,
    reject_candidate,
    report,
    save_queue,
)


def _fresh_patterns(tmp_path: Path) -> Path:
    p = tmp_path / "failure-patterns.md"
    p.write_text(
        "# Failure Patterns\n\n"
        "| skill | command | error | root_cause | fix | count | timestamp |\n"
        "|-------|---------|-------|------------|-----|-------|-----------|\n",
        encoding="utf-8",
    )
    return p


def test_harvest_from_safety_fail():
    cands = harvest_from_trace({
        "skill": "aws-ec2-ops",
        "final": {"status": "SAFETY_FAIL"},
        "iterations": [{
            "generator": {"command": "aws ec2 terminate-instances"},
            "critic": {"scores": {"safety": 0.0}},
        }],
    })
    assert len(cands) == 1
    assert cands[0].source_status == "SAFETY_FAIL"
    assert "safety" in cands[0].error


def test_harvest_blocked_and_pass_ignored():
    assert harvest_from_trace({"final": {"status": "PASS"}, "skill": "x"}) == []
    blocked = harvest_from_trace({
        "skill": "aws-iam-ops",
        "final": {"status": "BLOCKED", "reason": "runtime_safety"},
        "iterations": [],
    })
    assert len(blocked) == 1
    assert blocked[0].source_status == "BLOCKED"


def test_harvest_compensation_failure():
    cands = harvest_compensation_failure({
        "status": "BLOCKED",
        "skill": "aws-elb-ops",
        "compensation_node_id": "reregister",
        "reason": "proxy BLOCK",
    })
    assert len(cands) == 1
    assert cands[0].source_status == "COMPENSATION_FAIL"


def test_fixture_harvest_dedupe_under_10pct():
    h = harvest(use_fixtures=True)
    assert h.raw_count > h.unique_count
    assert h.duplicate_rate < 0.10
    assert h.to_dict()["auto_promotion_rate"] == 0.0
    assert len(h.candidates) == h.unique_count


def test_evaluate_before_after_gap(tmp_path):
    patterns = _fresh_patterns(tmp_path)
    cand = CandidateRule(
        id="cand-test",
        signature="aws-test-ops|aws test|safety=0.0",
        skill="aws-test-ops",
        command="aws test",
        error="safety=0.0",
        root_cause="r",
        fix="f",
        source_status="SAFETY_FAIL",
    )
    out = evaluate_candidate(cand, patterns_path=patterns)
    assert out.before_eval["gap"] is True
    assert out.after_eval["covered"] is True
    assert out.after_eval["no_regression"] is True


def test_approve_requires_approver_and_eval(tmp_path):
    patterns = _fresh_patterns(tmp_path)
    approvals = tmp_path / "approvals.jsonl"
    cand = CandidateRule(
        id="cand-test",
        signature="aws-test-ops|aws test|safety=0.0",
        skill="aws-test-ops",
        command="aws test",
        error="safety=0.0",
        root_cause="r",
        fix="f",
        source_status="SAFETY_FAIL",
    )
    with pytest.raises(ValueError, match="approver"):
        approve_candidate(cand, approver="  ", patterns_path=patterns, approvals_path=approvals)
    with pytest.raises(ValueError, match="before/after"):
        approve_candidate(cand, approver="alice", patterns_path=patterns, approvals_path=approvals)

    cand = evaluate_candidate(cand, patterns_path=patterns)
    approved = approve_candidate(
        cand, approver="alice", patterns_path=patterns, approvals_path=approvals,
    )
    assert approved.status == "approved"
    assert "aws-test-ops" in patterns.read_text()
    assert "alice" in approvals.read_text()


def test_reject_does_not_write_patterns(tmp_path):
    patterns = _fresh_patterns(tmp_path)
    before = patterns.read_text()
    cand = CandidateRule(
        id="cand-x", signature="a|b|c", skill="a", command="b", error="c",
        root_cause="r", fix="f", source_status="MAX_ITER",
    )
    reject_candidate(cand, reason="noise")
    assert cand.status == "rejected"
    assert patterns.read_text() == before


def test_auto_promotion_rate_always_zero():
    assert auto_promotion_rate() == 0.0


def test_no_public_auto_write_without_approver():
    """approve_candidate is the only public writer; requires approver kw."""
    sig = inspect.signature(approve_candidate)
    assert "approver" in sig.parameters
    # harvest / evaluate must not accept patterns write path
    assert "patterns_path" not in inspect.signature(harvest).parameters
    src = Path(SCRIPTS / "governed_learning.py").read_text(encoding="utf-8")
    # No helper that calls append_or_increment without going through approve
    assert src.count("append_or_increment") == 2  # import + approve body


def test_report_flags(tmp_path):
    h = harvest(use_fixtures=True)
    path = tmp_path / "q.json"
    save_queue(path, h)
    cands = load_queue(path)
    rep = report(cands, raw_count=h.raw_count)
    assert rep["auto_promotion_rate"] == 0.0
    assert rep["duplicate_rate_ok"] is True


def test_cli_harvest_evaluate_report(tmp_path):
    q = tmp_path / "queue.json"
    r1 = subprocess.run(
        [sys.executable, str(SCRIPTS / "governed_learning.py"),
         "harvest", "--fixtures", "--out", str(q)],
        cwd=str(REPO), capture_output=True, text=True, check=False,
    )
    assert r1.returncode == 0, r1.stderr + r1.stdout
    r2 = subprocess.run(
        [sys.executable, str(SCRIPTS / "governed_learning.py"),
         "evaluate", "--queue", str(q),
         "--patterns", str(_fresh_patterns(tmp_path))],
        cwd=str(REPO), capture_output=True, text=True, check=False,
    )
    assert r2.returncode == 0, r2.stderr
    r3 = subprocess.run(
        [sys.executable, str(SCRIPTS / "governed_learning.py"),
         "report", "--queue", str(q)],
        cwd=str(REPO), capture_output=True, text=True, check=False,
    )
    assert r3.returncode == 0, r3.stderr
    data = json.loads(r3.stdout)
    assert data["auto_promotion_rate"] == 0.0
    assert data["duplicate_rate_ok"] is True


def test_main_module_entry():
    assert callable(main)
    assert callable(evaluate_queue)
