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

import failure_kb  # noqa: E402
import governed_learning  # noqa: E402
from failure_kb import FailureRecord  # noqa: E402
from governed_learning import (  # noqa: E402
    GATE_DUPLICATE,
    GATE_DWELL,
    GATE_SAFETY,
    CandidateRule,
    MIN_ATTEMPT_COUNT,
    MIN_CONFIDENCE,
    MIN_DWELL_HOURS,
    _library_signatures,
    approve_candidate,
    auto_promote,
    auto_promotion_rate,
    blocking_gate,
    compute_confidence,
    dwell_stats,
    evaluate_candidate,
    evaluate_queue,
    harvest,
    harvest_compensation_failure,
    harvest_from_trace,
    load_candidate_state,
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
    """Fixture harvest must not pollute the git-tracked durable store."""
    q = tmp_path / "queue.json"
    tracked_state = governed_learning.CANDIDATE_STATE_PATH
    state_before = tracked_state.read_bytes()
    r1 = subprocess.run(
        [sys.executable, str(SCRIPTS / "governed_learning.py"),
         "harvest", "--fixtures", "--out", str(q)],
        cwd=str(REPO), capture_output=True, text=True, check=False,
    )
    assert r1.returncode == 0, r1.stderr + r1.stdout
    assert tracked_state.read_bytes() == state_before
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
# Durable store (P0-2): created_at + attempt_count survive re-harvest and
# brand-new processes. Without this Gate 4 (evidence) and Gate 5 (dwell) are
# dead — both restart from zero on every run.
# ---------------------------------------------------------------------------

FIXTURE_DUP_SIGNATURE = "aws-ec2-ops|aws ec2 terminate-instances|safety=0.0"
# Seen exactly once per fixture run → attempt_count grows by 1 per harvest.
FIXTURE_SOLO_SIGNATURE = "aws-s3-ops|aws s3api delete-bucket|idempotency=0.0"


def _seed_state(path: Path, signature: str, first_seen: str, attempts: int = 0) -> None:
    path.write_text(json.dumps({
        signature: {"first_seen": first_seen, "attempt_count": attempts},
    }), encoding="utf-8")


def _cli_harvest(state: Path, out: Path) -> dict[str, CandidateRule]:
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "governed_learning.py"),
         "harvest", "--fixtures", "--out", str(out), "--candidate-state", str(state)],
        cwd=str(REPO), capture_output=True, text=True, check=False,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    return {c.signature: c for c in load_queue(out)}


def test_harvest_twice_keeps_earliest_created_at(tmp_path, monkeypatch):
    """Second harvest of the same signature must not reset the dwell clock."""
    state_path = tmp_path / "candidate-state.json"
    first = harvest(use_fixtures=True, candidate_state_path=state_path)
    first_map = {c.signature: c.created_at for c in first.candidates}
    assert state_path.exists(), "harvest must persist candidate state to disk"
    persisted = json.loads(state_path.read_text(encoding="utf-8"))
    assert {sig: entry["first_seen"] for sig, entry in persisted.items()} == first_map

    # Repeat sightings accumulate evidence instead of a fresh clock.
    dup = next(c for c in first.candidates if c.signature == FIXTURE_DUP_SIGNATURE)
    assert dup.attempt_count == 2
    assert len(dup.sources) == 2

    monkeypatch.setattr(governed_learning, "_now", lambda: "2099-01-01T00:00:00Z")
    second = harvest(use_fixtures=True, candidate_state_path=state_path)
    second_map = {c.signature: c.created_at for c in second.candidates}
    assert second_map == first_map
    assert "2099-01-01T00:00:00Z" not in second_map.values()


def test_attempt_count_accumulates_across_processes(tmp_path):
    """Real subprocesses: attempt_count survives and grows past the gate."""
    state_path = tmp_path / "candidate-state.json"
    seeded = "2026-01-01T00:00:00Z"
    _seed_state(state_path, FIXTURE_SOLO_SIGNATURE, seeded)

    counts = []
    for i in range(MIN_ATTEMPT_COUNT):
        run = _cli_harvest(state_path, tmp_path / f"q{i}.json")
        cand = run[FIXTURE_SOLO_SIGNATURE]
        assert cand.created_at == seeded, "durable first_seen must not reset"
        counts.append(cand.attempt_count)

    assert counts == [1, 2, 3], "attempt_count must accumulate across processes"
    assert counts[-1] >= MIN_ATTEMPT_COUNT
    persisted = json.loads(state_path.read_text(encoding="utf-8"))
    assert persisted[FIXTURE_SOLO_SIGNATURE] == {"first_seen": seeded, "attempt_count": 3}


def test_candidate_state_persists_created_at_across_processes(tmp_path):
    """A brand-new process reads the same created_at (queue itself is transient)."""
    state_path = tmp_path / "candidate-state.json"
    seeded = "2026-01-01T00:00:00Z"
    _seed_state(state_path, FIXTURE_DUP_SIGNATURE, seeded)

    def _ages(path: Path) -> dict[str, str]:
        return {sig: e["first_seen"] for sig, e in json.loads(path.read_text(encoding="utf-8")).items()}

    run1 = _cli_harvest(state_path, tmp_path / "q1.json")
    assert run1[FIXTURE_DUP_SIGNATURE].created_at == seeded
    after_first = _ages(state_path)

    fresh = next(s for s in run1 if s != FIXTURE_DUP_SIGNATURE)
    run2 = _cli_harvest(state_path, tmp_path / "q2.json")
    assert run2[FIXTURE_DUP_SIGNATURE].created_at == seeded
    assert run2[fresh].created_at == run1[fresh].created_at
    assert _ages(state_path) == after_first, "second run must not reset any age"


def test_load_candidate_state_missing_file_returns_empty(tmp_path):
    assert load_candidate_state(tmp_path / "absent.json") == {}


@pytest.mark.parametrize("payload", ["{", "[]", "null", '"str"', "123"])
def test_load_candidate_state_invalid_payload_returns_empty(tmp_path, payload):
    state_path = tmp_path / "candidate-state.json"
    state_path.write_text(payload, encoding="utf-8")
    assert load_candidate_state(state_path) == {}


def test_load_candidate_state_drops_only_the_malformed_entries(tmp_path):
    """One corrupt record must not erase the age/evidence of healthy ones."""
    state_path = tmp_path / "candidate-state.json"
    state_path.write_text(json.dumps({
        FIXTURE_SOLO_SIGNATURE: {"first_seen": "2026-01-01T00:00:00Z", "attempt_count": 4},
        "not-an-object": "oops",
        "bad-count": {"first_seen": "2026-01-01T00:00:00Z", "attempt_count": "many"},
        "missing-first-seen": {"attempt_count": 2},
    }), encoding="utf-8")

    state = load_candidate_state(state_path)
    assert state[FIXTURE_SOLO_SIGNATURE] == {
        "first_seen": "2026-01-01T00:00:00Z", "attempt_count": 4,
    }
    assert "not-an-object" not in state
    assert "bad-count" not in state
    assert state["missing-first-seen"]["first_seen"] == ""


def test_partly_corrupt_store_does_not_reset_surviving_candidate(tmp_path, monkeypatch):
    """Harvest over a partly-corrupt store keeps the surviving age and count."""
    state_path = tmp_path / "candidate-state.json"
    state_path.write_text(json.dumps({
        FIXTURE_SOLO_SIGNATURE: {"first_seen": "2026-01-01T00:00:00Z", "attempt_count": 4},
        "junk": 42,
    }), encoding="utf-8")
    monkeypatch.setattr(governed_learning, "_now", lambda: "2099-01-01T00:00:00Z")

    report_h = harvest(use_fixtures=True, candidate_state_path=state_path)
    solo = next(c for c in report_h.candidates if c.signature == FIXTURE_SOLO_SIGNATURE)
    assert solo.created_at == "2026-01-01T00:00:00Z", "age must not reset to zero"
    assert solo.attempt_count == 5
    # Unknown signatures degrade to "new candidate" (fresh clock, count 1).
    unknown = next(c for c in report_h.candidates if c.signature not in {
        FIXTURE_SOLO_SIGNATURE, "junk",
    })
    assert unknown.created_at == "2099-01-01T00:00:00Z"
    assert unknown.attempt_count == 1


def test_corrupt_candidate_state_recovers_without_resetting_next_harvest(tmp_path, monkeypatch):
    state_path = tmp_path / "candidate-state.json"
    state_path.write_text("{", encoding="utf-8")
    initial_time = "2026-01-01T00:00:00Z"
    monkeypatch.setattr(governed_learning, "_now", lambda: initial_time)

    first = harvest(use_fixtures=True, candidate_state_path=state_path)
    assert {candidate.created_at for candidate in first.candidates} == {initial_time}

    monkeypatch.setattr(governed_learning, "_now", lambda: "2099-01-01T00:00:00Z")
    second = harvest(use_fixtures=True, candidate_state_path=state_path)
    assert {candidate.created_at for candidate in second.candidates} == {initial_time}


# ---------------------------------------------------------------------------
# Gate 1: confidence must be computable, evidence-driven and reachable
# ---------------------------------------------------------------------------

def test_confidence_grows_with_evidence_and_reaches_threshold(tmp_path):
    """One sighting is never enough; MIN_ATTEMPT_COUNT sightings is."""
    scores = []
    for attempts in range(1, MIN_ATTEMPT_COUNT + 1):
        cand = _make_candidate(tmp_path, attempt_count=attempts, source_status="MAX_ITER")
        scores.append(compute_confidence(cand))

    assert scores == sorted(scores) and len(set(scores)) == len(scores)
    assert scores[0] < MIN_CONFIDENCE, "a single sighting must not reach the gate"
    assert scores[-1] >= MIN_CONFIDENCE, "MIN_ATTEMPT_COUNT sightings must clear it"


def test_confidence_single_sighting_never_full_marks(tmp_path):
    for status in ("SAFETY_FAIL", "MAX_ITER", "BLOCKED", "COMPENSATION_FAIL"):
        cand = _make_candidate(tmp_path, attempt_count=1, source_status=status)
        score = compute_confidence(cand)
        assert score < 1.0, f"{status} must not score perfect on one sighting"


def test_confidence_safety_fail_is_sufficient_single_evidence(tmp_path):
    """A Critic safety verdict alone carries enough weight (Gate 5 still applies)."""
    cand = _make_candidate(tmp_path, attempt_count=1, source_status="SAFETY_FAIL")
    assert compute_confidence(cand) >= MIN_CONFIDENCE
    assert blocking_gate(
        cand, lib=set(), now=datetime.now(timezone.utc) + timedelta(days=30),
    ) == []  # dwell satisfied → no gate blocks it


def test_confidence_harvested_candidates_are_real(tmp_path):
    """Harvest output carries non-zero, evidence-derived confidence."""
    state_path = tmp_path / "candidate-state.json"
    report_h = harvest(use_fixtures=True, candidate_state_path=state_path)
    dup = next(c for c in report_h.candidates if c.signature == FIXTURE_DUP_SIGNATURE)
    solo = next(c for c in report_h.candidates if c.signature == FIXTURE_SOLO_SIGNATURE)
    assert dup.attempt_count == 2 and solo.attempt_count == 1
    assert compute_confidence(dup) > compute_confidence(solo) > 0.0
    # One harvest is never enough: every candidate is still gated (dwell/evidence).
    patterns = _fresh_patterns(tmp_path)
    evaluated = evaluate_queue(report_h.candidates, patterns_path=patterns)
    assert auto_promote(evaluated, patterns_path=patterns, dry_run=True) == []


def test_approve_writes_governed_learning_source(tmp_path):
    """Promoted KB records are attributed to governed_learning, not runtime_block."""
    jsonl = tmp_path / "failure-patterns.jsonl"
    cand = _make_candidate(tmp_path, confidence=0.98, attempt_count=5, created_days_ago=30)
    cand = evaluate_candidate(cand, patterns_path=jsonl)
    approve_candidate(
        cand, approver="alice", patterns_path=jsonl,
        approvals_path=tmp_path / "approvals.jsonl",
    )
    records = failure_kb.load_jsonl(jsonl)
    assert records, "approve must persist to the canonical jsonl"
    assert {r.source for r in records} == {"governed_learning"}


# ---------------------------------------------------------------------------
# End-to-end counter-proof: the gate is alive (P0-2 acceptance)
# ---------------------------------------------------------------------------

def test_e2e_real_pipeline_promotes_one_candidate(tmp_path):
    """Seeded age + MIN_ATTEMPT_COUNT real harvest processes → 1 promotion."""
    state_path = tmp_path / "candidate-state.json"
    queue = tmp_path / "queue.json"
    approvals = tmp_path / "approvals.jsonl"
    library = tmp_path / "failure-patterns.jsonl"
    library.write_bytes((REPO / "docs" / "failure-patterns.jsonl").read_bytes())

    # Age is injected via a seeded first_seen (no sleeping, no clock mocking).
    seeded = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    _seed_state(state_path, FIXTURE_SOLO_SIGNATURE, seeded)

    for i in range(MIN_ATTEMPT_COUNT):
        _cli_harvest(state_path, queue)

    def _cli(args: list[str]) -> str:
        r = subprocess.run(
            [sys.executable, str(SCRIPTS / "governed_learning.py"), *args],
            cwd=str(REPO), capture_output=True, text=True, check=False,
        )
        assert r.returncode == 0, r.stderr + r.stdout
        return r.stdout

    _cli(["evaluate", "--queue", str(queue), "--patterns", str(library)])
    out = _cli(["promote", "--queue", str(queue), "--patterns", str(library),
                "--approvals", str(approvals)])

    cands = {c.signature: c for c in load_queue(queue)}
    solo = cands[FIXTURE_SOLO_SIGNATURE]
    assert solo.attempt_count >= MIN_ATTEMPT_COUNT
    assert solo.confidence >= MIN_CONFIDENCE
    assert solo.status == "approved"

    promoted = [c for c in cands.values() if c.approval and c.approval.get("approver") == "system:auto"]
    assert len(promoted) == 1, f"expected exactly 1 promotion, got {len(promoted)}"
    assert f"1 / {len(cands)}" in out
    # The CLI must persist the post-promotion rate, not the pre-promotion 0.0.
    assert json.loads(queue.read_text())["auto_promotion_rate"] == pytest.approx(1 / len(cands))
    assert auto_promotion_rate(queue) > 0.0
    assert {r.source for r in failure_kb.load_jsonl(library) if r.error_signature == FIXTURE_SOLO_SIGNATURE} == {"governed_learning"}


def test_age_hours_invalid_created_at_returns_zero():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert governed_learning._age_hours(None, now) == 0.0  # type: ignore[arg-type]
    assert governed_learning._age_hours(42, now) == 0.0  # type: ignore[arg-type]
    assert governed_learning._age_hours("2026-01-01", now) == 0.0


# ---------------------------------------------------------------------------
# Gate 5 observability: injected clock + dwell-stats
# ---------------------------------------------------------------------------

def test_auto_promote_gate5_passes_once_dwell_elapsed(tmp_path):
    """With an injectable clock, the same candidate flips at exactly 168h."""
    patterns = _fresh_patterns(tmp_path)
    approvals = tmp_path / "approvals.jsonl"
    created = datetime(2026, 1, 1, tzinfo=timezone.utc)
    cand = _make_candidate(tmp_path, confidence=0.98, attempt_count=5, error="timeout")
    cand.created_at = created.strftime("%Y-%m-%dT%H:%M:%SZ")

    blocked: dict[str, list[str]] = {}
    too_young = auto_promote(
        [cand], patterns_path=patterns, approvals_path=approvals,
        now=created + timedelta(hours=MIN_DWELL_HOURS - 1), blocked_by=blocked,
    )
    assert too_young == []
    assert blocked == {cand.id: [GATE_DWELL]}

    promoted = auto_promote(
        [cand], patterns_path=patterns, approvals_path=approvals,
        now=created + timedelta(hours=MIN_DWELL_HOURS),
    )
    assert len(promoted) == 1
    assert promoted[0].approval["approver"] == "system:auto"


def test_dwell_stats_blocked_by_gate5(tmp_path):
    """dwell_stats names the Gate-5-blocked candidate and its real age."""
    patterns = _fresh_patterns(tmp_path)
    now = datetime.now(timezone.utc)
    young = _make_candidate(tmp_path, confidence=0.98, attempt_count=5, error="timeout")
    young.created_at = (now - timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ")
    old = _make_candidate(
        tmp_path, confidence=0.98, attempt_count=5, error="timeout",
        command="aws test stale-thing",
    )
    old.created_at = (now - timedelta(hours=200)).strftime("%Y-%m-%dT%H:%M:%SZ")

    stats = dwell_stats([young, old], patterns_path=patterns)
    assert stats["pending_total"] == 2
    assert stats["age_histogram_hours"] == {"<24h": 1, ">=168h": 1}
    assert stats["blocked_by_gate"] == {GATE_DWELL: 1, "promotable": 1}
    assert stats["dwell_blocked_count"] == 1
    blocked = stats["dwell_blocked"][0]
    assert blocked["id"] == young.id
    assert blocked["blocking_gates"] == [GATE_DWELL]
    assert blocked["terminal"] is False
    assert blocked["terminal_gates"] == []
    assert 5.5 < blocked["age_hours"] < 7.0
    assert 160.0 < blocked["hours_remaining"] < 163.0


def test_dwell_stats_reports_all_gates_and_terminal_block(tmp_path):
    patterns = _fresh_patterns(tmp_path)
    now = datetime(2026, 1, 10, tzinfo=timezone.utc)
    unsafe = _make_candidate(
        tmp_path,
        confidence=0.98,
        attempt_count=5,
        created_days_ago=1,
        error="safety=0.0",
        source_status="SAFETY_FAIL",
    )
    unsafe.created_at = (now - timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ")
    blocked: dict[str, list[str]] = {}

    assert auto_promote(
        [unsafe], patterns_path=patterns, now=now, blocked_by=blocked,
    ) == []
    assert blocked == {unsafe.id: [GATE_DWELL, GATE_SAFETY]}

    stats = dwell_stats([unsafe], patterns_path=patterns, now=now)
    assert stats["blocked_by_gate"] == {GATE_DWELL: 1, GATE_SAFETY: 1}
    assert stats["terminal_blocked_count"] == 1
    entry = stats["dwell_blocked"][0]
    assert entry["blocking_gates"] == [GATE_DWELL, GATE_SAFETY]
    assert entry["terminal_gates"] == [GATE_SAFETY]
    assert entry["terminal"] is True
    assert entry["hours_remaining"] is None


def test_cli_report_dwell_stats(tmp_path):
    """`report --dwell-stats` surfaces the Gate-5-blocked pending candidate."""
    patterns = _fresh_patterns(tmp_path)
    q = tmp_path / "queue.json"
    young = _make_candidate(tmp_path, confidence=0.98, attempt_count=5, error="timeout")
    young.created_at = (datetime.now(timezone.utc) - timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ")
    save_queue(q, [young])
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "governed_learning.py"),
         "report", "--queue", str(q), "--patterns", str(patterns), "--dwell-stats"],
        cwd=str(REPO), capture_output=True, text=True, check=False,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    data = json.loads(r.stdout)
    assert data["dwell_blocked_count"] == 1
    assert data["dwell_blocked"][0]["id"] == young.id
    assert data["blocked_by_gate"][GATE_DWELL] == 1


def test_cli_promote_reports_blocked_by(tmp_path):
    patterns = _fresh_patterns(tmp_path)
    q = tmp_path / "queue.json"
    young = _make_candidate(tmp_path, confidence=0.98, attempt_count=5, error="timeout")
    young.created_at = (datetime.now(timezone.utc) - timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ")
    save_queue(q, [young])
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "governed_learning.py"),
         "promote", "--queue", str(q), "--patterns", str(patterns), "--dry-run"],
        cwd=str(REPO), capture_output=True, text=True, check=False,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert "0 / 1" in r.stdout
    assert GATE_DWELL in r.stdout


# ---------------------------------------------------------------------------
# Contract C2: library may be canonical .jsonl, not just legacy markdown
# ---------------------------------------------------------------------------

def test_library_signatures_supports_jsonl_and_gate7(tmp_path):
    jsonl = tmp_path / "failure-patterns.jsonl"
    owned = "aws-jsonl-ops|aws jsonl delete|timeout"
    from failure_kb import append_or_increment as kb_append
    kb_append(FailureRecord(
        skill="aws-jsonl-ops", command="aws jsonl delete", error="timeout",
        error_signature=owned, root_cause="r", fix="f",
        first_seen="2026-01-01T00:00:00Z", last_seen="2026-01-01T00:00:00Z",
        source="governed_learning",
    ), jsonl)

    sigs = _library_signatures(jsonl)
    assert owned in sigs, "jsonl library must be readable (C2)"

    # Gate 7 must block a candidate already present in the jsonl library.
    cand = _make_candidate(
        tmp_path, skill="aws-jsonl-ops", command="aws jsonl delete", error="timeout",
        confidence=0.98, attempt_count=5, created_days_ago=30,
    )
    now = datetime.now(timezone.utc)
    blocked: dict[str, list[str]] = {}
    assert auto_promote([cand], patterns_path=jsonl, now=now, blocked_by=blocked) == []
    assert blocked == {cand.id: [GATE_DUPLICATE]}
    assert blocking_gate(cand, lib=_library_signatures(jsonl), now=now) == [GATE_DUPLICATE]


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
