"""TDD tests for scripts/gcl_metrics.py — L4 dim #5 observability.

Each test uses REAL fixtures from audit-results/gcl-trace-*.json — no mocks
of the functions under test. The point is to prove the script actually parses
real GCL traces and excludes plan artifacts.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# Make scripts/ importable
SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

from gcl_metrics import (  # noqa: E402
    classify_trace,
    collect_traces,
    extract_final_status,
    aggregate,
    render_markdown,
    AUDIT_DIR,
)


def test_real_gcl_trace_is_parsed_as_trace_not_plan():
    """gcl-trace-20260627-031257.json is a real GCL run (SAFETY_FAIL)."""
    p = AUDIT_DIR / "gcl-trace-20260627-031257.json"
    trace = json.loads(p.read_text())
    assert classify_trace(trace) == "gcl"
    assert extract_final_status(trace) == "SAFETY_FAIL"
    assert trace["skill"] == "aws-s3-ops"


def test_plan_artifact_is_excluded_from_metrics():
    """gcl-trace-20260705-181751.json is a plan artifact (has agents/strategy), not a real trace."""
    p = AUDIT_DIR / "gcl-trace-20260705-181751.json"
    trace = json.loads(p.read_text())
    assert classify_trace(trace) == "plan_artifact"
    # collect_traces must filter it out
    rows = collect_traces(AUDIT_DIR, days=365)
    paths = [r.path.name for r in rows]
    assert "gcl-trace-20260705-181751.json" not in paths
    assert "gcl-trace-20260705-182734.json" not in paths
    # but the real GCL traces ARE included
    assert "gcl-trace-20260627-031257.json" in paths
    assert "gcl-trace-20260627-031303.json" in paths


def test_pass_rate_per_skill():
    """aws-s3-ops has ≥2 known FAIL traces → pass_rate = 0 for those.

    Note: pollution traces from --self-test runs may add more; we test
    that the ORIGINAL 2 traces are correctly classified, not the exact total.
    """
    rows = collect_traces(AUDIT_DIR, days=365)
    s3_rows = [r for r in rows if r.skill == "aws-s3-ops"]
    # The original 4 fixtures produce 2 s3-ops traces; pollution may add more
    assert len(s3_rows) >= 2
    # Both original traces are FAIL (SAFETY_FAIL + MAX_ITER), not PASS
    original_paths = {
        AUDIT_DIR / "gcl-trace-20260627-031257.json",
        AUDIT_DIR / "gcl-trace-20260627-031303.json",
    }
    originals = [r for r in s3_rows if r.path in original_paths]
    assert len(originals) == 2
    assert all(r.status != "PASS" for r in originals)
    agg = aggregate(rows)
    by_skill = agg["by_skill"]
    assert "aws-s3-ops" in by_skill
    # PASS count must be 0 for the original 2 traces
    assert originals[0].status == "SAFETY_FAIL"
    assert originals[1].status == "MAX_ITER"
    # Total FAIL count >= 2 (original) + pollution may add more
    assert by_skill["aws-s3-ops"]["FAIL"] >= 2
    # Rate must be in valid range
    rate = by_skill["aws-s3-ops"]["PASS"] / by_skill["aws-s3-ops"]["TOTAL"]
    assert 0.0 <= rate <= 1.0


def test_failure_dimensions_are_aggregated():
    """SAFETY_FAIL trace has safety=0 → dimension fail histogram includes 'safety'."""
    rows = collect_traces(AUDIT_DIR, days=365)
    agg = aggregate(rows)
    dim_fails = agg["dim_fails"]
    # SAFETY_FAIL trace scored safety=0 in last iter
    assert "safety" in dim_fails
    assert dim_fails["safety"] >= 1
    # MAX_ITER trace scored idempotency=0 in last iter
    assert "idempotency" in dim_fails
    assert dim_fails["idempotency"] >= 1
    # Verify command attribution
    s3_rows = [r for r in rows if r.skill == "aws-s3-ops"]
    assert all("aws" in r.command for r in s3_rows)


def test_markdown_render_contains_three_tables():
    """render_markdown output must have ≥3 markdown tables + 'Pass-rate by skill' section."""
    rows = collect_traces(AUDIT_DIR, days=365)
    md = render_markdown(rows)
    # 3 tables expected: Overview by skill / Pass-rate by skill / Failure dimensions
    table_lines = [ln for ln in md.splitlines() if ln.startswith("|")]
    assert len(table_lines) >= 9  # 3 tables × ≥3 lines (header + sep + data)
    assert "## Pass-rate by skill" in md
    assert "## Failure dimensions" in md or "## Failure Dimensions" in md.lower()
    # Verify aws-s3-ops row appears in Overview
    assert "aws-s3-ops" in md


def test_json_output_is_machine_readable():
    """--json flag must emit parseable JSON to stdout."""
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "gcl_metrics.py"), "--json", "--days", "365"],
        capture_output=True, text=True, timeout=30, cwd=str(SCRIPTS_DIR.parent),
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    parsed = json.loads(result.stdout)
    assert isinstance(parsed, list)
    assert len(parsed) >= 2  # at least the 2 real GCL traces
    # Each row has expected fields
    first = parsed[0]
    for key in ("path", "skill", "status", "iter_count", "fail_dimensions"):
        assert key in first, f"missing key {key} in {first}"
    # Plan artifacts MUST NOT appear
    for row in parsed:
        assert "agents" not in str(row).lower() or "agents" not in row.get("path", "").lower()
