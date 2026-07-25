"""Tests for scripts/finops_gap_audit.py (F-7 Gap Exposure)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Ensure scripts/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from finops_gap_audit import (
    audit_d1_capability,
    audit_d2_routing,
    audit_d3_automation,
    audit_d4_tests,
    audit_d5_inference,
    format_json,
    format_markdown,
    run_audit,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_root(tmp_path: Path) -> Path:
    """Create a minimal fake project root for testing."""
    # aws-finops-core/SKILL.md with provides
    finops_dir = tmp_path / "aws-finops-core"
    finops_dir.mkdir()
    (finops_dir / "SKILL.md").write_text(
        "---\n"
        "name: aws-finops-core\n"
        "metadata:\n"
        "  provides:\n"
        "    - cost-anomaly-detection\n"
        "    - idle-resource-discovery\n"
        "    - tag-compliance-reporting\n"
        "---\n"
        "## Trigger\n",
        encoding="utf-8",
    )
    # references
    ref_dir = finops_dir / "references"
    ref_dir.mkdir()
    (ref_dir / "anomaly-detection.md").write_text("# anomaly\n")
    (ref_dir / "idle-detection-rules.md").write_text("# idle\n")
    (ref_dir / "tag-compliance.md").write_text("# tags\n")

    # AIOps routing files
    for name in ["aws-aiops-orchestrator", "aws-aiops-cruise", "aws-aiops-copilot"]:
        d = tmp_path / name
        d.mkdir()
        (d / "SKILL.md").write_text("---\nname: x\n---\n# no routing here\n")

    # scripts/
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "finops_gap_audit.py").write_text("# self\n")

    # scripts/tests/
    tests_dir = scripts_dir / "tests"
    tests_dir.mkdir()

    # _inference.py
    cruise_scripts = tmp_path / "aws-aiops-cruise" / "runbooks" / "scripts"
    cruise_scripts.mkdir(parents=True)
    (cruise_scripts / "_inference.py").write_text(
        'def apply():\n    rule = "EC2-CPU-01"\n'
    )

    return tmp_path


# ---------------------------------------------------------------------------
# D1: Capability coverage
# ---------------------------------------------------------------------------

class TestD1Capability:
    def test_all_covered(self, fake_root: Path):
        result = audit_d1_capability(fake_root)
        assert result["score"] == 1.0
        assert result["gaps"] == []
        assert result["covered"] == 3

    def test_missing_reference(self, fake_root: Path):
        # Remove a reference file
        (fake_root / "aws-finops-core" / "references" / "tag-compliance.md").unlink()
        result = audit_d1_capability(fake_root)
        assert result["score"] < 1.0
        assert any("tag-compliance" in g for g in result["gaps"])

    def test_no_skill_md(self, tmp_path: Path):
        (tmp_path / "aws-finops-core").mkdir()
        result = audit_d1_capability(tmp_path)
        assert result["score"] == 0.0


# ---------------------------------------------------------------------------
# D2: Routing coverage
# ---------------------------------------------------------------------------

class TestD2Routing:
    def test_no_routing(self, fake_root: Path):
        result = audit_d2_routing(fake_root)
        assert result["score"] == 0.0
        assert len(result["gaps"]) == 3

    def test_partial_routing(self, fake_root: Path):
        # Add finops reference to orchestrator
        orch = fake_root / "aws-aiops-orchestrator" / "SKILL.md"
        orch.write_text("---\nname: x\n---\ndelegate: aws-finops-core\n")
        result = audit_d2_routing(fake_root)
        assert result["score"] == pytest.approx(1 / 3, abs=0.01)
        assert len(result["gaps"]) == 2


# ---------------------------------------------------------------------------
# D3: Automation coverage
# ---------------------------------------------------------------------------

class TestD3Automation:
    def test_only_self(self, fake_root: Path):
        result = audit_d3_automation(fake_root)
        # Only finops_gap_audit.py exists out of 6 expected
        assert result["covered"] == 1
        assert result["total"] == 6
        assert result["score"] == pytest.approx(1 / 6, abs=0.01)

    def test_all_scripts_present(self, fake_root: Path):
        scripts_dir = fake_root / "scripts"
        for name in [
            "finops_anomaly_detect.py",
            "finops_budget_setup.py",
            "finops_idle_scan.py",
            "finops_ri_sp_analysis.py",
            "finops_tag_audit.py",
        ]:
            (scripts_dir / name).write_text("# stub\n")
        result = audit_d3_automation(fake_root)
        assert result["score"] == 1.0
        assert result["gaps"] == []


# ---------------------------------------------------------------------------
# D4: Test coverage
# ---------------------------------------------------------------------------

class TestD4Tests:
    def test_no_tests(self, fake_root: Path):
        result = audit_d4_tests(fake_root)
        assert result["score"] == 0.0
        assert any("test_finops_gap_audit" in g for g in result["gaps"])

    def test_with_test(self, fake_root: Path):
        tests_dir = fake_root / "scripts" / "tests"
        (tests_dir / "test_finops_gap_audit.py").write_text("# test\n")
        result = audit_d4_tests(fake_root)
        assert result["score"] == 1.0


# ---------------------------------------------------------------------------
# D5: Inference coverage
# ---------------------------------------------------------------------------

class TestD5Inference:
    def test_no_cost_rules(self, fake_root: Path):
        result = audit_d5_inference(fake_root)
        assert result["score"] == 0.0
        assert any("COST" in g for g in result["gaps"])

    def test_with_cost_rules(self, fake_root: Path):
        inf = fake_root / "aws-aiops-cruise" / "runbooks" / "scripts" / "_inference.py"
        inf.write_text(
            'def apply():\n'
            '    rule = "COST-SPIKE-01"\n'
            '    rule = "COST-IDLE-01"\n'
        )
        result = audit_d5_inference(fake_root)
        assert result["covered"] == 2


# ---------------------------------------------------------------------------
# Output formats
# ---------------------------------------------------------------------------

class TestOutputFormats:
    def test_json_valid(self, fake_root: Path):
        report = run_audit(fake_root)
        output = format_json(report)
        parsed = json.loads(output)
        assert "dimensions" in parsed
        assert "overall_score" in parsed
        assert parsed["verdict"] in ("PASS", "FAIL")

    def test_markdown_structure(self, fake_root: Path):
        report = run_audit(fake_root)
        output = format_markdown(report)
        assert "# FinOps Gap Exposure Report" in output
        assert "| Dimension |" in output
        assert "D1_capability_coverage" in output


# ---------------------------------------------------------------------------
# Integration: run_audit
# ---------------------------------------------------------------------------

class TestRunAudit:
    def test_overall_score(self, fake_root: Path):
        report = run_audit(fake_root)
        assert 0.0 <= report["overall_score"] <= 1.0
        assert report["verdict"] == "FAIL"  # gaps exist

    def test_all_dimensions_present(self, fake_root: Path):
        report = run_audit(fake_root)
        expected_keys = {
            "D1_capability_coverage",
            "D2_routing_coverage",
            "D3_automation_coverage",
            "D4_test_coverage",
            "D5_inference_coverage",
        }
        assert set(report["dimensions"].keys()) == expected_keys
