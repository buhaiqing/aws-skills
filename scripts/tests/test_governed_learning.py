"""ADR-0001 M4 -- governed_learning harvest / evaluate / approve / auto-promote."""
from __future__ import annotations

import inspect
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from hypothesis import given, assume, settings, HealthCheck
from hypothesis import strategies as st

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))

from governed_learning import (  # noqa: E402
    CandidateRule,
    MIN_CONFIDENCE,
    MIN_DWELL_HOURS,
    approve_candidate,
    auto_promote,
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


def _make_candidate(
    tmp_path: Path,
    *,
    skill: str = "aws-test-ops",
    command: str = "aws test delete-thing",
    error: str = "safety=0.5",
    source_status: str = "MAX_ITER",
    confidence: float = 0.98,
    attempt_count: int = 5,
    created_days_ago: int = 10,
    gap: bool = True,
    no_regression: bool = True,
) -> CandidateRule:
    """Build a candidate with eval evidence for auto-promo tests."""
    now = datetime.now(timezone.utc)
    created = (now - timedelta(days=created_days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")
    cand = CandidateRule(
        id="cand-test",
        signature=f"{skill}|{command}|{error[:50]}",
        skill=skill,
        command=command,
        error=error,
        root_cause="test root cause",
        fix="test fix",
        source_status=source_status,  # type: ignore[arg-type]
        confidence=confidence,
        attempt_count=attempt_count,
        created_at=created,
    )
    cand.before_eval = {"gap": gap, "signature_in_library": not gap, "at": created}
    cand.after_eval = {"no_regression": no_regression, "covered": True, "regressions": [], "at": created}
    return cand


# ---------------------------------------------------------------------------
# Existing tests (unchanged)
# ---------------------------------------------------------------------------

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


def test_no_public_auto_write_without_approver():
    """approve_candidate is the only public writer; requires approver kw."""
    sig = inspect.signature(approve_candidate)
    assert "approver" in sig.parameters
    assert "patterns_path" not in inspect.signature(harvest).parameters
    src = Path(SCRIPTS / "governed_learning.py").read_text(encoding="utf-8")
    assert src.count("append_or_increment") == 2  # import + approve body


def test_report_flags(tmp_path):
    h = harvest(use_fixtures=True)
    path = tmp_path / "q.json"
    save_queue(path, h)
    cands = load_queue(path)
    rep = report(cands, raw_count=h.raw_count, queue_path=path)
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


# ---------------------------------------------------------------------------
# Auto-promotion tests (new)
# ---------------------------------------------------------------------------

def test_auto_promote_eligible_happy_path(tmp_path):
    """Candidate meeting all 7 gates gets auto-promoted."""
    patterns = _fresh_patterns(tmp_path)
    approvals = tmp_path / "approvals.jsonl"
    cand = _make_candidate(tmp_path, confidence=0.98, attempt_count=5, created_days_ago=10)
    promoted = auto_promote([cand], patterns_path=patterns, approvals_path=approvals)
    assert len(promoted) == 1
    assert promoted[0].status == "approved"
    assert promoted[0].approval["approver"] == "system:auto"
    assert "aws-test-ops" in patterns.read_text()
    assert "system:auto" in approvals.read_text()


def test_auto_promote_rejects_low_confidence(tmp_path):
    patterns = _fresh_patterns(tmp_path)
    cand = _make_candidate(tmp_path, confidence=0.80, attempt_count=5, created_days_ago=10)
    promoted = auto_promote([cand], patterns_path=patterns)
    assert len(promoted) == 0
    assert cand.status == "pending"


def test_auto_promote_rejects_recent_candidate(tmp_path):
    """Candidate younger than MIN_DWELL_HOURS is rejected."""
    patterns = _fresh_patterns(tmp_path)
    cand = _make_candidate(tmp_path, confidence=0.98, attempt_count=5, created_days_ago=1)
    promoted = auto_promote([cand], patterns_path=patterns)
    assert len(promoted) == 0


def test_auto_promote_rejects_regression(tmp_path):
    patterns = _fresh_patterns(tmp_path)
    cand = _make_candidate(
        tmp_path, confidence=0.98, attempt_count=5, created_days_ago=10,
        no_regression=False,
    )
    promoted = auto_promote([cand], patterns_path=patterns)
    assert len(promoted) == 0


def test_auto_promote_rejects_already_in_library(tmp_path):
    patterns = _fresh_patterns(tmp_path)
    from _reflexion import FailurePattern, append_or_increment
    sig = "aws-test-ops|aws test delete-thing|safety=0.5"
    append_or_increment(patterns, FailurePattern(
        skill="aws-test-ops", command="aws test delete-thing",
        error="safety=0.5", root_cause="old", fix="old",
        timestamp="2026-01-01T00:00:00Z", count=1, error_signature=sig,
    ))
    cand = _make_candidate(tmp_path, confidence=0.98, attempt_count=5, created_days_ago=10)
    cand.signature = sig
    promoted = auto_promote([cand], patterns_path=patterns)
    assert len(promoted) == 0


def test_auto_promote_rejects_safety_zero(tmp_path):
    """SAFETY_FAIL with safety=0.0 always needs human."""
    patterns = _fresh_patterns(tmp_path)
    cand = _make_candidate(
        tmp_path, confidence=0.98, attempt_count=5, created_days_ago=10,
        error="safety=0.0", source_status="SAFETY_FAIL",
    )
    promoted = auto_promote([cand], patterns_path=patterns)
    assert len(promoted) == 0


def test_auto_promote_safety_fail_eligible(tmp_path):
    """SAFETY_FAIL with safety > 0.0 is eligible even with low attempt_count."""
    patterns = _fresh_patterns(tmp_path)
    cand = _make_candidate(
        tmp_path, confidence=0.98, attempt_count=1, created_days_ago=10,
        error="safety=0.5", source_status="SAFETY_FAIL",
    )
    promoted = auto_promote([cand], patterns_path=patterns)
    assert len(promoted) == 1


def test_auto_promote_dry_run(tmp_path):
    """dry_run=True does not write to patterns file."""
    patterns = _fresh_patterns(tmp_path)
    before = patterns.read_text()
    cand = _make_candidate(tmp_path, confidence=0.98, attempt_count=5, created_days_ago=10)
    promoted = auto_promote([cand], patterns_path=patterns, dry_run=True)
    assert len(promoted) == 1
    assert promoted[0].approval["dry_run"] is True
    assert patterns.read_text() == before


def test_auto_promote_rate_computes_correctly(tmp_path):
    assert auto_promotion_rate() == 0.0
    assert auto_promotion_rate(tmp_path / "nonexistent.json") == 0.0
    q = tmp_path / "queue.json"
    q.write_text(json.dumps({"candidates": []}), encoding="utf-8")
    assert auto_promotion_rate(q) == 0.0


def test_auto_promote_skips_unevaluated(tmp_path):
    """Candidates without before_eval/after_eval are skipped."""
    patterns = _fresh_patterns(tmp_path)
    cand = CandidateRule(
        id="cand-noeval", signature="a|b|c", skill="a", command="b", error="c",
        root_cause="r", fix="f", source_status="MAX_ITER",
        confidence=0.99, attempt_count=10, created_at="2026-01-01T00:00:00Z",
    )
    promoted = auto_promote([cand], patterns_path=patterns)
    assert len(promoted) == 0


def test_auto_promote_low_attempt_count_rejected(tmp_path):
    """Non-SAFETY_FAIL with attempt_count < MIN_ATTEMPT_COUNT is rejected."""
    patterns = _fresh_patterns(tmp_path)
    cand = _make_candidate(
        tmp_path, confidence=0.98, attempt_count=2, created_days_ago=10,
        source_status="MAX_ITER",
    )
    promoted = auto_promote([cand], patterns_path=patterns)
    assert len(promoted) == 0


def test_auto_promote_rate_with_real_queue(tmp_path):
    """auto_promotion_rate computes correctly from a queue with mixed approvals."""
    patterns = _fresh_patterns(tmp_path)
    approvals = tmp_path / "approvals.jsonl"
    c1 = _make_candidate(tmp_path, confidence=0.98, attempt_count=5, created_days_ago=10)
    c2 = _make_candidate(
        tmp_path, confidence=0.50, attempt_count=5, created_days_ago=10,
        command="aws test other-thing", error="timeout",
    )
    all_cands = [c1, c2]
    all_cands = evaluate_queue(all_cands, patterns_path=patterns)
    auto_promote(all_cands, patterns_path=patterns, approvals_path=approvals)

    q = tmp_path / "queue.json"
    save_queue(q, all_cands)
    rate = auto_promotion_rate(q)
    assert rate == 0.5


def test_cli_promote_dry_run(tmp_path):
    patterns = _fresh_patterns(tmp_path)
    q = tmp_path / "queue.json"
    cand = _make_candidate(tmp_path, confidence=0.98, attempt_count=5, created_days_ago=10)
    q.write_text(json.dumps({
        "raw_count": 1,
        "unique_count": 1,
        "duplicate_rate": 0.0,
        "candidates": [cand.to_dict()],
    }), encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "governed_learning.py"),
         "promote", "--queue", str(q), "--patterns", str(patterns), "--dry-run"],
        cwd=str(REPO), capture_output=True, text=True, check=False,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert "dry-run" in r.stdout
    assert "1 / 1" in r.stdout


def test_candidate_rule_backward_compat():
    """Old queue files without confidence/attempt_count/created_at still load."""
    data = {
        "id": "cand-old",
        "signature": "a|b|c",
        "skill": "a",
        "command": "b",
        "error": "c",
        "root_cause": "r",
        "fix": "f",
        "source_status": "MAX_ITER",
    }
    cand = CandidateRule.from_dict(data)
    assert cand.confidence == 0.0
    assert cand.attempt_count == 0
    assert cand.created_at == ""


# ---------------------------------------------------------------------------
# Hypothesis property-based tests
# ---------------------------------------------------------------------------



# Strategy for building valid CandidateRule fields
st_skill = st.sampled_from(["aws-ec2-ops", "aws-s3-ops", "aws-iam-ops", "aws-rds-ops", "aws-kms-ops"])
st_command = st.sampled_from(["aws ec2 terminate-instances", "aws s3api delete-bucket", "aws iam delete-user"])
st_error = st.text(min_size=1, max_size=50).filter(lambda x: x.strip())
st_source_status = st.sampled_from(["SAFETY_FAIL", "MAX_ITER", "BLOCKED", "COMPENSATION_FAIL"])
st_confidence = st.floats(min_value=0.0, max_value=1.0)
st_attempt_count = st.integers(min_value=0, max_value=100)
st_created_days_ago = st.integers(min_value=0, max_value=365)
st_bool = st.booleans()


@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    confidence=st_confidence,
    attempt_count=st_attempt_count,
    created_days_ago=st_created_days_ago,
    gap=st_bool,
    no_regression=st_bool,
)
def test_auto_promote_never_promotes_without_eval(tmp_path, confidence, attempt_count, created_days_ago, gap, no_regression):
    """Property: candidates without before_eval/after_eval are NEVER promoted."""
    from datetime import timedelta
    patterns = _fresh_patterns(tmp_path)
    now = datetime.now(timezone.utc)
    created = (now - timedelta(days=created_days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")
    cand = CandidateRule(
        id="cand-prop", signature="prop|test|x", skill="prop",
        command="test", error="x", root_cause="r", fix="f",
        source_status="MAX_ITER",  # type: ignore[arg-type]
        confidence=confidence, attempt_count=attempt_count, created_at=created,
    )
    # Intentionally NO before_eval / after_eval
    promoted = auto_promote([cand], patterns_path=patterns)
    assert len(promoted) == 0


@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    confidence=st_confidence,
    attempt_count=st_attempt_count,
    created_days_ago=st_created_days_ago,
)
def test_auto_promote_safety_zero_always_rejected(tmp_path, confidence, attempt_count, created_days_ago):
    """Property: SAFETY_FAIL with safety=0.0 is NEVER auto-promoted, regardless of other fields."""
    from datetime import timedelta
    patterns = _fresh_patterns(tmp_path)
    now = datetime.now(timezone.utc)
    created = (now - timedelta(days=created_days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")
    cand = CandidateRule(
        id="cand-sz", signature="sz|test|x", skill="sz",
        command="test", error="safety=0.0", root_cause="r", fix="f",
        source_status="SAFETY_FAIL",  # type: ignore[arg-type]
        confidence=confidence, attempt_count=attempt_count, created_at=created,
    )
    cand.before_eval = {"gap": True, "signature_in_library": False, "at": created}
    cand.after_eval = {"no_regression": True, "covered": True, "regressions": [], "at": created}
    promoted = auto_promote([cand], patterns_path=patterns)
    assert len(promoted) == 0, "safety=0.0 must always require human"


@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    confidence=st_confidence,
    created_days_ago=st_created_days_ago,
    attempt_count=st_attempt_count,
)
def test_auto_promote_low_confidence_always_rejected(tmp_path, confidence, created_days_ago, attempt_count):
    """Property: confidence < 0.95 is NEVER auto-promoted."""
    assume(confidence < 0.95)
    from datetime import timedelta
    patterns = _fresh_patterns(tmp_path)
    now = datetime.now(timezone.utc)
    created = (now - timedelta(days=created_days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")
    cand = CandidateRule(
        id="cand-lc", signature="lc|test|x", skill="lc",
        command="test", error="timeout", root_cause="r", fix="f",
        source_status="MAX_ITER",  # type: ignore[arg-type]
        confidence=confidence, attempt_count=attempt_count, created_at=created,
    )
    cand.before_eval = {"gap": True, "signature_in_library": False, "at": created}
    cand.after_eval = {"no_regression": True, "covered": True, "regressions": [], "at": created}
    promoted = auto_promote([cand], patterns_path=patterns)
    assert len(promoted) == 0, f"confidence={confidence} < 0.95 must not promote"


@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(created_days_ago=st.integers(min_value=0, max_value=6))
def test_auto_promote_young_candidates_rejected(tmp_path, created_days_ago):
    """Property: candidates younger than 7 days are NEVER auto-promoted."""
    from datetime import timedelta
    patterns = _fresh_patterns(tmp_path)
    now = datetime.now(timezone.utc)
    created = (now - timedelta(days=created_days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")
    cand = CandidateRule(
        id="cand-yc", signature="yc|test|x", skill="yc",
        command="test", error="timeout", root_cause="r", fix="f",
        source_status="MAX_ITER",  # type: ignore[arg-type]
        confidence=0.99, attempt_count=10, created_at=created,
    )
    cand.before_eval = {"gap": True, "signature_in_library": False, "at": created}
    cand.after_eval = {"no_regression": True, "covered": True, "regressions": [], "at": created}
    promoted = auto_promote([cand], patterns_path=patterns)
    assert len(promoted) == 0, f"age={created_days_ago}d < 7d must not promote"


@settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(no_regression=st_bool)
def test_auto_promote_regression_gate(tmp_path, no_regression):
    """Property: when no_regression=False, zero candidates are promoted."""
    from datetime import timedelta
    patterns = _fresh_patterns(tmp_path)
    now = datetime.now(timezone.utc)
    created = (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    cand = CandidateRule(
        id="cand-rg", signature="rg|test|x", skill="rg",
        command="test", error="timeout", root_cause="r", fix="f",
        source_status="MAX_ITER",  # type: ignore[arg-type]
        confidence=0.99, attempt_count=10, created_at=created,
    )
    cand.before_eval = {"gap": True, "signature_in_library": False, "at": created}
    cand.after_eval = {"no_regression": no_regression, "covered": True, "regressions": [], "at": created}
    promoted = auto_promote([cand], patterns_path=patterns)
    if not no_regression:
        assert len(promoted) == 0, "no_regression=False must block promotion"


@settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(sig_in_lib=st_bool)
def test_auto_promote_library_dedup(tmp_path, sig_in_lib):
    """Property: if signature already in library, NOT promoted regardless of other fields."""
    from datetime import timedelta
    patterns = _fresh_patterns(tmp_path)
    if sig_in_lib:
        from _reflexion import FailurePattern, append_or_increment
        append_or_increment(patterns, FailurePattern(
            skill="lib", command="test", error="timeout",
            root_cause="old", fix="old",
            timestamp="2026-01-01T00:00:00Z", count=1,
            error_signature="lib|test|timeout",
        ))
    now = datetime.now(timezone.utc)
    created = (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    cand = CandidateRule(
        id="cand-ld", signature="lib|test|timeout", skill="lib",
        command="test", error="timeout", root_cause="r", fix="f",
        source_status="MAX_ITER",  # type: ignore[arg-type]
        confidence=0.99, attempt_count=10, created_at=created,
    )
    cand.before_eval = {"gap": not sig_in_lib, "signature_in_library": sig_in_lib, "at": created}
    cand.after_eval = {"no_regression": True, "covered": True, "regressions": [], "at": created}
    promoted = auto_promote([cand], patterns_path=patterns)
    if sig_in_lib:
        assert len(promoted) == 0, "in-library must not promote"
