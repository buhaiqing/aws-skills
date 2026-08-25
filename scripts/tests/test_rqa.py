"""TDD tests for scripts/rqa.py - L4 Gap 4 Reasoning Quality Audit.

Property invariants:
- a PASS trace with any final-iteration dim < 1.0 ALWAYS yields a finding
- an all-1.0 PASS trace NEVER yields findings
- non-PASS traces NEVER yield findings
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

REPO = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from rqa import RqaFinding, audit_dir, audit_trace  # noqa: E402

_DIMS = ("correctness", "safety", "idempotency", "traceability", "spec_compliance")


def _trace(status: str, scores: dict | None, iters: list | None = None) -> dict:
    iterations = iters if iters is not None else (
        [{
            "iter": 1,
            "generator": {"command": "aws s3 list-buckets"},
            "critic": {"scores": scores or {}, "suggestions": []},
            "decision": "RETURN" if status == "PASS" else "ABORT",
        }]
    )
    return {"skill": "aws-s3-ops", "iterations": iterations,
            "final": {"status": status, "iter": 1, "output": None}}


# ---------------------------------------------------------------------------
# Unit
# ---------------------------------------------------------------------------


def test_full_score_pass_has_no_findings():
    scores = {d: 1.0 for d in _DIMS}
    assert audit_trace(_trace("PASS", scores)) == []


def test_pass_with_low_safety_is_high_severity():
    scores = {d: 1.0 for d in _DIMS}
    scores["safety"] = 0.5
    findings = audit_trace(_trace("PASS", scores))
    assert len(findings) == 1
    assert findings[0].code == "RQA-001"
    assert findings[0].severity == "high"
    assert "safety" in findings[0].detail


def test_pass_with_low_non_safety_dim_is_medium():
    scores = {d: 1.0 for d in _DIMS}
    scores["idempotency"] = 0.5
    findings = audit_trace(_trace("PASS", scores))
    assert len(findings) == 1
    assert findings[0].severity == "medium"


def test_pass_without_iterations_flagged():
    findings = audit_trace(_trace("PASS", None, iters=[]))
    assert len(findings) == 1
    assert findings[0].code == "RQA-002"


def test_pass_missing_dim_flagged():
    scores = {d: 1.0 for d in _DIMS}
    del scores["traceability"]
    findings = audit_trace(_trace("PASS", scores))
    assert len(findings) == 1
    assert findings[0].code == "RQA-003"


def test_non_pass_never_flagged():
    for status in ("SAFETY_FAIL", "MAX_ITER", "BLOCKED", "COMPENSATED"):
        assert audit_trace(_trace(status, {d: 0.0 for d in _DIMS})) == []


def test_audit_dir_batch(tmp_path):
    good = _trace("PASS", {d: 1.0 for d in _DIMS})
    bad = _trace("PASS", {**{d: 1.0 for d in _DIMS}, "safety": 0.0})
    (tmp_path / "gcl-trace-aaa.json").write_text(json.dumps(good))
    (tmp_path / "gcl-trace-bbb.json").write_text(json.dumps(bad))
    (tmp_path / "not-a-trace.json").write_text(json.dumps(good))
    rep = audit_dir(tmp_path)
    assert rep["traces_audited"] == 2
    assert rep["traces_flagged"] == 1
    assert rep["total_findings"] == 1


def test_audit_dir_tolerates_corrupt_json(tmp_path):
    (tmp_path / "gcl-trace-bad.json").write_text("{not json")
    rep = audit_dir(tmp_path)
    assert rep["traces_audited"] == 1
    assert rep["total_findings"] == 0


# ---------------------------------------------------------------------------
# Hypothesis property tests
# ---------------------------------------------------------------------------

_score = st.sampled_from([0.0, 0.5, 1.0])


@settings(max_examples=50, deadline=None)
@given(scores=st.fixed_dictionaries({d: _score for d in _DIMS}))
def test_pass_low_dim_always_flagged(scores):
    """Property: PASS + any dim < 1.0 => at least one finding."""
    findings = audit_trace(_trace("PASS", scores))
    has_low = any(v < 1.0 for v in scores.values())
    if has_low:
        assert findings, f"expected findings for {scores}"
        assert all(isinstance(f, RqaFinding) for f in findings)
    else:
        assert findings == []


@settings(max_examples=30, deadline=None)
@given(status=st.sampled_from(["SAFETY_FAIL", "MAX_ITER", "BLOCKED"]))
def test_non_pass_never_flagged_fuzzed(status):
    """Property: non-PASS traces never produce findings."""
    scores = {d: 0.0 for d in _DIMS}
    assert audit_trace(_trace(status, scores)) == []
