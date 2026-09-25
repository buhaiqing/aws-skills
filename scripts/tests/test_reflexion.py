"""TDD tests for scripts/_reflexion.py — L4 dim #3 reflexion automation.

Real fixtures: scripts/tests/fixtures/gcl-traces/ (committed; audit-results is gitignored).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

REPO = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import failure_kb  # noqa: E402
# Captured at import: runtime_safety/gcl_runner re-register a *copy* of
# _reflexion in sys.modules (their exec'd loader), so a later `import
# _reflexion` would not be the module whose globals _cli_main reads.
import _reflexion as _reflexion_module  # noqa: E402
from _reflexion import (  # noqa: E402
    FailurePattern,
    derive_from_error,
    derive_from_trace,
    append_or_increment,
    prune_low_frequency,
)


_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "gcl-traces"
SAFETY_FAIL_TRACE = _FIXTURES / "gcl-trace-20260627-031257.json"
MAX_ITER_TRACE = _FIXTURES / "gcl-trace-20260627-031303.json"


def test_derive_from_pass_trace_returns_empty():
    """PASS status → no patterns (we only reflect on failures)."""
    trace = {"final": {"status": "PASS"}, "iterations": [{"critic": {"scores": {"safety": 1.0}}}]}
    assert derive_from_trace(trace) == []


def test_derive_from_safety_fail_returns_one_pattern():
    """SAFETY_FAIL trace → 1 pattern referencing the failing dimension."""
    trace = json.loads(SAFETY_FAIL_TRACE.read_text())
    patterns = derive_from_trace(trace)
    assert len(patterns) == 1
    p = patterns[0]
    assert p.skill == "aws-s3-ops"
    assert "safety" in p.error
    assert p.command == "aws --self-test"
    # timestamp must be ISO 8601
    parsed_ts = datetime.fromisoformat(p.timestamp)
    assert parsed_ts.tzinfo is not None


def test_derive_from_max_iter_returns_one_pattern():
    """MAX_ITER trace → 1 pattern referencing the failing dimension (idempotency)."""
    trace = json.loads(MAX_ITER_TRACE.read_text())
    patterns = derive_from_trace(trace)
    assert len(patterns) == 1
    p = patterns[0]
    assert p.skill == "aws-s3-ops"
    assert "idempotency" in p.error


def test_append_or_increment_adds_new_row(tmp_path):
    """Empty file → first append creates header + 1 row."""
    target = tmp_path / "failure-patterns.md"
    pat = FailurePattern(
        skill="aws-test-ops", command="aws test",
        error="safety=0.0", root_cause="r", fix="f", timestamp="2026-07-25T00:00:00+00:00",
    )
    result = append_or_increment(target, pat)
    assert result == "appended"
    text = target.read_text()
    assert "aws-test-ops" in text
    assert "safety=0.0" in text
    # Count column = 1
    assert "| 1 |" in text


def test_append_or_increment_dedups_and_increments(tmp_path):
    """Same pattern appended twice → count = 2, only 1 row."""
    target = tmp_path / "failure-patterns.md"
    pat = FailurePattern(
        skill="aws-test-ops", command="aws test",
        error="safety=0.0", root_cause="r", fix="f", timestamp="2026-07-25T00:00:00+00:00",
    )
    append_or_increment(target, pat)
    pat2 = FailurePattern(
        skill="aws-test-ops", command="aws test",
        error="safety=0.0", root_cause="r", fix="f", timestamp="2026-07-25T00:01:00+00:00",
    )
    result = append_or_increment(target, pat2)
    assert result == "incremented"
    text = target.read_text()
    # Only one data row
    data_rows = [ln for ln in text.splitlines() if ln.startswith("| aws-test-ops")]
    assert len(data_rows) == 1
    assert "| 2 |" in text


def test_prune_removes_low_frequency(tmp_path):
    """Prune drops count < min_count."""
    target = tmp_path / "failure-patterns.md"
    target.write_text(
        "# Test\n## Section\n| skill | command | error | root_cause | fix | count | timestamp |\n|-------|---------|-------|------------|-----|-------|-----------|\n"
        "| aws-a | cmd | err-A | rc | fx | 1 | ts |\n"
        "| aws-b | cmd | err-B | rc | fx | 1 | ts |\n"
        "| aws-c | cmd | err-C | rc | fx | 1 | ts |\n"
        "| aws-d | cmd | err-D | rc | fx | 1 | ts |\n"
        "| aws-e | cmd | err-E | rc | fx | 1 | ts |\n"
        "| aws-keep | cmd | err-K | rc | fx | 5 | ts |\n"
    )
    removed = prune_low_frequency(target, min_count=3, max_lines=10)
    assert removed == 5
    text = target.read_text()
    assert "aws-keep" in text
    assert "aws-a" not in text


def test_gcl_runner_self_test_on_fail_appends_to_failure_patterns(tmp_path):
    """End-to-end: gcl_runner.py --self-test --on-fail → appends to failure-patterns.md."""
    target = tmp_path / "failure-patterns.md"
    result = subprocess.run(
        [
            sys.executable, str(SCRIPTS_DIR / "gcl_runner.py"),
            "--skill", "aws-s3-ops",
            "--request", "delete bucket test",  # destructive → safety=0 → SAFETY_FAIL
            "--self-test", "--no-prune", "--on-fail",
            "--failure-patterns", str(target),
        ],
        capture_output=True, text=True, cwd=str(REPO), timeout=60,
    )
    assert target.exists(), f"--on-fail should create file. stdout={result.stdout} stderr={result.stderr}"
    text = target.read_text()
    # --self-test for aws-s3-ops SAFETY_FAIL should append a row
    assert "aws-s3-ops" in text
    # Default SAFETY_FAIL trace has safety=0
    assert "safety" in text


# --- F-23: empty-file presence bug (silent data loss) ---

def test_append_or_increment_recovers_from_empty_existing_file(tmp_path):
    """When failure-patterns.md exists but is empty, append must NOT silently lose data.

    Reproduces: external tooling (touch, git checkout, etc.) leaves a 0-byte
    file. Without this fix, _replace_rows finds no header and writes empty
    content back, losing the new pattern.
    """
    from _reflexion import FailurePattern as FP

    p = tmp_path / "failure-patterns.md"
    p.write_text("")  # exists but empty
    pat = FP(
        skill="aws-ec2-ops",
        command="aws ec2 terminate-instances",
        error="MissingParameter",
        root_cause="no instance ids arg",
        fix="pass --instance-ids",
        timestamp="2026-07-25T00:00:00+00:00",
    )
    result = append_or_increment(p, pat)
    text = p.read_text(encoding="utf-8")
    assert result == "appended"
    # Critical: file MUST now have valid header + 1 data row
    assert text.strip(), "file is empty after append (silent data loss)"
    assert "skill" in text and "command" in text and "count" in text, (
        f"header not restored, got: {text!r}"
    )
    assert "aws ec2 terminate-instances" in text, "data row missing"
    assert p.stat().st_size > 0, "file size still 0"


def test_append_or_increment_recovers_from_corrupted_no_header_file(tmp_path):
    """When failure-patterns.md exists with content but no header row, append rebuilds.

    A file containing only data rows (no `| skill | command | ...` header)
    is treated similarly: `_parse_table_rows` finds 0 rows, dedup loop
    appends a new row, but `_replace_rows` cannot locate the header to
    splice into — so the data row would be silently dropped. Fix should
    detect this case and reseed from scratch.
    """
    from _reflexion import FailurePattern as FP

    p = tmp_path / "failure-patterns.md"
    # Body that LOOKS like a table row but no header above
    p.write_text(
        "| aws-ec2-ops | aws ec2 terminate-instances | MissingParameter | rc | fix | 1 | 2026-07-25T00:00:00+00:00 |\n"
    )
    pat = FP(
        skill="aws-s3-ops",
        command="aws s3 rm",
        error="NoSuchBucket",
        root_cause="x",
        fix="y",
        timestamp="2026-07-25T00:01:00+00:00",
    )
    append_or_increment(p, pat)
    text = p.read_text(encoding="utf-8")
    # New row must be present; fix rebuilds from scratch (replaces file)
    assert "aws s3 rm" in text, "new row missing"
    assert p.stat().st_size > 0, "file should not be empty"



# ---------------------------------------------------------------------------
# derive_from_error tests
# ---------------------------------------------------------------------------



def test_derive_from_error_basic():
    """derive_from_error creates a FailurePattern from keyword args."""
    pat = derive_from_error(
        skill="aws-ec2-ops",
        command="aws ec2 terminate-instances",
        error="MissingParameter",
        root_cause="no instance ids",
        fix="pass --instance-ids",
        source="runtime_safety",
    )
    assert pat.skill == "aws-ec2-ops"
    assert pat.error == "MissingParameter"
    assert pat.root_cause == "no instance ids"
    assert pat.fix == "pass --instance-ids"
    assert "aws-ec2-ops|aws ec2 terminate-instances|MissingParameter" == pat.error_signature
    # timestamp is ISO 8601
    from datetime import datetime
    ts = datetime.fromisoformat(pat.timestamp)
    assert ts.tzinfo is not None


def test_derive_from_error_defaults():
    """derive_from_error fills defaults when root_cause/fix are empty."""
    pat = derive_from_error(
        skill="aws-s3-ops",
        command="aws s3 rm",
        error="AccessDenied",
    )
    assert "external" in pat.root_cause
    assert "Inspect failure-patterns.md" in pat.fix


def test_derive_from_error_appends_to_file(tmp_path):
    """derive_from_error + append_or_increment writes to file."""
    from _reflexion import append_or_increment
    target = tmp_path / "failure-patterns.md"
    pat = derive_from_error(
        skill="aws-test-ops",
        command="aws test delete-thing",
        error="ThrottlingException",
        root_cause="API rate limit exceeded",
        fix="Add retry with backoff",
        source="test",
    )
    result = append_or_increment(target, pat)
    assert result == "appended"
    text = target.read_text()
    assert "aws-test-ops" in text
    assert "ThrottlingException" in text


def test_derive_from_error_dedup_increments(tmp_path):
    """Same error twice → incremented, not appended."""
    from _reflexion import append_or_increment
    target = tmp_path / "failure-patterns.md"
    for _ in range(3):
        pat = derive_from_error(
            skill="aws-test-ops",
            command="aws test",
            error="timeout",
            source="test",
        )
        append_or_increment(target, pat)
    text = target.read_text()
    # Should have count=3
    assert "| 3 |" in text


# ---------------------------------------------------------------------------
# Hypothesis property tests for derive_from_error
# ---------------------------------------------------------------------------



@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    skill=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='-')),
    command=st.text(min_size=1, max_size=80),
    error=st.text(min_size=1, max_size=100),
)
def test_derive_from_error_always_returns_valid_pattern(skill, command, error):
    """Property: derive_from_error always returns a valid FailurePattern."""
    pat = derive_from_error(skill=skill, command=command, error=error)
    assert isinstance(pat, FailurePattern)
    assert pat.skill == skill
    assert pat.command == command
    assert pat.error == error
    assert pat.error_signature == f"{skill}|{command}|{error[:50]}"
    assert pat.timestamp  # non-empty
    # timestamp is parseable ISO 8601
    from datetime import datetime
    ts = datetime.fromisoformat(pat.timestamp)
    assert ts.tzinfo is not None


@settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    skill=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L',), whitelist_characters='-')),
    error=st.text(min_size=1, max_size=200),
)
def test_derive_from_error_signature_deterministic(skill, error):
    """Property: same inputs → same error_signature (deterministic dedup)."""
    p1 = derive_from_error(skill=skill, command="cmd", error=error)
    p2 = derive_from_error(skill=skill, command="cmd", error=error)
    assert p1.error_signature == p2.error_signature


@settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(error=st.text(min_size=51, max_size=200, alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters=' -_.')))
def test_derive_from_error_signature_truncates_error(error):
    """Property: error_signature uses error[:50], not full error."""
    pat = derive_from_error(skill="s", command="c", error=error)
    # error_signature format: "skill|command|error[:50]"
    sig_parts = pat.error_signature.split("|")
    assert len(sig_parts) == 3
    assert len(sig_parts[2]) == 50


# ---------------------------------------------------------------------------
# P0-3: canonical .jsonl write path (writer → real reader round-trip)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(("producer_source", "expected"), [
    ("gcl", "gcl_trace"),
    ("runtime_safety", "runtime_block"),
    ("golden_eval", "governed_learning"),
    ("some-unknown-tool", "runtime_block"),  # never falls back to "manual"
])
def test_append_or_increment_jsonl_translates_source(tmp_path, producer_source, expected):
    """jsonl writes carry a failure_kb.SOURCES value, never "manual"."""
    import failure_kb

    target = tmp_path / "failure-patterns.jsonl"
    pat = derive_from_error(
        skill="aws-test-ops", command="aws test",
        error=f"err-{producer_source}", source=producer_source,
    )
    append_or_increment(target, pat)
    recs = failure_kb.load_jsonl(target)
    assert len(recs) == 1
    assert recs[0].source == expected


def test_derive_from_trace_defaults_to_gcl_source():
    trace = json.loads(SAFETY_FAIL_TRACE.read_text())
    assert derive_from_trace(trace)[0].source == "gcl"
    assert derive_from_trace(trace, source="golden_eval")[0].source == "golden_eval"


def test_gcl_runner_on_fail_round_trips_through_runtime_safety_reader(tmp_path):
    """P0-3 DoD: real writer (gcl_runner --on-fail) → real reader (runtime_safety).

    The fixture IS the writer's own output — no hand-made parser is used for
    the assertions, only runtime_safety.load_failure_patterns (the real
    consumer) and failure_kb.load_jsonl (the loader it delegates to).
    """
    import failure_kb
    from runtime_safety import load_failure_patterns

    target = tmp_path / "failure-patterns.jsonl"
    result = subprocess.run(
        [
            sys.executable, str(SCRIPTS_DIR / "gcl_runner.py"),
            "--skill", "aws-s3-ops",
            "--request", "delete bucket test",  # destructive → safety=0 → SAFETY_FAIL
            "--self-test", "--no-prune", "--on-fail",
            "--failure-patterns", str(target),
        ],
        capture_output=True, text=True, cwd=str(REPO), timeout=60,
    )
    assert target.exists(), f"stdout={result.stdout} stderr={result.stderr}"

    written = failure_kb.load_jsonl(target)
    assert written, "gcl_runner did not persist any record to the canonical jsonl"
    assert all(r.source != "manual" for r in written)
    assert [r.source for r in written] == ["gcl_trace"]

    # Real reader must see exactly what the writer produced.
    rows = load_failure_patterns(target)
    assert len(rows) == len(written)
    assert rows[0]["skill"] == written[0].skill == "aws-s3-ops"
    assert rows[0]["error"] == written[0].error
    assert rows[0]["count"] == str(written[0].count)


# ---------------------------------------------------------------------------
# record-failure CLI tests
# ---------------------------------------------------------------------------

def test_record_failure_cli_dry_run(tmp_path):
    """record-failure --dry-run prints but does not write."""
    from _reflexion import FailurePattern as FP
    target = tmp_path / "failure-patterns.md"
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "_reflexion.py"),
         "record-failure", str(target), "--dry-run",
         "--skill", "aws-test-ops", "--cmd", "aws test delete",
         "--error", "AccessDenied"],
        capture_output=True, text=True, check=False, cwd=str(REPO),
    )
    assert result.returncode == 0
    assert "DRY-RUN" in result.stdout
    assert not target.exists() or target.read_text() == ""


def test_record_failure_cli_real(tmp_path):
    """record-failure writes to file."""
    target = tmp_path / "failure-patterns.md"
    # _reflexion.py CLI: first positional arg is command, second is path
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "_reflexion.py"),
         "record-failure", str(target),
         "--skill", "aws-test-ops", "--cmd", "aws test delete",
         "--error", "ThrottlingException",
         "--root-cause", "rate limit", "--fix", "add backoff",
         "--source", "test"],
        capture_output=True, text=True, check=False, cwd=str(REPO),
    )
    assert result.returncode == 0, f"stderr={result.stderr} stdout={result.stdout}"
    assert target.exists(), f"file not created. stdout={result.stdout} stderr={result.stderr}"
    text = target.read_text()
    assert "aws-test-ops" in text
    assert "ThrottlingException" in text


def test_record_failure_cli_requires_skill_and_error(tmp_path):
    """record-failure without --skill or --error exits with error."""
    target = tmp_path / "failure-patterns.md"
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "_reflexion.py"),
         "record-failure", str(target)],
        capture_output=True, text=True, check=False, cwd=str(REPO),
    )
    assert result.returncode != 0


# ---------------------------------------------------------------------------
# P0-3: CLI default target = canonical .jsonl (C1)
# ---------------------------------------------------------------------------

def test_cli_default_target_is_canonical_jsonl(monkeypatch, tmp_path):
    """record-failure without --path writes the canonical JSONL (C1)."""
    assert _reflexion_module._DEFAULT_PATTERNS_PATH == (
        REPO / "docs" / "failure-patterns.jsonl"
    )
    # Redirect the shipped default to tmp and let the CLI resolve it itself.
    target = tmp_path / "failure-patterns.jsonl"
    monkeypatch.setattr(_reflexion_module, "_DEFAULT_PATTERNS_PATH", target)

    rc = _reflexion_module._cli_main([
        "record-failure",
        "--skill", "aws-default-ops", "--cmd", "aws default rm",
        "--error", "AccessDenied", "--source", "runtime_safety",
    ])
    assert rc == 0
    assert target.exists(), "CLI default did not reach the canonical jsonl"
    recs = failure_kb.load_jsonl(target)
    assert [r.skill for r in recs] == ["aws-default-ops"]
    assert [r.source for r in recs] == ["runtime_block"]


# ---------------------------------------------------------------------------
# P0-3: rendered .md must not silently fork from the .jsonl (C1)
# ---------------------------------------------------------------------------

_MD_TABLE_SEP_RE = re.compile(r"^\|[\s\-|]+\|$")


def _md_data_rows(md_text: str) -> list[str]:
    """Table rows excluding header (line above separator) and separator lines."""
    lines = md_text.splitlines()
    sep_idx = {i for i, ln in enumerate(lines) if _MD_TABLE_SEP_RE.match(ln)}
    header_idx = {i - 1 for i in sep_idx}
    return [
        ln for i, ln in enumerate(lines)
        if ln.startswith("|") and i not in sep_idx and i not in header_idx
    ]


def test_render_failure_warns_without_blocking_persistence(tmp_path, capsys):
    """A failed md re-render must WARN on stderr but still persist the jsonl."""
    # md path is a directory → the real renderer exits non-zero.
    (tmp_path / "failure-patterns.md").mkdir()
    target = tmp_path / "failure-patterns.jsonl"

    result = append_or_increment(
        target,
        derive_from_error(skill="aws-warn-ops", command="aws warn",
                          error="Boom", source="runtime_safety"),
    )
    assert result == "appended", "render failure must not block persistence"
    recs = failure_kb.load_jsonl(target)
    assert [r.skill for r in recs] == ["aws-warn-ops"]
    stderr = capsys.readouterr().err
    assert "WARNING" in stderr and "failure-patterns.md" in stderr


def test_renderer_output_row_count_matches_jsonl(tmp_path):
    """One rendered table row per jsonl record; no unbalanced backticks."""
    canonical = REPO / "docs" / "failure-patterns.jsonl"
    md = tmp_path / "failure-patterns.md"
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "_render_failure_patterns.py"),
         "--jsonl", str(canonical), "--md", str(md)],
        capture_output=True, text=True, check=False, cwd=str(REPO),
    )
    assert result.returncode == 0, f"stderr={result.stderr}"
    records = failure_kb.load_jsonl(canonical)
    assert records, "canonical jsonl unexpectedly empty"
    rows = _md_data_rows(md.read_text(encoding="utf-8"))
    assert len(rows) == len(records), (
        f"md has {len(rows)} rows, jsonl has {len(records)} records — silent fork"
    )
    assert all(ln.count("`") % 2 == 0 for ln in rows), "unbalanced backticks in md"


def test_committed_md_equals_fresh_render_of_canonical_jsonl(tmp_path):
    """docs/failure-patterns.md must equal a fresh render of the jsonl (C1).

    Byte-equality is the fork guard: any hand-edit of the md, or a jsonl write
    that skipped re-rendering, makes this fail.
    """
    canonical = REPO / "docs" / "failure-patterns.jsonl"
    committed_md = REPO / "docs" / "failure-patterns.md"
    fresh_md = tmp_path / "failure-patterns.md"
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "_render_failure_patterns.py"),
         "--jsonl", str(canonical), "--md", str(fresh_md)],
        capture_output=True, text=True, check=False, cwd=str(REPO),
    )
    assert result.returncode == 0, f"stderr={result.stderr}"

    committed = committed_md.read_text(encoding="utf-8")
    assert "docs/failure-patterns.jsonl" in committed, "md must declare canonical store"
    assert committed == fresh_md.read_text(encoding="utf-8"), (
        "committed md drifted from canonical jsonl — re-run "
        "scripts/_render_failure_patterns.py"
    )

# --- O3: check-reflexion-freshness CLI ---

def _write_patterns_jsonl(path: Path, last_seen_dates):
    rows = [
        json.dumps({
            "skill": f"svc{i}", "command": "cmd", "error": "err",
            "root_cause": "rc", "fix": "fx", "timestamp": "2026-01-01T00:00:00Z",
            "count": 1, "last_seen": d, "error_signature": f"svc{i}|cmd|err",
            "source": "gcl_trace",
        })
        for i, d in enumerate(last_seen_dates)
    ]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def test_check_reflexion_freshness_stale(tmp_path):
    """Newest last_seen older than --days → exit 1 + stderr 'stale'."""
    p = tmp_path / "failure-patterns.jsonl"
    _write_patterns_jsonl(p, ["2026-09-14"])  # 10 days before as-of
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "self_review.py"),
         "check-reflexion-freshness", "--patterns", str(p),
         "--days", "7", "--as-of", "2026-09-24"],
        capture_output=True, text=True, check=False, cwd=str(REPO),
    )
    assert result.returncode == 1, f"stderr={result.stderr}"
    assert "stale" in result.stderr


def test_check_reflexion_freshness_fresh(tmp_path):
    """Newest last_seen within --days → exit 0."""
    p = tmp_path / "failure-patterns.jsonl"
    _write_patterns_jsonl(p, ["2026-09-22"])  # 2 days before as-of
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "self_review.py"),
         "check-reflexion-freshness", "--patterns", str(p),
         "--days", "7", "--as-of", "2026-09-24"],
        capture_output=True, text=True, check=False, cwd=str(REPO),
    )
    assert result.returncode == 0, f"stderr={result.stderr}"
    assert "fresh" in result.stdout


def test_check_reflexion_freshness_missing_file(tmp_path):
    """Missing JSONL → exit 1 + stderr 'missing'."""
    p = tmp_path / "absent.jsonl"
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "self_review.py"),
         "check-reflexion-freshness", "--patterns", str(p),
         "--days", "7", "--as-of", "2026-09-24"],
        capture_output=True, text=True, check=False, cwd=str(REPO),
    )
    assert result.returncode == 1
    assert "missing" in result.stderr

def test_check_reflexion_freshness_malformed_jsonl(tmp_path):
    """Corrupt line in JSONL → exit 1 + clean stderr (no traceback), R2 fix."""
    p = tmp_path / "failure-patterns.jsonl"
    p.write_text('{"skill": "svc", "last_seen": "2026-09-22"}\nNOT-JSON\n',
                 encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "self_review.py"),
         "check-reflexion-freshness", "--patterns", str(p),
         "--days", "7", "--as-of", "2026-09-24"],
        capture_output=True, text=True, check=False, cwd=str(REPO),
    )
    assert result.returncode == 1
    assert "malformed JSONL" in result.stderr
    assert "Traceback" not in result.stderr, "must fail closed with clean message"
