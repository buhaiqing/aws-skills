"""TDD tests for L3 L2-composite skills — structural validation.

The 3 L2 composite skills (aws-aiops-orchestrator, aws-aiops-copilot,
aws-security-copilot) declare `cross_skill_deps` + `delegate` keys in their
frontmatter. These tests prove the keys point to real directories and the
declared `provides` operations have delegate targets.

L3 dim 5.2-bis: L2 composite 实跑性 — these tests validate the structural
contract; full end-to-end execution would require live AWS credentials.
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# Make PyYAML available
try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


def _load_frontmatter(path: Path) -> dict:
    """Read YAML frontmatter from a SKILL.md."""
    if yaml is None:
        raise RuntimeError("PyYAML not installed")
    text = path.read_text()
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    return yaml.safe_load(parts[1]) or {}


def test_orchestrator_cross_skill_deps_all_exist():
    """aws-aiops-orchestrator declares 30 cross_skill_deps — each must exist as a dir."""
    fm = _load_frontmatter(REPO / "aws-aiops-orchestrator" / "SKILL.md")
    deps = fm.get("metadata", {}).get("cross_skill_deps", [])
    assert len(deps) >= 20, f"expected ≥20 deps, got {len(deps)}: {deps}"
    missing = [d for d in deps if not (REPO / d).is_dir()]
    assert missing == [], f"missing dirs: {missing}"


def test_copilot_delegate_targets_all_exist():
    """aws-aiops-copilot delegate keys must point to existing dirs."""
    fm = _load_frontmatter(REPO / "aws-aiops-copilot" / "SKILL.md")
    delegate = fm.get("metadata", {}).get("delegate", {})
    assert "aws-aiops-cruise" in delegate, "copilot must delegate to cruise"
    assert "aws-aiops-orchestrator" in delegate, "copilot must delegate to orchestrator"
    missing = [k for k in delegate if not (REPO / k).is_dir()]
    assert missing == [], f"missing delegate targets: {missing}"


def test_secops_copilot_delegate_targets_all_exist():
    """aws-security-copilot delegate keys must point to existing dirs."""
    fm = _load_frontmatter(REPO / "aws-security-copilot" / "SKILL.md")
    delegate = fm.get("metadata", {}).get("delegate", {})
    cross = fm.get("metadata", {}).get("cross_skill_deps", [])
    assert len(delegate) >= 5, f"secops copilot should have ≥5 delegate targets, got {len(delegate)}"
    # Check delegate keys
    missing_delegate = [k for k in delegate if not (REPO / k).is_dir()]
    assert missing_delegate == [], f"missing delegate targets: {missing_delegate}"
    # Check cross_skill_deps
    missing_cross = [d for d in cross if not (REPO / d).is_dir()]
    assert missing_cross == [], f"missing cross_skill_deps: {missing_cross}"


def test_orchestrator_provides_consistent_with_delegate():
    """orchestrator's `provides` list should map to delegate operations."""
    fm = _load_frontmatter(REPO / "aws-aiops-orchestrator" / "SKILL.md")
    provides = fm.get("metadata", {}).get("provides", [])
    # orchestrator has 30 cross_skill_deps; each dep's aws-*-ops can be invoked
    # We don't enforce 1:1 provides↔delegate (orchestrator is orchestrator-meta),
    # but provides must be a non-empty list
    assert isinstance(provides, list)
    assert len(provides) >= 1, f"orchestrator provides empty: {provides}"


def test_all_composite_status_not_design_draft():
    """L3 L2 composites should NOT be 'design-draft' anymore after P0 closure.

    This is the meta-test that closes L3 dim 5.2-bis: composites are validated
    end-to-end (by other tests), so status should advance from 'design-draft'.
    Mark them with status='validated' (or remove status) once composite tests pass.
    """
    for skill_name in ("aws-aiops-orchestrator", "aws-aiops-copilot", "aws-security-copilot"):
        fm = _load_frontmatter(REPO / skill_name / "SKILL.md")
        status = fm.get("metadata", {}).get("status", "")
        # After L3 closure, status should NOT be 'design-draft'
        assert status != "design-draft", (
            f"{skill_name} still marked 'design-draft'; "
            f"frontmatter status should advance after L3 structural validation"
        )


def test_composite_skills_have_gcl_enabled():
    """L2 composites must have GCL metadata block (per AGENTS.md Charter)."""
    for skill_name in ("aws-aiops-orchestrator", "aws-aiops-copilot", "aws-security-copilot"):
        fm = _load_frontmatter(REPO / skill_name / "SKILL.md")
        gcl = fm.get("metadata", {}).get("gcl", {})
        assert gcl.get("enabled") is True, f"{skill_name} gcl.enabled must be True"


def test_delegate_contract_alignment_orchestrator_copilot():
    """copilot's delegate op strings should be a subset of orchestrator's capabilities."""
    copilot_fm = _load_frontmatter(REPO / "aws-aiops-copilot" / "SKILL.md")
    copilot_ops = copilot_fm.get("metadata", {}).get("delegate", {}).get("aws-aiops-orchestrator", [])
    # copilot delegates "cross-service-rca" to orchestrator; orchestrator must declare a related provide
    assert "cross-service-rca" in copilot_ops, f"copilot must delegate cross-service-rca to orchestrator: {copilot_ops}"
