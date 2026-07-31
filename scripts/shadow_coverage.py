#!/usr/bin/env python3
"""Shadow coverage gate — ADR-0001 M2 Wave 4.

Every high-risk destructive rich scenario must yield non-empty plan_hash +
ok ShadowEvidence (local simulate). false_block_rate =
blocked_but_should_allow / should_allow_total (fixture: confirmed ALLOW;
drift → BLOCK).

CLI: python3 scripts/shadow_coverage.py check --all-high-risk
     [--shadow-dir PATH] [--out PATH]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from execution_plan import ExecutionPlan, make_plan  # noqa: E402
from golden_eval import (  # noqa: E402
    HIGH_RISK_SKILLS,
    Scenario,
    load_scenarios_for_skill,
)
from shadow_exec import run_shadow  # noqa: E402

_RESOURCE_RE = re.compile(
    r"\b(i-[0-9a-f]+|vol-[0-9a-f]+|ami-[0-9a-f]+|"
    r"arn:aws:[^\s]+|"
    r"[a-z0-9][a-z0-9.\-]{2,62})\b",
    re.I,
)


@dataclass
class ScenarioCoverage:
    skill: str
    scenario_id: str
    plan_hash: str
    ok: bool
    path: str | None = None
    error: str | None = None


@dataclass
class CoverageReport:
    destructive_total: int = 0
    covered: int = 0
    failed: list[ScenarioCoverage] = field(default_factory=list)
    results: list[ScenarioCoverage] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        if self.destructive_total == 0:
            return 1.0
        return self.covered / self.destructive_total

    def to_dict(self) -> dict[str, Any]:
        return {
            "destructive_total": self.destructive_total,
            "covered": self.covered,
            "failed": len(self.failed),
            "pass_rate": round(self.pass_rate, 4),
            "results": [asdict(r) for r in self.results],
        }


def false_block_rate(blocked_but_should_allow: int, should_allow_total: int) -> float:
    """``false_block_rate = blocked_but_should_allow / should_allow_total``."""
    if should_allow_total <= 0:
        return 0.0
    return blocked_but_should_allow / should_allow_total


def _extract_resource_ids(request: str) -> list[str]:
    found = _RESOURCE_RE.findall(request or "")
    out: list[str] = []
    for item in found:
        if item not in out:
            out.append(item)
    return out[:8]


def plan_from_scenario(skill: str, scn: Scenario) -> ExecutionPlan:
    """Build a minimal ExecutionPlan for a destructive scenario."""
    if scn.expected_plan.strip():
        operation = scn.expected_plan.strip()
    else:
        svc = skill.removeprefix("aws-").removesuffix("-ops")
        operation = f"{svc} {scn.id.replace('_', '-')}"
    return make_plan(
        skill=skill,
        operation=operation,
        args={"scenario_id": scn.id, "request": scn.request},
        region=scn.user_region or "us-east-1",
        resource_ids=_extract_resource_ids(scn.request),
        risk="destructive",
    )


def iter_destructive_scenarios(
    repo: Path = REPO,
    skills: tuple[str, ...] = HIGH_RISK_SKILLS,
) -> list[tuple[str, Scenario]]:
    """Load high-risk rich scenarios with ``risk: destructive`` (case-insensitive)."""
    out: list[tuple[str, Scenario]] = []
    for skill in skills:
        for scn in load_scenarios_for_skill(skill, repo):
            if scn.risk.strip().lower() == "destructive":
                out.append((skill, scn))
    return out


def check_destructive_shadow_coverage(
    *,
    shadow_dir: Path,
    repo: Path = REPO,
    skills: tuple[str, ...] = HIGH_RISK_SKILLS,
) -> CoverageReport:
    """Run simulate shadow for every high-risk destructive scenario."""
    shadow_dir.mkdir(parents=True, exist_ok=True)
    report = CoverageReport()
    for skill, scn in iter_destructive_scenarios(repo=repo, skills=skills):
        report.destructive_total += 1
        try:
            plan = plan_from_scenario(skill, scn)
            if not plan.plan_hash:
                raise ValueError("empty plan_hash")
            result = run_shadow(
                plan,
                mode="simulate",
                audit_dir=shadow_dir,
                persist=True,
            )
            row = ScenarioCoverage(
                skill=skill,
                scenario_id=scn.id,
                plan_hash=plan.plan_hash,
                ok=bool(result.ok and result.plan_hash),
                path=result.path,
                error=result.error,
            )
        except Exception as exc:  # noqa: BLE001 — surface per-scenario
            row = ScenarioCoverage(
                skill=skill,
                scenario_id=scn.id,
                plan_hash="",
                ok=False,
                error=str(exc),
            )
        report.results.append(row)
        if row.ok:
            report.covered += 1
        else:
            report.failed.append(row)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="shadow_coverage")
    sub = parser.add_subparsers(dest="cmd", required=True)
    check_p = sub.add_parser(
        "check",
        help="Assert 100% destructive high-risk scenarios produce plan+shadow",
    )
    check_p.add_argument(
        "--all-high-risk",
        action="store_true",
        required=True,
        help=f"Cover skills: {', '.join(HIGH_RISK_SKILLS)}",
    )
    check_p.add_argument(
        "--shadow-dir",
        default=str(REPO / "audit-results" / "shadow"),
        help="Directory for persisted ShadowEvidence JSON",
    )
    check_p.add_argument(
        "--out",
        default="",
        help="Optional coverage report JSON path",
    )
    args = parser.parse_args(argv)

    if args.cmd == "check":
        report = check_destructive_shadow_coverage(
            shadow_dir=Path(args.shadow_dir),
        )
        summary = report.to_dict()
        print(
            f"shadow_coverage: covered={report.covered}/"
            f"{report.destructive_total} "
            f"pass_rate={report.pass_rate:.0%} "
            f"failed={len(report.failed)}"
        )
        if args.out:
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(
                json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"saved: {out}")
        else:
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if report.covered == report.destructive_total and report.destructive_total > 0 else 1

    return 2


if __name__ == "__main__":
    sys.exit(main())
