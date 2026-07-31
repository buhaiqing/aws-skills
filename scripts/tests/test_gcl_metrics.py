"""TDD tests for scripts/gcl_metrics.py — L4 dim #5 observability.

Uses committed fixtures under scripts/tests/fixtures/gcl-traces/
(audit-results/ is gitignored and absent on CI).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

from gcl_metrics import (  # noqa: E402
    classify_trace,
    collect_traces,
    extract_final_status,
    aggregate,
    render_markdown,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "gcl-traces"


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
    rows = collect_traces(FIXTURES, days=365)
    paths = [r.path.name for r in rows]
    assert "gcl-trace-20260705-181751.json" not in paths
    assert "gcl-trace-20260705-182734.json" not in paths
    assert "gcl-trace-20260627-031257.json" in paths
    assert "gcl-trace-20260627-031303.json" in paths


def test_pass_rate_per_skill():
    """aws-s3-ops has ≥2 known FAIL fixtures → classified correctly."""
    rows = collect_traces(FIXTURES, days=365)
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
    rate = by_skill["aws-s3-ops"]["PASS"] / by_skill["aws-s3-ops"]["TOTAL"]
    assert 0.0 <= rate <= 1.0


def test_failure_dimensions_are_aggregated():
    """SAFETY_FAIL → safety dim; MAX_ITER → idempotency dim."""
    rows = collect_traces(FIXTURES, days=365)
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
    rows = collect_traces(FIXTURES, days=365)
    md = render_markdown(rows)
    table_lines = [ln for ln in md.splitlines() if ln.startswith("|")]
    assert len(table_lines) >= 9
    assert "## Pass-rate by skill" in md
    assert "## Failure dimensions" in md or "## Failure Dimensions" in md.lower()
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
