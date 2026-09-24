"""TDD tests for scripts/gcl_metrics.py — L4 dim #5 observability.

Uses committed fixtures under scripts/tests/fixtures/gcl-traces/
(audit-results/ is gitignored and absent on CI).
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

from gcl_metrics import (  # noqa: E402
    classify_trace,
    collect_traces,
    extract_final_status,
    aggregate,
    render_markdown,
    append_timeseries,
    read_timeseries,
    parse_timeseries_day,
    staleness_check,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "gcl-traces"
EXPECTED_SCHEMA = ["timestamp", "window_days", "skill", "total", "pass", "fail", "pass_rate"]


def _data_rows(path: Path) -> list[dict[str, str]]:
    """Read the CSV the way a real consumer would (no re-implemented parsing)."""
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    with path.open(encoding="utf-8") as fh:
        assert fh.readline().strip() == ",".join(EXPECTED_SCHEMA)
    return rows


def test_real_gcl_trace_is_parsed_as_trace_not_plan():
    """gcl-trace-20260627-031257.json is a real GCL run (SAFETY_FAIL)."""
    p = FIXTURES / "gcl-trace-20260627-031257.json"
    trace = json.loads(p.read_text())
    assert classify_trace(trace) == "gcl"
    assert extract_final_status(trace) == "SAFETY_FAIL"
    assert trace["skill"] == "aws-s3-ops"


def test_plan_artifact_is_excluded_from_metrics():
    """Plan artifacts (strategy/agents) must be filtered out of collect_traces."""
    p = FIXTURES / "gcl-trace-20260705-181751.json"
    trace = json.loads(p.read_text())
    assert classify_trace(trace) == "plan_artifact"
    rows = collect_traces(FIXTURES, days=365, include_self_test=True)
    paths = [r.path.name for r in rows]
    assert "gcl-trace-20260705-181751.json" not in paths
    assert "gcl-trace-20260705-182734.json" not in paths
    assert "gcl-trace-20260627-031257.json" in paths
    assert "gcl-trace-20260627-031303.json" in paths


def test_pass_rate_per_skill():
    """aws-s3-ops has ≥2 known FAIL fixtures → classified correctly."""
    rows = collect_traces(FIXTURES, days=365, include_self_test=True)
    s3_rows = [r for r in rows if r.skill == "aws-s3-ops"]
    assert len(s3_rows) >= 2
    original_paths = {
        FIXTURES / "gcl-trace-20260627-031257.json",
        FIXTURES / "gcl-trace-20260627-031303.json",
    }
    originals = [r for r in s3_rows if r.path in original_paths]
    assert len(originals) == 2
    assert all(r.status != "PASS" for r in originals)
    agg = aggregate(rows)
    by_skill = agg["by_skill"]
    assert "aws-s3-ops" in by_skill
    assert originals[0].status == "SAFETY_FAIL"
    assert originals[1].status == "MAX_ITER"
    assert by_skill["aws-s3-ops"]["FAIL"] >= 2
    # fixtures hold exactly 2 FAIL / 0 PASS for aws-s3-ops, so the rate is 0.0
    assert by_skill["aws-s3-ops"] == {"PASS": 0, "FAIL": 2, "TOTAL": 2}
    rate = by_skill["aws-s3-ops"]["PASS"] / by_skill["aws-s3-ops"]["TOTAL"]
    assert rate == 0.0


def test_failure_dimensions_are_aggregated():
    """SAFETY_FAIL → safety dim; MAX_ITER → idempotency dim."""
    rows = collect_traces(FIXTURES, days=365, include_self_test=True)
    agg = aggregate(rows)
    dim_fails = agg["dim_fails"]
    assert "safety" in dim_fails
    assert dim_fails["safety"] >= 1
    assert "idempotency" in dim_fails
    assert dim_fails["idempotency"] >= 1
    s3_rows = [r for r in rows if r.skill == "aws-s3-ops"]
    assert all("aws" in r.command for r in s3_rows)


def test_markdown_render_contains_three_tables():
    """render_markdown output must have ≥3 markdown tables + Pass-rate section."""
    rows = collect_traces(FIXTURES, days=365, include_self_test=True)
    md = render_markdown(rows)
    table_lines = [ln for ln in md.splitlines() if ln.startswith("|")]
    assert len(table_lines) >= 9
    assert "## Pass-rate by skill" in md
    assert "## Failure dimensions histogram" in md
    assert "aws-s3-ops" in md


def test_json_output_is_machine_readable():
    """--json flag must emit parseable JSON to stdout (fixture audit-dir)."""
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "gcl_metrics.py"),
            "--json",
            "--days",
            "365",
            "--audit-dir",
            str(FIXTURES),
            "--include-self-test",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(SCRIPTS_DIR.parent),
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    parsed = json.loads(result.stdout)
    assert isinstance(parsed, list)
    assert len(parsed) >= 2
    first = parsed[0]
    for key in ("path", "skill", "status", "iter_count", "fail_dimensions"):
        assert key in first, f"missing key {key} in {first}"


# --- P0-4: self-test stub filtering (spec §4 P0-4 + C6/C7/C8) ---


def test_stub_trace_filtered_by_default():
    """Real trace appears; stub trace is excluded when include_self_test=False."""
    from gcl_metrics import collect_traces

    rows = collect_traces(FIXTURES, days=365)  # default: include_self_test=False
    paths = {r.path.name for r in rows}
    assert "gcl-trace-20260924-real.json" in paths, "real trace must remain"
    assert "gcl-trace-20260924-stub.json" not in paths, "stub trace must be hidden by default"


def test_include_self_test_flag_includes_stub():
    """When include_self_test=True, both real and stub appear."""
    from gcl_metrics import collect_traces

    rows = collect_traces(FIXTURES, days=365, include_self_test=True)
    paths = {r.path.name for r in rows}
    assert "gcl-trace-20260924-real.json" in paths
    assert "gcl-trace-20260924-stub.json" in paths


def test_aggregate_excludes_stub_skill_when_filtered():
    """By default, no stub trace (SAFETY_FAIL) leaks into aggregate output."""
    from gcl_metrics import collect_traces

    rows = collect_traces(FIXTURES, days=365)  # default excludes stubs
    leaked = [r for r in rows if r.status == "SAFETY_FAIL"]
    assert leaked == [], f"stub trace(s) leaked into default aggregate: {[r.path.name for r in leaked]}"


def test_cli_flag_surfaces_in_help():
    """--include-self-test flag must be visible via --help (audit discoverability)."""
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "gcl_metrics.py"), "--help"],
        capture_output=True, text=True, timeout=10,
    )
    assert "--include-self-test" in result.stdout


def test_markdown_documents_stub_filter_behavior():
    """render_markdown header must call out stub-filter behavior (audit hygiene)."""
    from gcl_metrics import render_markdown

    rows = []  # empty is fine; we only care about the header
    md = render_markdown(rows)
    assert "real" in md.lower() or "stub" in md.lower()
    assert "--include-self-test" in md


def test_append_timeseries_creates_header_and_real_rows(tmp_path):
    """Missing file → created with schema header + one row per skilled trace."""
    csv_path = tmp_path / "metrics" / "timeseries.csv"
    rows = [r for r in collect_traces(FIXTURES, days=365, include_self_test=True) if r.skill == "aws-s3-ops"]
    written = append_timeseries(csv_path, rows, window_days=365, day="2026-09-24")

    assert written == 1
    data = _data_rows(csv_path)
    assert len(data) == 1
    row = data[0]
    assert row["timestamp"] == "2026-09-24"
    assert row["window_days"] == "365"
    assert row["skill"] == "aws-s3-ops"
    # fixtures hold 2 FAIL / 0 PASS for aws-s3-ops
    assert (row["total"], row["pass"], row["fail"]) == ("2", "0", "2")
    assert float(row["pass_rate"]) == 0.0


def test_append_timeseries_is_idempotent_for_same_day(tmp_path):
    """Second run on the same UTC day overwrites instead of appending."""
    csv_path = tmp_path / "timeseries.csv"
    rows = [r for r in collect_traces(FIXTURES, days=365, include_self_test=True) if r.skill == "aws-s3-ops"]
    append_timeseries(csv_path, rows, window_days=365, day="2026-09-24")
    first = csv_path.read_text(encoding="utf-8")
    append_timeseries(csv_path, rows, window_days=365, day="2026-09-24")

    assert csv_path.read_text(encoding="utf-8") == first
    assert len(_data_rows(csv_path)) == 1


def test_append_timeseries_keeps_rows_from_other_days(tmp_path):
    """A new UTC day appends a new row; older rows survive."""
    csv_path = tmp_path / "timeseries.csv"
    rows = [r for r in collect_traces(FIXTURES, days=365, include_self_test=True) if r.skill == "aws-s3-ops"]
    append_timeseries(csv_path, rows, window_days=365, day="2026-09-24")
    append_timeseries(csv_path, rows, window_days=365, day="2026-09-25")

    data = _data_rows(csv_path)
    assert [r["timestamp"] for r in data] == ["2026-09-24", "2026-09-25"]
    assert {r["skill"] for r in data} == {"aws-s3-ops"}


def test_append_timeseries_without_traces_writes_header_only(tmp_path):
    """Empty window (no audit dir) still yields a schema-valid CSV."""
    csv_path = tmp_path / "timeseries.csv"
    written = append_timeseries(csv_path, collect_traces(tmp_path / "missing", days=365),
                               window_days=365, day="2026-09-24")

    assert written == 0
    assert _data_rows(csv_path) == []


def test_repo_durable_timeseries_is_schema_valid():
    """docs/metrics/timeseries.csv is committed, BOM-free and schema-valid.

    A BOM would rename the first DictReader field to '\\ufefftimestamp' and make
    read_timeseries silently discard every stored row. The committed copy ships
    header-only, but a local `make metrics` legitimately adds data rows, so this
    asserts the header + per-row schema rather than emptiness.
    """
    durable = SCRIPTS_DIR.parent / "docs" / "metrics" / "timeseries.csv"
    assert durable.exists(), f"{durable} must be committed (it is the durable store)"
    assert durable.read_text(encoding="utf-8").splitlines()[0] == ",".join(EXPECTED_SCHEMA)
    for row in read_timeseries(durable):
        assert all(row.get(k) for k in EXPECTED_SCHEMA), f"empty cell in {row}"
        assert parse_timeseries_day(row["timestamp"]) is not None, f"bad date in {row}"
        assert int(row["total"]) == int(row["pass"]) + int(row["fail"])
        assert 0.0 <= float(row["pass_rate"]) <= 1.0


def test_dirty_timeseries_row_does_not_break_staleness(tmp_path):
    """One unparseable timestamp is skipped, not fatal to the whole command."""
    csv_path = tmp_path / "timeseries.csv"
    csv_path.write_text(
        ",".join(EXPECTED_SCHEMA) + "\n"
        "not-a-date,365,aws-s3-ops,2,0,2,0.0000\n"
        "2026-09-23,365,aws-s3-ops,2,0,2,0.0000\n",
        encoding="utf-8",
    )

    ok, msg = staleness_check(csv_path, 7, today=date(2026, 9, 24))
    assert ok is True and "2026-09-23" in msg


def test_staleness_check_missing_and_fresh_and_stale(tmp_path):
    """no data → False; recent entry → True; older than max-age → False."""
    missing = tmp_path / "absent.csv"
    assert staleness_check(missing, 7, today=date(2026, 9, 24)) == (
        False, f"metrics stale: no data rows in {missing}")

    csv_path = tmp_path / "timeseries.csv"
    rows = collect_traces(FIXTURES, days=365, include_self_test=True)
    append_timeseries(csv_path, rows, window_days=365, day="2026-09-23")
    ok, msg = staleness_check(csv_path, 7, today=date(2026, 9, 24))
    assert ok is True and "2026-09-23" in msg
    ok, msg = staleness_check(csv_path, 7, today=date(2026, 10, 24))
    assert ok is False and "31d old" in msg


def test_cli_staleness_check_exit_code(tmp_path):
    """`--staleness-check` exits 1 on empty timeseries, 0 once a row exists."""
    csv_path = tmp_path / "timeseries.csv"

    def _cli(*extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "gcl_metrics.py"),
             "--staleness-check", "--max-age-days", "7", *extra],
            capture_output=True, text=True, timeout=30, cwd=str(SCRIPTS_DIR.parent),
        )

    empty = _cli("--timeseries", str(csv_path))
    assert empty.returncode == 1, f"stdout={empty.stdout} stderr={empty.stderr}"
    assert "no data rows" in empty.stdout

    subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "gcl_metrics.py"),
         "--days", "365", "--audit-dir", str(FIXTURES), "--timeseries", str(csv_path)],
        capture_output=True, text=True, timeout=30, cwd=str(SCRIPTS_DIR.parent),
        check=True,
    )
    fresh = _cli("--timeseries", str(csv_path))
    assert fresh.returncode == 0, f"stdout={fresh.stdout} stderr={fresh.stderr}"
    assert "metrics fresh" in fresh.stdout
