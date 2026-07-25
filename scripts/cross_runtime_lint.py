#!/usr/bin/env python3
"""Cross-Runtime Portability Lint — L4 #11.

Static analysis of `aws-*-ops/SKILL.md` for runtime-specific hardcodes
(`~/.codex/`, `~/.claude/`, `~/.cursor/`, `/Users/...`, hardcoded python
versions, etc.). Outputs a per-skill portability score [0, 1] and
a Markdown/JSON report for cross-runtime coverage matrix.

Contract: `docs/superpowers/specs/2026-07-25-cross-runtime-lint-design.md`.

CLI:
    python3 scripts/cross_runtime_lint.py lint \\
        --skill aws-ec2-ops --repo .

    python3 scripts/cross_runtime_lint.py lint --all \\
        --out docs/runtime/cross-runtime.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Runtime-specific patterns: (regex, runtime_label, weight)
_PATTERNS: list[tuple[re.Pattern, str, float]] = [
    (re.compile(r"~/\.codex/"), "codex", 1.0),
    (re.compile(r"~/\.claude/"), "claude", 1.0),
    (re.compile(r"~/\.cursor/"), "cursor", 1.0),
    (re.compile(r"`?/Users/[A-Za-z0-9_.-]+/"), "host-path", 1.5),
    (re.compile(r"`?/home/[A-Za-z0-9_.-]+/"), "host-path", 1.5),
    (re.compile(r"\bpython3\.\d+\b"), "py-version", 0.4),
    # version-pin: only flag X.Y.Z in compat/requires/min-version contexts,
    # NOT the skill own `version:` field (which should stay exact).
    (re.compile(r"(?:compat|requires|min[_-]?version)\s*[:=]\s*[\"\x27]?[>=<]*\s*\d+\.\d+\.\d+"), "version-pin", 0.3),
    (re.compile(r"`?/usr/local/bin/"), "usr-local", 0.8),
    (re.compile(r"`?/usr/bin/"), "usr-bin", 0.6),
    (re.compile(r"\bwheel install\b"), "wheel-install", 0.5),
    (re.compile(r"\bsudo apt\b"), "sudo-apt", 1.2),
    (re.compile(r"`brew install\b"), "brew", 0.6),
]


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class CouplingHit:
    runtime: str
    pattern: str
    line_number: int
    line_content: str
    weight: float = 1.0


@dataclass
class SkillLintReport:
    skill: str
    skill_md: str
    score: float
    hits: list[CouplingHit] = field(default_factory=list)
    portable_hints: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def detect_runtime_coupling(skill_md: Path) -> list[CouplingHit]:
    """Scan SKILL.md line-by-line for known runtime-specific patterns."""
    p = Path(skill_md)
    if not p.exists():
        return []
    hits: list[CouplingHit] = []
    for ln, line in enumerate(p.read_text(encoding="utf-8").splitlines(),
                              start=1):
        for pat, runtime, weight in _PATTERNS:
            m = pat.search(line)
            if m:
                hits.append(CouplingHit(
                    runtime=runtime,
                    pattern=m.group(0),
                    line_number=ln,
                    line_content=line.strip()[:120],
                    weight=weight,
                ))
    return hits


def score_portability(skill_md: Path) -> float:
    """Compute portability score [0, 1]. 1.0 = no coupling, lower = coupled.

    Score = max(0, 1 - (sum_weights / 10)). Caps so that a single
    SKILL.md never goes below 0 even with many hits (one bad file
    shouldn't be blacklisted; coverage matrix handles nuance).
    """
    hits = detect_runtime_coupling(skill_md)
    total_weight = sum(h.weight for h in hits)
    score = max(0.0, 1.0 - total_weight / 10.0)
    return round(score, 3)


def lint_repo(repo: Path = REPO) -> dict[str, SkillLintReport]:
    """Walk repo for `aws-*-ops/SKILL.md`, lint each, return dict."""
    repo = Path(repo)
    reports: dict[str, SkillLintReport] = {}
    for skill_dir in sorted(repo.glob("aws-*-ops")):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        hits = detect_runtime_coupling(skill_md)
        score = score_portability(skill_md)
        # Generate portable hints (low-hanging: each hit type has a fix)
        hints = _portable_hints(hits)
        reports[skill_dir.name] = SkillLintReport(
            skill=skill_dir.name,
            skill_md=str(skill_md.relative_to(repo)),
            score=score,
            hits=hits,
            portable_hints=hints,
        )
    return reports


def _portable_hints(hits: list[CouplingHit]) -> list[str]:
    """Return deduplicated portable-fix suggestions based on hit runtimes."""
    hints: list[str] = []
    seen: set[str] = set()
    for h in hits:
        hint = _hint_for_runtime(h.runtime)
        if hint and hint not in seen:
            seen.add(hint)
            hints.append(hint)
    return hints


def _hint_for_runtime(runtime: str) -> str:
    return {
        "codex": "move `~/.codex/config.toml` reference to AGENTS.md §15 'Runtime integration' table; symlink for portability",
        "claude": "move `~/.claude/settings.json` reference to AGENTS.md §15 'Runtime integration' table; use $HOME variable",
        "cursor": "move `~/.cursor/settings.json` reference to AGENTS.md §15 'Runtime integration' table",
        "host-path": "replace /Users/<name>/ with $HOME/ relative path or `python3 scripts/...` (no host path)",
        "py-version": "remove `python3.X.Y` pin; rely on shebang `#!/usr/bin/env python3`",
        "version-pin": "use >=N.N for compat ranges (skill version: field stays exact)",
        "usr-local": "use `python3 -m script` form instead of `/usr/local/bin/X`",
        "usr-bin": "use `cmd` form instead of `/usr/bin/cmd` absolute path",
        "wheel-install": "specify dependency in `requirements.txt` rather than install instructions",
        "sudo-apt": "move system-level deps to README Prerequisites section",
        "brew": "use a portable package manager (pip/npm/cargo) instead of brew",
    }.get(runtime, "")


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_markdown(reports: dict[str, SkillLintReport]) -> str:
    """Render Markdown coverage matrix."""
    lines = ["# Cross-Runtime Portability Report", ""]
    if not reports:
        lines.append("_(no skills found)_")
        return "\n".join(lines) + "\n"

    avg = sum(r.score for r in reports.values()) / len(reports)
    lines.append(f"Skills: **{len(reports)}**  |  Avg portability: **{avg:.2f}**")
    lines.append("")

    # Sort by score (worst first)
    sorted_reports = sorted(reports.values(), key=lambda r: r.score)
    lines.append("## Per-skill portability score")
    lines.append("")
    lines.append("| Skill | Score | Hits | Worst runtime |")
    lines.append("|-------|-------|------|---------------|")
    for r in sorted_reports:
        worst = max((h.runtime for h in r.hits), default="(none)",
                    key=lambda x: sum(h.weight for h in r.hits
                                       if h.runtime == x))
        lines.append(f"| {r.skill} | {r.score:.2f} | {len(r.hits)} | {worst} |")
    lines.append("")

    lines.append("## Suggested portable fixes")
    lines.append("")
    seen_hints: set[str] = set()
    for r in sorted_reports:
        for h in r.portable_hints:
            if h in seen_hints:
                continue
            seen_hints.add(h)
            lines.append(f"- {h}")
    lines.append("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _emit_skill_markdown(r: SkillLintReport) -> str:
    lines = [f"## {r.skill}", ""]
    lines.append(f"- score: **{r.score:.2f}**")
    lines.append(f"- hits: {len(r.hits)}")
    if r.hits:
        lines.append("")
        lines.append("| Line | Runtime | Pattern | Content |")
        lines.append("|------|---------|---------|---------|")
        for h in r.hits[:20]:  # cap
            content = h.line_content.replace("|", "\\|")
            lines.append(f"| {h.line_number} | {h.runtime} | `{h.pattern}` | `{content}` |")
    if r.portable_hints:
        lines.append("")
        lines.append("**Portable hints**:")
        for h in r.portable_hints:
            lines.append(f"- {h}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="cross_runtime_lint")
    sub = ap.add_subparsers(dest="cmd", required=True)

    lint_p = sub.add_parser("lint", help="Lint one skill or all.")
    lint_p.add_argument("--skill", help="specific aws-<svc>-ops skill")
    lint_p.add_argument("--all", action="store_true",
                        help="lint every aws-*-ops in repo")
    lint_p.add_argument("--repo", default=str(REPO))
    lint_p.add_argument("--out", default="-")
    lint_p.add_argument("--json", action="store_true")

    args = ap.parse_args(argv)

    if args.cmd != "lint":
        ap.error("unknown command")
        return 2

    if not (args.skill or args.all):
        ap.error("provide --skill X or --all")
        return 2

    repo = Path(args.repo)
    if args.all:
        reports = lint_repo(repo=repo)
    else:
        skill_md = repo / args.skill / "SKILL.md"
        hits = detect_runtime_coupling(skill_md)
        score = score_portability(skill_md)
        reports = {args.skill: SkillLintReport(
            skill=args.skill, skill_md=str(skill_md.relative_to(repo)),
            score=score, hits=hits,
            portable_hints=_portable_hints(hits),
        )}

    if args.json:
        payload = {name: asdict(r) for name, r in reports.items()}
        sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    else:
        if args.all:
            md = render_markdown(reports)
        else:
            md = _emit_skill_markdown(reports[args.skill])
        if args.out == "-":
            sys.stdout.write(md)
        else:
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(md, encoding="utf-8")
            print(f"saved: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
