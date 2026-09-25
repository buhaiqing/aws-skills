import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
from learning_outcomes import append_event, build_report, verify_ledger  # noqa: E402


def event(event_id, kind, candidate="c1", **extra):
    return {"event_id": event_id, "event_type": kind, "candidate_id": candidate, **extra}


def test_append_is_idempotent_and_append_only(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    first = event("a", "candidate_proposed")
    assert append_event(path, first)
    assert not append_event(path, first)
    assert append_event(path, event("b", "candidate_evaluated"))
    assert [json.loads(line)["event_id"] for line in path.read_text().splitlines()] == ["a", "b"]


def test_malformed_event_fails_closed(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    with pytest.raises(ValueError):
        append_event(path, {"event_id": "x"})
    path.write_text('{"event_id":"x","event_type":"candidate_proposed"}\n')
    assert not verify_ledger(path)


def test_report_counts_chain_and_delta_and_rollback_rate():
    events = [
        event("1", "candidate_proposed", delta=0),
        event("2", "candidate_evaluated"),
        event("3", "promotion_recorded"),
        event("4", "deployment_observed"),
        event("5", "post_deploy_measured", delta=4),
        event("6", "rollback_recorded"),
        event("7", "candidate_proposed", candidate="c2"),
    ]
    report = build_report(events)
    assert report["event_counts"]["candidate_proposed"] == 2
    assert report["complete_chains"] == 1
    assert report["post_deploy_delta"] == 4
    assert report["rollback_rate"] == 1.0


def test_cli_verify_empty_ledger(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    path.touch()
    result = subprocess.run([sys.executable, str(REPO / "scripts/learning_outcomes.py"), "verify", "--ledger", str(path)], text=True)
    assert result.returncode == 0
