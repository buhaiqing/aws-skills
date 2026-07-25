#!/usr/bin/env python3
"""Golden Eval — Eval-Driven Dev (L4 #7).

Each L1/L2 skill ships a `golden-scenarios.yaml` (≥5 representative scenarios).
This module replays each scenario through `gcl_runner.py --self-test`, compares
the actual trace status + scores against expectations, and (optionally)
diffs the current run against a saved baseline to flag regressions.

Contract — see `docs/superpowers/specs/2026-07-25-eval-driven-dev-design.md`.

CLI:
    python3 scripts/golden_eval.py run \\
        --skill aws-ec2-ops \\
        --scenarios aws-ec2-ops/golden-scenarios.yaml \\
        --out audit-results/golden/aws-ec2-ops.json

    python3 scripts/golden_eval.py diff \\
        --current audit-results/golden/aws-ec2-ops.json \\
        --baseline audit-results/golden/aws-ec2-ops-baseline.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

try:
    import yaml as _yaml  # noqa: F401
    _HAS_YAML = True
except ImportError:  # pragma: no cover
    _HAS_YAML = False
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

VALID_STATUSES = frozenset({"PASS", "SAFETY_FAIL", "MAX_ITER"})

REPO = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO / "scripts"
GCL_RUNNER = SCRIPTS_DIR / "gcl_runner.py"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Scenario:
    id: str
    description: str
    request: str
    expected_status: str
    user_region: str = ""
    safety_confirm: str = ""


@dataclass
class ScenarioResult:
    scenario: dict
    actual_status: str
    actual_scores: dict[str, float]
    matched_status: bool
    score_deltas: dict[str, float] = field(default_factory=dict)


@dataclass
class BaselineReport:
    regressions: list[str]
    fixed: list[str]
    unchanged: list[str]
    missing_in_baseline: list[str]
    missing_in_current: list[str]

    @property
    def has_regression(self) -> bool:
        return bool(self.regressions)


# ---------------------------------------------------------------------------
# Scenario loader (very small YAML parser — the only fields used)
# ---------------------------------------------------------------------------

def _yaml_minimal_load(text: str) -> Any:
    """Thin wrapper over PyYAML safe_load (handle empty / multi-doc).

    The golden-scenarios schema is flat enough that yaml.safe_load is
    sufficient; we add explicit error wrapping so caller-facing failures
    cite the file path.
    """
    import yaml as _yaml  # local import: keep module import lazy
    try:
        return _yaml.safe_load(text)
    except _yaml.YAMLError as exc:
        raise ValueError(f"YAML parse error: {exc}") from exc


# ---------------------------------------------------------------------------
# Scenario loading
# ---------------------------------------------------------------------------

def load_scenarios(path: Path) -> list[Scenario]:
    """Parse `scenarios.yaml` (multi-doc) into a list of Scenario objects.

    Expected top level (single doc):
        skill: aws-x-ops
        scenarios:
          - id: foo
            description: ...
            request: ...
            expected_status: PASS
            user_region: us-east-1
            safety_confirm: ""
    """
    text = path.read_text(encoding="utf-8")
    doc = _yaml_minimal_load(text)
    if not isinstance(doc, dict):
        raise ValueError(f"top-level of {path} must be a mapping")
    raw_list = doc.get("scenarios", [])
    if not isinstance(raw_list, list):
        raise ValueError(f"{path}: 'scenarios' must be a list")

    out: list[Scenario] = []
    for row in raw_list:
        if not isinstance(row, dict):
            raise ValueError(f"{path}: each scenario must be a mapping")
        scn_id = row.get("id")
        if not scn_id:
            raise ValueError(f"{path}: scenario missing required 'id'")
        request = row.get("request", "")
        expected_status = row.get("expected_status", "")
        if expected_status not in VALID_STATUSES:
            raise ValueError(
                f"{path}: scenario {scn_id!r} expected_status="
                f"{expected_status!r} not in {sorted(VALID_STATUSES)}"
            )
        out.append(Scenario(
            id=str(scn_id),
            description=str(row.get("description", "")),
            request=str(request),
            expected_status=expected_status,
            user_region=str(row.get("user_region", "")),
            safety_confirm=str(row.get("safety_confirm", "")),
        ))
    return out


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def _invoke_gcl_runner(
    skill: str,
    request: str,
    user_region: str,
    safety_confirm: str,
    gcl_runner_path: Path = GCL_RUNNER,
) -> dict:
    """Invoke gcl_runner.py and return the trace dict.

    gcl_runner's stdout is a human-readable summary (`status: PASS`,
    `trace: audit-results/gcl-trace-YYYYMMDD-HHMMSS.json`); the trace
    itself is persisted to a file. We extract the trace path and read
    the JSON file. Falls back to a stub OTHER-status trace if the file
    cannot be read (e.g. skill not found, network error).
    """
    proc = subprocess.run(
        [sys.executable, str(gcl_runner_path),
         "--self-test",
         "--skill", skill,
         "--request", request,
         "--user-region", user_region,
         "--safety-confirm", safety_confirm,
         "--no-prune"],
        capture_output=True, text=True, timeout=60,
    )
    # Strategy 1: trace-file path embedded in gcl_runner stdout
    for line in proc.stdout.splitlines():
        if line.startswith("trace:"):
            rel = line.split(":", 1)[1].strip()
            trace_path = (gcl_runner_path.parent.parent / rel).resolve()
            if trace_path.exists():
                try:
                    return json.loads(trace_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    pass
            break
    # Strategy 2: stdout is raw JSON (useful for test mocks / future APIs)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        pass
    # Strategy 3: fallback to OTHER-status trace so callers can see what happened
    return {
        "skill": skill,
        "request": request,
        "final": {
            "status": "OTHER",
            "iter": 0,
            "error": (proc.stdout or proc.stderr).strip()[:200],
        },
        "iterations": [],
    }


def run_scenario(
    scenario: Scenario,
    skill: str,
    gcl_runner_path: Path = GCL_RUNNER,
) -> ScenarioResult:
    """Run one scenario via `gcl_runner --self-test`, return ScenarioResult.

    Exit code 0 = PASS, 1 = SAFETY_FAIL/MAX_ITER; we do not raise.
    """
    trace = _invoke_gcl_runner(
        skill=skill,
        request=scenario.request,
        user_region=scenario.user_region,
        safety_confirm=scenario.safety_confirm,
        gcl_runner_path=gcl_runner_path,
    )
    actual_status = (trace.get("final") or {}).get("status", "OTHER")
    iters = trace.get("iterations", [])
    actual_scores: dict[str, float] = {}
    if iters:
        scores = (iters[-1].get("critic") or {}).get("scores", {}) or {}
        for k, v in scores.items():
            try:
                actual_scores[k] = float(v)
            except (TypeError, ValueError):
                pass
    matched_status = (actual_status == scenario.expected_status)
    return ScenarioResult(
        scenario=asdict(scenario),
        actual_status=actual_status,
        actual_scores=actual_scores,
        matched_status=matched_status,
        score_deltas={},
    )


def run_scenarios(
    scenarios: list[Scenario],
    skill: str,
    gcl_runner_path: Path = GCL_RUNNER,
) -> list[ScenarioResult]:
    """Run all scenarios; return one ScenarioResult per scenario (in order)."""
    return [run_scenario(s, skill, gcl_runner_path) for s in scenarios]


# ---------------------------------------------------------------------------
# Baseline comparison
# ---------------------------------------------------------------------------

def compare_to_baseline(
    current: list[ScenarioResult],
    baseline: list[ScenarioResult],
) -> BaselineReport:
    """Three-way classification: regressions / fixed / unchanged.

    - regression: matched_status was True in baseline, now False
    - fixed:      matched_status was False in baseline, now True
    - unchanged:  matched_status equal in both
    - missing_in_baseline: scenarios in current with no baseline record
      (new scenarios — not a regression, just new coverage)
    - missing_in_current:  scenarios in baseline but absent now
      (treated as regression: capability disappeared)
    """
    def _id(r: Any) -> str:
        s = r["scenario"] if isinstance(r, dict) else r.scenario
        return s["id"] if isinstance(s, dict) else s.id

    def _matched(r: Any) -> bool:
        return r["matched_status"] if isinstance(r, dict) else r.matched_status

    base_by_id: dict[str, Any] = {_id(r): r for r in baseline}
    curr_by_id: dict[str, Any] = {_id(r): r for r in current}

    regressions: list[str] = []
    fixed: list[str] = []
    unchanged: list[str] = []
    missing_in_baseline: list[str] = []

    for r in current:
        cid = _id(r)
        if cid not in base_by_id:
            missing_in_baseline.append(cid)
            continue
        b_match = _matched(base_by_id[cid])
        c_match = _matched(r)
        if b_match and not c_match:
            regressions.append(cid)
        elif not b_match and c_match:
            fixed.append(cid)
        else:
            unchanged.append(cid)

    missing_in_current = sorted(set(base_by_id) - set(curr_by_id))
    # Missing-in-current is also a regression (capability disappeared)
    regressions = sorted(set(regressions) | set(missing_in_current))
    return BaselineReport(
        regressions=sorted(regressions),
        fixed=sorted(fixed),
        unchanged=sorted(unchanged),
        missing_in_baseline=sorted(missing_in_baseline),
        missing_in_current=sorted(missing_in_current),
    )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def save_results(results: list[ScenarioResult], path: Path, skill: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "skill": skill,
        "results": [asdict(r) for r in results],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_results(path: Path) -> list[ScenarioResult]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    out: list[ScenarioResult] = []
    for r in payload["results"]:
        out.append(ScenarioResult(
            scenario=r["scenario"],
            actual_status=r["actual_status"],
            actual_scores=r.get("actual_scores", {}),
            matched_status=r["matched_status"],
            score_deltas=r.get("score_deltas", {}),
        ))
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _emit_run_summary(results: list[ScenarioResult]) -> int:
    n_pass = sum(1 for r in results if r.matched_status)
    n_total = len(results)
    n_fail = n_total - n_pass
    print(f"scenarios: {n_pass}/{n_total} matched expected_status")
    for r in results:
        # r is always ScenarioResult dataclass; r.scenario is a dict (asdict)
        sid = r.scenario["id"] if isinstance(r.scenario, dict) else r.scenario.id
        flag = "ok" if r.matched_status else "FAIL"
        print(f"  [{flag}] {sid:30s} actual={r.actual_status}")
    return 0 if n_fail == 0 else 1


def _emit_diff_report(report: BaselineReport) -> int:
    print("## Regression Report")
    print(f"regressions:        {len(report.regressions)}")
    print(f"fixed:              {len(report.fixed)}")
    print(f"unchanged:          {len(report.unchanged)}")
    if report.missing_in_baseline:
        print(f"missing_in_baseline: {len(report.missing_in_baseline)} (new — not regressions)")
    if report.missing_in_current:
        print(f"missing_in_current:  {len(report.missing_in_current)} (capability disappeared)")
    if report.regressions:
        print("\nRegressions:")
        for sid in report.regressions:
            print(f"  - {sid}")
    if report.fixed:
        print("\nFixed:")
        for sid in report.fixed:
            print(f"  - {sid}")
    return 1 if report.has_regression else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="golden_eval")
    sub = ap.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="Run a scenarios YAML.")
    run_p.add_argument("--skill", required=True)
    run_p.add_argument("--scenarios", required=True,
                       help="Path to a scenarios YAML.")
    run_p.add_argument("--out", required=True, help="Output JSON path.")
    run_p.add_argument("--gcl-runner",
                       default=str(GCL_RUNNER))

    diff_p = sub.add_parser("diff",
                            help="Compare current vs baseline run JSON.")
    diff_p.add_argument("--current", required=True)
    diff_p.add_argument("--baseline", required=True)

    args = ap.parse_args(argv)

    if args.cmd == "run":
        scenarios = load_scenarios(Path(args.scenarios))
        gcl_path = Path(args.gcl_runner)
        results = run_scenarios(scenarios, skill=args.skill,
                                gcl_runner_path=gcl_path)
        save_results(results, Path(args.out), skill=args.skill)
        print(f"saved: {args.out}")
        return _emit_run_summary(results)

    if args.cmd == "diff":
        current = load_results(Path(args.current))
        baseline = load_results(Path(args.baseline))
        report = compare_to_baseline(current, baseline)
        return _emit_diff_report(report)

    ap.error(f"unknown command: {args.cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
