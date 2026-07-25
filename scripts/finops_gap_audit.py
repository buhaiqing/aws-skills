#!/usr/bin/env python3
"""FinOps Gap Exposure Audit (F-7).

Diagnoses the real gap between documented FinOps capabilities and actual
implementation across 5 dimensions:

  D1: Capability coverage  — SKILL.md `provides` vs references/ files
  D2: Routing coverage     — AIOps orchestrator/cruise route to finops-core
  D3: Automation coverage  — scripts/finops_*.py existence
  D4: Test coverage        — tests for FinOps scripts
  D5: Inference coverage   — COST-* rules in _inference.py

Usage:
    python3 scripts/finops_gap_audit.py [--format json|md] [--verbose]

Exit codes:
    0 — all dimensions fully covered (no gaps)
    1 — gaps detected in one or more dimensions
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Mapping: provides capability → expected reference file (stem)
_CAPABILITY_REF_MAP: dict[str, str] = {
    "cost-anomaly-detection": "anomaly-detection",
    "idle-resource-discovery": "idle-detection-rules",
    "tag-compliance-reporting": "tag-compliance",
    "ri-sp-coverage-analysis": "reserved-coverage",
    "ecs-idle-service-discovery": "idle-detection-rules",
    "ecs-fargate-rightsizing": "idle-detection-rules",
    "ecs-fargate-spot-optimization": "idle-detection-rules",
    "app-autoscaling-ecs-targets": "idle-detection-rules",
    "app-autoscaling-policies": "idle-detection-rules",
    "budget-alert-review": "budget-alerts",
}

# Mapping: provides capability → expected automation script
_CAPABILITY_SCRIPT_MAP: dict[str, str] = {
    "cost-anomaly-detection": "finops_anomaly_detect.py",
    "idle-resource-discovery": "finops_idle_scan.py",
    "tag-compliance-reporting": "finops_tag_audit.py",
    "ri-sp-coverage-analysis": "finops_ri_sp_analysis.py",
    "budget-alert-review": "finops_budget_setup.py",
}

# AIOps routing files to check for finops-core references
_ROUTING_FILES = [
    "aws-aiops-orchestrator/SKILL.md",
    "aws-aiops-cruise/SKILL.md",
    "aws-aiops-copilot/SKILL.md",
]

# Inference rule prefix for FinOps
_COST_RULE_PREFIX = "COST-"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_project_root() -> Path:
    """Walk up from this script to find the repo root (has aws-finops-core/)."""
    p = Path(__file__).resolve().parent
    for _ in range(5):
        if (p / "aws-finops-core").is_dir():
            return p
        p = p.parent
    return Path(__file__).resolve().parent.parent


def _parse_frontmatter_provides(skill_md: Path) -> list[str]:
    """Extract `metadata.provides` list from SKILL.md YAML frontmatter."""
    text = skill_md.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return []

    # Find closing ---
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return []

    # Find `provides:` block and collect list items
    provides: list[str] = []
    in_provides = False
    for i in range(1, end_idx):
        stripped = lines[i].strip()
        if stripped.startswith("provides:"):
            in_provides = True
            continue
        if in_provides:
            if stripped.startswith("- "):
                provides.append(stripped[2:].strip().strip('"').strip("'"))
            elif stripped and not stripped.startswith("#"):
                # Non-list line ends the block
                break
    return provides


def _grep_count(path: Path, pattern: str) -> int:
    """Count lines matching a regex pattern in a file."""
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8")
    return len(re.findall(pattern, text, re.MULTILINE))


# ---------------------------------------------------------------------------
# Dimension auditors
# ---------------------------------------------------------------------------

def audit_d1_capability(root: Path) -> dict:
    """D1: Capability coverage — provides vs references."""
    skill_md = root / "aws-finops-core" / "SKILL.md"
    ref_dir = root / "aws-finops-core" / "references"

    if not skill_md.exists():
        return {"score": 0.0, "gaps": ["aws-finops-core/SKILL.md not found"], "total": 0, "covered": 0}

    provides = _parse_frontmatter_provides(skill_md)
    if not provides:
        return {"score": 0.0, "gaps": ["Cannot parse provides from SKILL.md"], "total": 0, "covered": 0}

    gaps = []
    covered = 0
    for cap in provides:
        expected_ref = _CAPABILITY_REF_MAP.get(cap)
        if expected_ref is None:
            # Unknown capability — check if any reference mentions it
            gaps.append(f"{cap}: no known reference mapping")
            continue
        ref_file = ref_dir / f"{expected_ref}.md"
        if ref_file.exists():
            covered += 1
        else:
            gaps.append(f"{cap}: missing reference {expected_ref}.md")

    total = len(provides)
    score = covered / total if total > 0 else 0.0
    return {"score": round(score, 3), "gaps": gaps, "total": total, "covered": covered}


def audit_d2_routing(root: Path) -> dict:
    """D2: Routing coverage — AIOps routes to finops-core."""
    gaps = []
    covered = 0
    total = len(_ROUTING_FILES)

    for rel in _ROUTING_FILES:
        path = root / rel
        if not path.exists():
            gaps.append(f"{rel}: file not found")
            continue
        count = _grep_count(path, r"aws-finops-core|finops")
        if count > 0:
            covered += 1
        else:
            gaps.append(f"{rel}: no finops-core reference")

    score = covered / total if total > 0 else 0.0
    return {"score": round(score, 3), "gaps": gaps, "total": total, "covered": covered}


def audit_d3_automation(root: Path) -> dict:
    """D3: Automation coverage — scripts/finops_*.py existence."""
    scripts_dir = root / "scripts"
    gaps = []
    covered = 0

    # Check known expected scripts
    expected_scripts = set(_CAPABILITY_SCRIPT_MAP.values())
    # Also include this audit script itself
    expected_scripts.add("finops_gap_audit.py")

    total = len(expected_scripts)
    for script_name in sorted(expected_scripts):
        script_path = scripts_dir / script_name
        if script_path.exists():
            covered += 1
        else:
            gaps.append(f"missing script: {script_name}")

    score = covered / total if total > 0 else 0.0
    return {"score": round(score, 3), "gaps": gaps, "total": total, "covered": covered}


def audit_d4_tests(root: Path) -> dict:
    """D4: Test coverage — tests for FinOps scripts."""
    tests_dir = root / "scripts" / "tests"
    gaps = []
    covered = 0

    # Find all finops_*.py scripts
    scripts_dir = root / "scripts"
    finops_scripts = sorted(scripts_dir.glob("finops_*.py"))

    if not finops_scripts:
        return {"score": 0.0, "gaps": ["No finops_*.py scripts found"], "total": 0, "covered": 0}

    total = len(finops_scripts)
    for script in finops_scripts:
        test_name = f"test_{script.stem}.py"
        test_path = tests_dir / test_name
        if test_path.exists():
            covered += 1
        else:
            gaps.append(f"missing test: {test_name}")

    score = covered / total if total > 0 else 0.0
    return {"score": round(score, 3), "gaps": gaps, "total": total, "covered": covered}


def audit_d5_inference(root: Path) -> dict:
    """D5: Inference coverage — COST-* rules in _inference.py."""
    inference_path = root / "aws-aiops-cruise" / "runbooks" / "scripts" / "_inference.py"

    if not inference_path.exists():
        return {"score": 0.0, "gaps": ["_inference.py not found"], "total": 1, "covered": 0}

    text = inference_path.read_text(encoding="utf-8")
    cost_rules = re.findall(rf'rule\s*=\s*"({_COST_RULE_PREFIX}[A-Z0-9-]+)"', text)

    # Also check docs for declared COST rules
    inference_rules_md = root / "aws-aiops-cruise" / "references" / "inference-rules.md"
    declared_rules: set[str] = set()
    if inference_rules_md.exists():
        doc_text = inference_rules_md.read_text(encoding="utf-8")
        declared_rules = set(re.findall(rf'({_COST_RULE_PREFIX}[A-Z0-9-]+)', doc_text))

    implemented = set(cost_rules)
    gaps = []

    if not implemented:
        gaps.append("No COST-* rules implemented in _inference.py")

    # Check for declared but unimplemented
    unimplemented = declared_rules - implemented
    for rule in sorted(unimplemented):
        gaps.append(f"declared but not implemented: {rule}")

    # Score: at least 1 COST rule = partial; all declared = full
    total = max(len(declared_rules), 1)
    covered = len(implemented & declared_rules) if declared_rules else len(implemented)
    score = covered / total if total > 0 else 0.0

    return {"score": round(score, 3), "gaps": gaps, "total": total, "covered": covered}


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def run_audit(root: Path) -> dict:
    """Run all 5 dimension audits and return structured report."""
    dims = {
        "D1_capability_coverage": audit_d1_capability(root),
        "D2_routing_coverage": audit_d2_routing(root),
        "D3_automation_coverage": audit_d3_automation(root),
        "D4_test_coverage": audit_d4_tests(root),
        "D5_inference_coverage": audit_d5_inference(root),
    }

    scores = [d["score"] for d in dims.values()]
    overall = round(sum(scores) / len(scores), 3) if scores else 0.0
    has_gaps = any(d["gaps"] for d in dims.values())

    return {
        "audit_date": datetime.now(timezone.utc).isoformat(),
        "project_root": str(root),
        "dimensions": dims,
        "overall_score": overall,
        "verdict": "FAIL" if has_gaps else "PASS",
    }


def format_json(report: dict) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False)


def format_markdown(report: dict) -> str:
    lines = [
        "# FinOps Gap Exposure Report (F-7)",
        "",
        f"**Audit Date**: {report['audit_date']}",
        f"**Overall Score**: {report['overall_score']:.1%}",
        f"**Verdict**: {report['verdict']}",
        "",
        "## Dimension Scores",
        "",
        "| Dimension | Score | Covered/Total | Gaps |",
        "|-----------|-------|---------------|------|",
    ]

    for name, dim in report["dimensions"].items():
        gap_count = len(dim["gaps"])
        lines.append(
            f"| {name} | {dim['score']:.1%} | {dim['covered']}/{dim['total']} | {gap_count} |"
        )

    # Detail gaps
    for name, dim in report["dimensions"].items():
        if dim["gaps"]:
            lines.append(f"\n### {name} — Gaps")
            for gap in dim["gaps"]:
                lines.append(f"- {gap}")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="FinOps Gap Exposure Audit (F-7): diagnose real capability gaps."
    )
    parser.add_argument(
        "--format",
        choices=["json", "md"],
        default="md",
        help="Output format (default: md)",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Project root (default: auto-detect)",
    )
    args = parser.parse_args(argv)

    root = args.root if args.root else _find_project_root()
    report = run_audit(root)

    if args.format == "json":
        print(format_json(report))
    else:
        print(format_markdown(report))

    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
