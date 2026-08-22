"""TDD tests for scripts/failure_kb.py — P0 failure knowledge base."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from failure_kb import FailureRecord, append_or_increment, export_markdown, load_jsonl, search_lexical  # noqa: E402


# -- helpers ---------------------------------------------------------------

def _rec(**overrides) -> FailureRecord:
    base = {
        "id": "fp-000001",
        "category": "cli_parameter",
        "skill": "aws-ec2-ops",
        "command": "aws ec2 terminate-instances",
        "error": "MissingParameter",
        "error_signature": "ec2-ops|terminate-instances|MissingParameter",
        "root_cause": "Missing --instance-ids",
        "fix": "--instance-ids i-xxx",
        "count": 1,
        "first_seen": "2026-06-04T00:00:00Z",
        "last_seen": "2026-06-04T00:00:00Z",
        "source": "gcl_trace",
        "tags": [],
        "vector": None,
    }
    base.update(overrides)
    return FailureRecord(**base)


def _rec_dict(**overrides) -> dict:
    r = _rec(**overrides)
    return {
        "id": r.id,
        "category": r.category,
        "skill": r.skill,
        "command": r.command,
        "error": r.error,
        "error_signature": r.error_signature,
        "root_cause": r.root_cause,
        "fix": r.fix,
        "count": r.count,
        "first_seen": r.first_seen,
        "last_seen": r.last_seen,
        "source": r.source,
        "tags": r.tags,
        "vector": r.vector,
    }


# -- 13 tests --------------------------------------------------------------

def test_failure_record_from_dict():
    d = _rec_dict()
    rec = FailureRecord.from_dict(d)
    assert rec.id == "fp-000001"
    assert rec.category == "cli_parameter"
    assert rec.skill == "aws-ec2-ops"
    assert rec.count == 1
    assert rec.tags == []
    assert rec.vector is None
    # round-trip
    assert rec.to_dict()["id"] == "fp-000001"
    # id format
    assert rec.id.startswith("fp-")
    # category enum membership
    assert rec.category in {
        "cli_parameter", "query_miss", "skill_generation",
        "cross_skill", "runtime", "token_efficiency",
    }
    assert rec.source in {
        "gcl_trace", "self_review", "runtime_block", "manual", "governed_learning",
    }


def test_load_jsonl_valid(tmp_path: Path):
    p = tmp_path / "kb.jsonl"
    r1 = _rec_dict()
    r2 = _rec_dict(id="fp-000002", skill="aws-s3-ops", command="aws s3 rm", error="NoSuchBucket",
                   error_signature="s3-ops|rm|NoSuchBucket")
    p.write_text(json.dumps(r1) + "\n" + json.dumps(r2) + "\n", encoding="utf-8")
    records = load_jsonl(p)
    assert len(records) == 2
    assert records[0].id == "fp-000001"
    assert records[1].skill == "aws-s3-ops"


def test_load_jsonl_empty(tmp_path: Path):
    p = tmp_path / "empty.jsonl"
    p.write_text("", encoding="utf-8")
    assert load_jsonl(p) == []
    # also non-existent file
    assert load_jsonl(tmp_path / "nope.jsonl") == []


def test_load_jsonl_invalid_json(tmp_path: Path):
    p = tmp_path / "bad.jsonl"
    p.write_text('{"id": "fp-000001"}\nnot-json\n', encoding="utf-8")
    with pytest.raises(ValueError, match="line 2"):
        load_jsonl(p)


def test_append_new_record(tmp_path: Path):
    p = tmp_path / "kb.jsonl"
    rec = _rec(id="", error_signature="sig-new")
    result = append_or_increment([rec], p)
    assert result in ("appended", "incremented")
    records = load_jsonl(p)
    assert len(records) == 1
    assert records[0].error_signature == "sig-new"


def test_append_increment_existing(tmp_path: Path):
    p = tmp_path / "kb.jsonl"
    rec1 = _rec(error_signature="sig-dup", count=1)
    append_or_increment([rec1], p)
    rec2 = _rec(error_signature="sig-dup", count=1)
    result = append_or_increment([rec2], p)
    assert result == "incremented"
    records = load_jsonl(p)
    assert len(records) == 1
    assert records[0].count == 2


def test_append_idempotent(tmp_path: Path):
    p = tmp_path / "kb.jsonl"
    sig = "sig-idem"
    for _ in range(3):
        append_or_increment([_rec(error_signature=sig)], p)
    records = load_jsonl(p)
    assert len(records) == 1
    assert records[0].count == 3
    # verify atomic write produced valid JSONL
    lines = p.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    json.loads(lines[0])


def test_append_generates_id(tmp_path: Path):
    p = tmp_path / "kb.jsonl"
    rec = _rec(id="", error_signature="sig-gen")
    append_or_increment([rec], p)
    records = load_jsonl(p)
    assert len(records) == 1
    assert records[0].id.startswith("fp-")
    # fp-NNNNNN format (6 digits)
    assert len(records[0].id) == 9  # fp- + 6 digits
    assert records[0].id[3:].isdigit()


def test_search_lexical_basic():
    r1 = _rec(skill="aws-ec2-ops", command="aws ec2 terminate-instances",
              error="MissingParameter", root_cause="Missing --instance-ids")
    r2 = _rec(id="fp-000002", skill="aws-s3-ops", command="aws s3 rm",
              error="NoSuchBucket", root_cause="bucket not found",
              error_signature="sig2")
    r3 = _rec(id="fp-000003", skill="aws-iam-ops", command="aws iam create-user",
              error="EntityAlreadyExists", root_cause="user exists",
              error_signature="sig3")
    results = search_lexical("terminate instance missing", [r1, r2, r3], k=5)
    assert len(results) >= 1
    assert results[0].skill == "aws-ec2-ops"


def test_search_lexical_top_k():
    recs = [
        _rec(id=f"fp-{i:06d}", skill="aws-ec2-ops", command="aws ec2 terminate-instances",
             error_signature=f"sig-{i}")
        for i in range(10)
    ]
    results = search_lexical("terminate", recs, k=3)
    assert len(results) == 3


def test_search_lexical_empty_query():
    recs = [_rec()]
    assert search_lexical("", recs) == []
    assert search_lexical("   ", recs) == []


def test_export_markdown_structure():
    recs = [
        _rec(category="cli_parameter"),
        _rec(id="fp-000002", category="runtime", skill="aws-lambda-ops",
             command="aws lambda delete-function", error="X",
             error_signature="sig-runtime", source="manual"),
    ]
    md = export_markdown(recs)
    assert "cli_parameter" in md
    assert "runtime" in md
    # tables
    assert "|" in md
    assert "aws-ec2-ops" in md
    assert "aws-lambda-ops" in md


def test_export_markdown_header():
    md = export_markdown([_rec()])
    assert "AUTO-GENERATED" in md


def test_cli_export(tmp_path: Path):
    p_in = tmp_path / "in.jsonl"
    p_out = tmp_path / "out.md"
    p_in.write_text(json.dumps(_rec_dict()) + "\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "failure_kb.py"), "export",
         "--input", str(p_in), "--output", str(p_out)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    assert p_out.exists()
    assert "AUTO-GENERATED" in p_out.read_text(encoding="utf-8")
