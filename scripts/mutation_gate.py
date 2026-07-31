#!/usr/bin/env python3
"""Mutation safety gate — verify baseline diff catches removed safety gates.

Hermetic self-test: run a known SAFETY_FAIL scenario, simulate gate removal
(PASS where SAFETY_FAIL expected), assert compare_to_baseline flags regression.

CLI:
    python3 scripts/mutation_gate.py --self-test
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import asdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from golden_eval import (  # noqa: E402
    Scenario,
    ScenarioResult,
    compare_to_baseline,
    load_scenarios_for_skill,
    run_scenario,
)

# Known high-risk destructive scenario: iam delete-user without confirm.
_MUTATION_SKILL = "aws-iam-ops"
_MUTATION_SCENARIO_ID = "iam-delete-user-no-confirm"


def _find_mutation_scenario() -> Scenario:
    for scn in load_scenarios_for_skill(_MUTATION_SKILL, repo=REPO):
        if scn.id == _MUTATION_SCENARIO_ID:
            return scn
    raise RuntimeError(
        f"scenario {_MUTATION_SCENARIO_ID!r} not found under {_MUTATION_SKILL}"
    )


def run_mutation_self_test() -> int:
    """Exit 0 if mutation is detected; exit 1 if gate removal goes unnoticed."""
    scn = _find_mutation_scenario()
    if scn.expected_status != "SAFETY_FAIL":
        print(
            f"mutation_gate: expected {_MUTATION_SCENARIO_ID} "
            f"expected_status=SAFETY_FAIL, got {scn.expected_status!r}",
            file=sys.stderr,
        )
        return 1

    baseline_result = run_scenario(scn, skill=_MUTATION_SKILL)
    if not baseline_result.matched_status:
        print(
            f"mutation_gate: baseline run did not match "
            f"(actual={baseline_result.actual_status!r})",
            file=sys.stderr,
        )
        return 1

    # Simulate removed safety gate: destructive op wrongly passes.
    mutated_result = ScenarioResult(
        scenario=asdict(scn),
        actual_status="PASS",
        actual_scores={"safety": 1.0},
        matched_status=False,
    )

    report = compare_to_baseline([mutated_result], [baseline_result])
    if _MUTATION_SCENARIO_ID not in report.regressions:
        print(
            "mutation_gate: FAIL — gate removal not detected "
            f"(regressions={report.regressions})",
            file=sys.stderr,
        )
        return 1

    print(
        f"mutation_gate: OK — regression detected for {_MUTATION_SCENARIO_ID}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="mutation_gate")
    ap.add_argument(
        "--self-test",
        action="store_true",
        help="Hermetic mutation detection check (no AWS)",
    )
    args = ap.parse_args(argv)

    if args.self_test:
        return run_mutation_self_test()

    ap.error("Provide --self-test")
    return 2


if __name__ == "__main__":
    sys.exit(main())
