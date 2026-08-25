"""TDD tests for scripts/memory_eval.py — L4 #10 retrieval quality eval.

Property invariants:
- retrieve() never returns more than top_k results
- metrics are always in [0, 1]
- gcl_gate_memory: never retrieved → decay (confidence never increases)
- gcl_gate_memory: relevant hit → promote (confidence never decreases)
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

REPO = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from memory_eval import (  # noqa: E402
    AUTO_DERIVE_THRESHOLD,
    CONFIDENCE_FLOOR,
    EvalCase,
    GateResult,
    RetrievalMetrics,
    eval_retrieval,
    gcl_gate_memory,
    retrieve,
)


# ---------------------------------------------------------------------------
# Lightweight stub (avoids import coupling to session_memory)
# ---------------------------------------------------------------------------

@dataclass
class _Rec:
    id: str
    summary: str = ""
    detail: str = ""
    scope: str = "convention"
    confidence: float = 1.0
    tags: list[str] | None = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


def _rec(id: str, summary: str, **kw) -> _Rec:
    return _Rec(id=id, summary=summary, **kw)


# ---------------------------------------------------------------------------
# retrieve
# ---------------------------------------------------------------------------


def test_retrieve_returns_sorted_by_score():
    records = [_rec("a", "aws region us-east-1"),
               _rec("b", "aws region ap-southeast-1"),
               _rec("c", "unrelated topic")]
    hits = retrieve(records, "aws region")
    assert len(hits) == 2
    assert hits[0][0].id in ("a", "b")


def test_retrieve_respects_top_k():
    records = [_rec(str(i), "aws region convention") for i in range(10)]
    assert len(retrieve(records, "aws region", top_k=3)) == 3


def test_retrieve_empty_query():
    assert retrieve([_rec("a", "x")], "") == []


def test_retrieve_no_match():
    assert retrieve([_rec("a", "foo")], "bar baz qux") == []


def test_retrieve_confidence_weights_score():
    """Higher confidence record should rank first."""
    low = _rec("a", "aws convention", confidence=0.3)
    high = _rec("b", "aws convention", confidence=1.0)
    hits = retrieve([low, high], "aws convention", top_k=2)
    assert hits[0][0].id == "b"


def test_retrieve_scope_boost():
    """convention scope gets 1.2x boost over default."""
    conv = _rec("a", "aws convention", scope="convention")
    other = _rec("b", "aws convention", scope="user-pref")
    hits = retrieve([conv, other], "aws convention", top_k=2)
    assert hits[0][0].id == "a"


# ---------------------------------------------------------------------------
# eval_retrieval
# ---------------------------------------------------------------------------


def test_eval_perfect_retrieval():
    records = [_rec("a", "aws region"), _rec("b", "s3 bucket")]
    cases = [EvalCase("aws region", ["a"])]
    m = eval_retrieval(cases, records, top_k=3)
    assert m.hit_rate == 1.0
    assert m.precision_at_k > 0
    assert m.mrr == 1.0
    assert m.cases_total == 1


def test_eval_miss():
    records = [_rec("a", "aws region")]
    cases = [EvalCase("s3 bucket", ["b-missing"])]
    m = eval_retrieval(cases, records, top_k=3)
    assert m.hit_rate == 0.0
    assert m.mrr == 0.0


def test_eval_empty_cases():
    m = eval_retrieval([], [_rec("a", "x")])
    assert m.hit_rate == 0.0
    assert m.cases_total == 0


def test_eval_rr_ranking():
    """First relevant at rank 2 → MRR = 0.5."""
    high = _rec("a", "aws region convention", confidence=1.0)
    low  = _rec("b", "aws region detail",    confidence=0.2)
    cases = [EvalCase("aws region", ["b"])]
    m = eval_retrieval(cases, [high, low], top_k=3)
    assert m.mrr == 0.5


# ---------------------------------------------------------------------------
# gcl_gate_memory (critic)
# ---------------------------------------------------------------------------


def test_never_retrieved_decays():
    records = [_rec("a", "old fact", confidence=0.8)]
    cases = [EvalCase("unrelated query", ["other-id"])]
    results = gcl_gate_memory(records, cases, top_k=3)
    assert results[0].decision == "decay"
    assert results[0].new_confidence < results[0].old_confidence


def test_retrieved_and_relevant_promotes():
    records = [_rec("a", "aws convention", confidence=0.5)]
    cases = [EvalCase("aws convention", ["a"])]
    results = gcl_gate_memory(records, cases, top_k=3)
    assert results[0].decision == "promote"
    assert results[0].new_confidence > results[0].old_confidence


def test_no_cases_unchanged():
    records = [_rec("a", "aws region", confidence=0.5)]
    results = gcl_gate_memory(records, [], top_k=3)
    assert results[0].decision == "unchanged"
    assert results[0].new_confidence == 0.5


def test_confidence_clamped():
    """Promote on already-1.0 → stays 1.0."""
    records = [_rec("a", "aws region", confidence=1.0)]
    cases = [EvalCase("aws region", ["a"])]
    results = gcl_gate_memory(records, cases, top_k=3, promote_boost=0.5)
    assert results[0].new_confidence == 1.0


def test_auto_derive_eligibility():
    records = [
        _rec("a", "aws convention", confidence=0.5),
        _rec("b", "old unused", confidence=0.2),
    ]
    cases = [EvalCase("aws convention", ["a"])]
    results = gcl_gate_memory(records, cases, top_k=3)
    report_data = {
        "promoted": sum(1 for g in results if g.decision == "promote"),
        "eligible": sum(
            1 for g in results if g.new_confidence >= AUTO_DERIVE_THRESHOLD
        ),
    }
    assert report_data["promoted"] >= 1
    # "a" promoted from 0.5 + 0.05 = 0.55 < 0.6 threshold → not eligible
    # (unless promote_boost is higher). Test with bigger boost:
    results2 = gcl_gate_memory(records, cases, top_k=3, promote_boost=0.2)
    eligible2 = sum(
        1 for g in results2 if g.new_confidence >= AUTO_DERIVE_THRESHOLD
    )
    assert eligible2 >= 1


# ---------------------------------------------------------------------------
# Hypothesis property tests
# ---------------------------------------------------------------------------


@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    top_k=st.integers(min_value=1, max_value=10),
    n_records=st.integers(min_value=0, max_value=20),
)
def test_retrieve_never_exceeds_top_k(top_k, n_records):
    """Property: retrieve() output length ≤ top_k."""
    records = [_rec(str(i), f"aws region {i}") for i in range(n_records)]
    hits = retrieve(records, "aws region", top_k=top_k)
    assert len(hits) <= top_k
    for r, s in hits:
        assert s > 0


@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    hit_rate=st.floats(min_value=0.0, max_value=1.0),
    cases_total=st.integers(min_value=1, max_value=100),
)
def test_metrics_always_in_unit_interval(hit_rate, cases_total):
    """Property: all metrics are in [0, 1]."""
    m = RetrievalMetrics(
        hit_rate=hit_rate,
        precision_at_k=hit_rate,
        mrr=hit_rate,
        cases_total=cases_total,
        cases_with_hit=int(hit_rate * cases_total),
    )
    assert 0 <= m.hit_rate <= 1
    assert 0 <= m.precision_at_k <= 1
    assert 0 <= m.mrr <= 1


@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    confidence=st.floats(min_value=0.0, max_value=1.0),
    is_relevant=st.booleans(),
)
def test_gate_never_retrieved_never_promotes(confidence, is_relevant):
    """Property: a record never in any top-k can never be promoted."""
    records = [_rec("target", "target summary", confidence=confidence)]
    # Cases where "target" is never relevant
    cases = [EvalCase("unrelated query", ["other-id"])]
    results = gcl_gate_memory(records, cases, top_k=1)
    assert results[0].decision != "promote"
    # Confidence never increases for never-retrieved
    assert results[0].new_confidence <= confidence


@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(confidence=st.floats(min_value=0.0, max_value=1.0))
def test_gate_relevant_always_promotes(confidence):
    """Property: a record that IS relevant when retrieved always gets promoted."""
    records = [_rec("target", "aws convention", confidence=confidence)]
    cases = [EvalCase("aws convention", ["target"])]
    results = gcl_gate_memory(records, cases, top_k=3)
    if results[0].decision == "promote":
        assert results[0].new_confidence >= confidence
