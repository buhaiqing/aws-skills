"""TDD tests for scripts/cross_skill_transfer.py - L4 Gap 5.

Property invariants:
- the critic gate NEVER accepts below min_evidence (fuzzed inputs)
- harvest output NEVER contains duplicate (source, target, fact) triples
"""
from __future__ import annotations

import sys
from pathlib import Path
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

REPO = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from cross_skill_transfer import (  # noqa: E402
    GENERIC_BLOCKLIST,
    MIN_EVIDENCE,
    TransferCandidate,
    gcl_gate_transfer,
    harvest_transfer_candidates,
    load_skill_deps,
    report,
)


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------


def _make_skill(root: Path, name: str, deps: list[str] | None) -> None:
    skill_dir = root / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    body = f"# {name}\n\n## Dependencies\n\n"
    if deps is not None:
        body += "cross_skill_deps:\n"
        body += "".join(f"  - {d}\n" for d in deps)
    (skill_dir / "SKILL.md").write_text(body, encoding="utf-8")


def test_load_skill_deps_parses_declarations(tmp_path):
    _make_skill(tmp_path, "aws-ec2-ops", None)
    _make_skill(tmp_path, "aws-topo-ops", ["aws-ec2-ops"])
    deps = load_skill_deps(tmp_path)
    assert deps == {"aws-topo-ops": ["aws-ec2-ops"]}


def test_load_skill_deps_tolerant_of_missing_dir(tmp_path):
    assert load_skill_deps(tmp_path / "nope") == {}


def test_load_skill_deps_ignores_self_reference(tmp_path):
    _make_skill(tmp_path, "aws-ec2-ops", ["aws-ec2-ops"])
    assert load_skill_deps(tmp_path) == {}


# ---------------------------------------------------------------------------
# harvest_transfer_candidates
# ---------------------------------------------------------------------------


def _pattern(skill: str, command: str, fix: str = "", count: int = 1) -> dict:
    return {
        "skill": skill,
        "command": command,
        "error": "SomeError",
        "root_cause": "root",
        "fix": fix,
        "count": count,
        "timestamp": "2026-08-26T00:00:00+00:00",
    }


def test_harvest_flows_downstream_only(tmp_path):
    """Knowledge flows source -> dependents: topo lists ec2 as a dep, so
    lessons harvested in ec2 transfer to topo; topo's own lessons go
    nowhere (nobody lists topo)."""
    _make_skill(tmp_path, "aws-ec2-ops", None)
    _make_skill(tmp_path, "aws-topo-ops", ["aws-ec2-ops"])

    # topo's pattern: no skill lists topo -> no candidates
    assert harvest_transfer_candidates(
        tmp_path, [_pattern("aws-topo-ops", "aws topo run")],
    ) == []

    # ec2's pattern: topo lists ec2 -> one candidate
    cands = harvest_transfer_candidates(
        tmp_path, [_pattern("aws-ec2-ops", "aws ec2 run", fix="use --flag")],
    )
    assert len(cands) == 1
    assert cands[0].source_skill == "aws-ec2-ops"
    assert cands[0].target_skill == "aws-topo-ops"
    assert cands[0].fact == "aws ec2 run: use --flag"


def test_harvest_dedups_by_source_target_fact(tmp_path):
    _make_skill(tmp_path, "aws-ec2-ops", None)
    _make_skill(tmp_path, "aws-topo-ops", ["aws-ec2-ops"])
    rows = [
        _pattern("aws-ec2-ops", "aws ec2 run", fix="use --flag"),
        _pattern("aws-ec2-ops", "aws ec2 run", fix="use --flag"),
    ]
    cands = harvest_transfer_candidates(tmp_path, rows)
    assert len(cands) == 1


def test_harvest_skips_rows_without_skill_or_command(tmp_path):
    _make_skill(tmp_path, "aws-ec2-ops", ["aws-topo-ops"])
    cands = harvest_transfer_candidates(
        tmp_path, [{"skill": "", "command": ""}, {"skill": "aws-ec2-ops"}],
    )
    assert cands == []


# ---------------------------------------------------------------------------
# gcl_gate_transfer (critic)
# ---------------------------------------------------------------------------


def _cand(evidence: int, fact: str = "aws ec2 run: use --flag") -> TransferCandidate:
    return TransferCandidate(
        source_skill="aws-ec2-ops",
        target_skill="aws-topo-ops",
        fact=fact,
        evidence_count=evidence,
    )


def test_gate_rejects_below_min_evidence():
    assert gcl_gate_transfer(_cand(MIN_EVIDENCE - 1)).status == "rejected"


def test_gate_accepts_at_min_evidence():
    assert gcl_gate_transfer(_cand(MIN_EVIDENCE)).status == "accepted"


def test_gate_rejects_self_transfer():
    c = TransferCandidate(
        source_skill="aws-ec2-ops", target_skill="aws-ec2-ops",
        fact="f", evidence_count=99,
    )
    assert gcl_gate_transfer(c).status == "rejected"


def test_gate_generic_fact_needs_double_evidence():
    generic_fact = "aws ec2 run: throttling backoff"
    assert any(g in generic_fact for g in GENERIC_BLOCKLIST)
    assert gcl_gate_transfer(_cand(2 * MIN_EVIDENCE - 1, generic_fact)).status == "rejected"
    assert gcl_gate_transfer(_cand(2 * MIN_EVIDENCE, generic_fact)).status == "accepted"


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------


def test_report_counts_and_rate():
    cands = [_cand(5), _cand(0), _cand(1)]
    gated = [gcl_gate_transfer(c) for c in cands]
    rep = report(gated)
    assert rep["total"] == 3
    assert rep["accepted"] == 1
    assert rep["rejected"] == 2
    assert rep["acceptance_rate"] == round(1 / 3, 4)


def test_report_empty():
    assert report([]) == {
        "total": 0, "accepted": 0, "rejected": 0, "acceptance_rate": 0.0,
    }


# ---------------------------------------------------------------------------
# Hypothesis property tests
# ---------------------------------------------------------------------------


@settings(max_examples=50, deadline=None)
@given(
    evidence=st.integers(min_value=0, max_value=1000),
    fact=st.text(min_size=0, max_size=120),
    min_evidence=st.integers(min_value=1, max_value=10),
)
def test_gate_never_accepts_below_min_evidence(evidence, fact, min_evidence):
    """Property: accepted implies evidence_count >= min_evidence."""
    c = _cand(evidence, fact=fact or "f")
    out = gcl_gate_transfer(c, min_evidence=min_evidence)
    if out.status == "accepted":
        assert out.evidence_count >= min_evidence
        assert out.source_skill != out.target_skill


@settings(
    max_examples=30, deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    rows=st.lists(
        st.fixed_dictionaries({
            "skill": st.sampled_from(["aws-a-ops", "aws-b-ops"]),
            "command": st.sampled_from(["cmd one", "cmd two"]),
            "error": st.just("E"),
            "root_cause": st.just("rc"),
            "fix": st.sampled_from(["", "fix x"]),
            "count": st.integers(min_value=1, max_value=9),
            "timestamp": st.just("t"),
        }),
        max_size=20,
    ),
)
def test_harvest_never_duplicates_triples(tmp_path, rows):
    """Property: (source, target, fact) triples are unique in harvest output."""
    _make_skill(tmp_path, "aws-a-ops", ["aws-b-ops"])
    _make_skill(tmp_path, "aws-b-ops", None)
    cands = harvest_transfer_candidates(tmp_path, rows)
    keys = [(c.source_skill, c.target_skill, c.fact) for c in cands]
    assert len(keys) == len(set(keys))
