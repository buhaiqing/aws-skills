#!/usr/bin/env python3
"""A/B Test Hard Gate — L4 #9.

Compares two pre-computed golden_eval results JSONs (baseline vs candidate)
and gates a CI pipeline: exit 1 if any scenario regressed.

Also exposes `cascaded_skills(skill)` to list `cross_skill_deps` for
L2 composite skills (advisory; does not participate in gate decision).

Contract: `docs/superpowers/specs/2026-07-25-ab-gate-design.md`.

CLI:
    python3 scripts/ab_gate.py gate \\
        --baseline audit-results/baseline/aws-ec2-ops.json \\
        --candidate audit-results/golden/aws-ec2-ops.json

    python3 scripts/ab_gate.py cascade --skill aws-aiops-copilot

    python3 scripts/ab_gate.py gate ... --json
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Reuse the small YAML lite loader from _frontmatter.py if present; otherwise
# fall back to a regex-based extractor for `cross_skill_deps`. Both paths
# intentionally avoid a PyYAML dependency for this thin CLI.
try:
    from _frontmatter import extract_deps as _fm_extract_deps  # type: ignore
except Exception:  # pragma: no cover
    _fm_extract_deps = None


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ABReport:
    baseline_path: Path
    candidate_path: Path
    regressions: list[str] = field(default_factory=list)
    fixed: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    missing_in_baseline: list[str] = field(default_factory=list)
    missing_in_candidate: list[str] = field(default_factory=list)
    error: str = ""

    @property
    def has_regression(self) -> bool:
        return bool(self.regressions) or bool(self.missing_in_candidate)

    @property
    def has_error(self) -> bool:
        return bool(self.error)

    @property
    def exit_code(self) -> int:
        if self.has_error:
            return 2
        return 1 if self.has_regression else 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _id(row: dict) -> str:
    s = row.get("scenario") or {}
    return str(s.get("id", "?"))


def _matched(row: dict) -> bool:
    return bool(row.get("matched_status"))


def _load_results(path: Path) -> tuple[list[dict] | None, str]:
    """Return (results, error). Error is non-empty on failure."""
    if not path.exists():
        return None, f"file not found: {path}"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON in {path}: {exc}"
    results = payload.get("results")
    if not isinstance(results, list):
        return None, f"{path}: missing 'results' list"
    return results, ""


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def run_ab_gate(
    baseline_path: Path,
    candidate_path: Path,
    drop_threshold: float = 0.05,
) -> ABReport:
    """Compare baseline + candidate golden_eval results.

    `drop_threshold` is currently informational (no per-skill delta
    computation here — `compare_to_baseline` in `golden_eval.py` already
    does that). We expose it for future per-skill pass-rate gating.
    """
    report = ABReport(baseline_path=baseline_path, candidate_path=candidate_path)
    base, err = _load_results(Path(baseline_path))
    if err:
        report.error = f"baseline: {err}"
        return report
    cand, err = _load_results(Path(candidate_path))
    if err:
        report.error = f"candidate: {err}"
        return report

    base_by_id = {_id(r): r for r in base}
    cand_by_id = {_id(r): r for r in cand}

    for cid, r in cand_by_id.items():
        if cid not in base_by_id:
            report.missing_in_baseline.append(cid)
            continue
        b_match = _matched(base_by_id[cid])
        c_match = _matched(r)
        if b_match and not c_match:
            report.regressions.append(cid)
        elif not b_match and c_match:
            report.fixed.append(cid)
        else:
            report.unchanged.append(cid)
    report.missing_in_candidate = sorted(set(base_by_id) - set(cand_by_id))
    return report


def cascaded_skills(skill_name: str, repo: Path = REPO) -> list[str]:
    """Read SKILL.md frontmatter; return `metadata.cross_skill_deps` list."""
    skill_md = Path(repo) / skill_name / "SKILL.md"
    if not skill_md.exists():
        return []
    if _fm_extract_deps is not None:
        try:
            deps = _fm_extract_deps(skill_md)
            return [d for d in deps if not d.startswith("aws-") or "ops" in d]
        except Exception:
            pass
    # Fallback: regex against the frontmatter block
    return _regex_extract_deps(skill_md)


def _regex_extract_deps(skill_md: Path) -> list[str]:
    text = skill_md.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or not lines[0].startswith("---"):
        return []
    end = None
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            end = i
            break
    if end is None:
        return []
    deps: list[str] = []
    in_section = False
    for i in range(1, end):
        line = lines[i]
        if line.startswith("cross_skill_deps:"):
            in_section = True
            continue
        if in_section:
            stripped = line.strip()
            if not stripped:
                continue
            if not stripped.startswith("- "):
                break
            label = stripped[2:].strip()
            if "[" in label:
                label = label.split("]", 1)[0].lstrip("[")
            if label:
                deps.append(label)
    return deps


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _render_markdown(r: ABReport) -> str:
    lines = ["## A/B Gate Report", ""]
    if r.error:
        lines.append(f"**ERROR**: {r.error}")
        return "\n".join(lines) + "\n"
    lines.append(f"- baseline: `{r.baseline_path}`")
    lines.append(f"- candidate: `{r.candidate_path}`")
    lines.append(f"- regressions: **{len(r.regressions)}**")
    lines.append(f"- fixed: **{len(r.fixed)}**")
    lines.append(f"- unchanged: **{len(r.unchanged)}**")
    if r.missing_in_baseline:
        lines.append(f"- missing_in_baseline: {len(r.missing_in_baseline)}")
    if r.missing_in_candidate:
        lines.append(f"- missing_in_candidate: {len(r.missing_in_candidate)}")
    if r.regressions:
        lines.append("\n**Regressions**:")
        for s in r.regressions:
            lines.append(f"- {s}")
    if r.fixed:
        lines.append("\n**Fixed**:")
        for s in r.fixed:
            lines.append(f"- {s}")
    return "\n".join(lines) + "\n"


def _emit_gate(r: ABReport, as_json: bool) -> int:
    if as_json:
        payload = {
            "baseline_path": str(r.baseline_path),
            "candidate_path": str(r.candidate_path),
            "regressions": sorted(r.regressions),
            "fixed": sorted(r.fixed),
            "unchanged": sorted(r.unchanged),
            "missing_in_baseline": sorted(r.missing_in_baseline),
            "missing_in_candidate": sorted(r.missing_in_candidate),
            "error": r.error,
            "exit_code": r.exit_code,
        }
        sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(_render_markdown(r))
    if r.error:
        sys.stderr.write(f"ERROR: {r.error}\n")
    return r.exit_code


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="ab_gate")
    sub = ap.add_subparsers(dest="cmd", required=True)

    gate_p = sub.add_parser("gate",
                            help="Compare baseline vs candidate and gate.")
    gate_p.add_argument("--baseline", required=True)
    gate_p.add_argument("--candidate", required=True)
    gate_p.add_argument("--drop-threshold", type=float, default=0.05)
    gate_p.add_argument("--json", action="store_true",
                        help="Emit JSON instead of Markdown")

    cascade_p = sub.add_parser("cascade",
                               help="List cross_skill_deps for an L2 composite.")
    cascade_p.add_argument("--skill", required=True)

    args = ap.parse_args(argv)

    if args.cmd == "gate":
        r = run_ab_gate(Path(args.baseline), Path(args.candidate),
                        drop_threshold=args.drop_threshold)
        return _emit_gate(r, as_json=args.json)

    if args.cmd == "cascade":
        deps = cascaded_skills(args.skill)
        if not deps:
            print(f"no SKILL.md or no cross_skill_deps for {args.skill}")
            return 0
        print(f"cascaded skills for {args.skill}:")
        for d in deps:
            print(f"  - {d}")
        return 0

    ap.error(f"unknown command: {args.cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
