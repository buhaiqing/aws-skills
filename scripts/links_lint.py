#!/usr/bin/env python3
"""SR-4 verification: cross-file markdown `#anchor` links must exist.

Scans skill ``SKILL.md`` for ``[text](path.md#anchor)`` links, resolves
relative to the skill dir, and checks GitHub-style heading slugs.

CLI (canonical)::

    python3 scripts/links_lint.py lint [--all|--skill NAME] [--repo PATH]

Hook-compatible aliases (pre-commit)::

    python3 scripts/links_lint.py --all [--strict]
    python3 scripts/links_lint.py <skill-dir> [--strict]

``--strict`` is accepted for hook compat (lint always fails closed on breaks).
Exit 0 if every anchor exists; exit 1 listing broken ones.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

LINK_RE = re.compile(
    r"\[([^\]]*)\]\((?!https?://)([^)#]+\.md)#([A-Za-z0-9_./-]+)\)"
)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
_STRIP = str.maketrans("", "", ":.,&()?!/")


def gh_anchor(text: str) -> str:
    """Convert heading text to a GitHub-style anchor (SR-4)."""
    s = text.lower().replace(" ", "-").translate(_STRIP)
    # Em/en dashes and similar → hyphen, then collapse runs.
    s = re.sub(r"[—–−]+", "-", s)
    while "--" in s:
        s = s.replace("--", "-")
    return s.strip("-")


def collect_anchors(ref_path: Path) -> set[str]:
    text = ref_path.read_text(encoding="utf-8")
    return {gh_anchor(m.group(2)) for m in HEADING_RE.finditer(text)}


def discover_skills(repo: Path) -> list[Path]:
    skills: list[Path] = []
    for d in sorted(repo.iterdir()):
        if d.is_dir() and d.name.startswith("aws-") and (d / "SKILL.md").exists():
            skills.append(d)
    return skills


def check_skill(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return [f"{skill_dir.name}: SKILL.md missing"]
    text = skill_md.read_text(encoding="utf-8")
    for m in LINK_RE.finditer(text):
        rel, anchor = m.group(2), m.group(3)
        target = (skill_md.parent / rel).resolve()
        if not target.is_file():
            errors.append(f"{skill_dir.name}/SKILL.md → {rel}#{anchor}: file missing")
            continue
        anchors = collect_anchors(target)
        if anchor not in anchors:
            sample = sorted(anchors)[:3]
            errors.append(
                f"{skill_dir.name}/SKILL.md → {rel}#{anchor}: "
                f"anchor not found (sample: {sample})"
            )
    return errors


def lint(repo: Path, *, skill: str | None = None) -> tuple[int, list[str]]:
    if skill:
        targets = [repo / skill]
    else:
        targets = discover_skills(repo)
    if not targets:
        return 2, ["no skill directories found"]

    all_errors: list[str] = []
    for t in targets:
        errs = check_skill(t)
        if errs:
            print(f"\n=== {t.name} ({len(errs)} broken link(s)) ===")
            for e in errs:
                print(f"  - {e}")
            all_errors.extend(errs)
    if all_errors:
        print(f"\nTOTAL: {len(all_errors)} broken link(s)")
    else:
        n = len(targets)
        print(f"OK: {n} skill(s), 0 broken anchors")
    return (1 if all_errors else 0), all_errors


def _normalize_argv(argv: list[str]) -> list[str]:
    """Map pre-commit aliases onto ``lint ...``."""
    argv = [a for a in argv if a != "--strict"]
    if not argv:
        return ["lint", "--all"]
    if argv[0] == "lint":
        return argv
    if argv[0] in ("-h", "--help"):
        return argv
    if argv[0] == "--all" or argv[0].startswith("--skill") or argv[0] == "--repo":
        return ["lint", *argv]
    # Positional skill directory path (absolute or relative).
    path = Path(argv[0])
    if path.is_dir() or path.name.startswith("aws-"):
        return ["lint", "--skill", path.name, *argv[1:]]
    return ["lint", *argv]


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    argv = _normalize_argv(raw)

    ap = argparse.ArgumentParser(prog="links_lint")
    sub = ap.add_subparsers(dest="cmd", required=True)
    lint_p = sub.add_parser("lint", help="Verify SKILL.md #anchor links.")
    lint_p.add_argument("--skill", help="specific skill dir name")
    lint_p.add_argument("--all", action="store_true", help="lint every aws-* skill")
    lint_p.add_argument("--repo", default=str(REPO))

    args = ap.parse_args(argv)
    if args.cmd != "lint":
        return 2
    if args.skill and args.all:
        ap.error("use --skill or --all, not both")
    if not args.skill and not args.all:
        args.all = True
    code, _ = lint(Path(args.repo), skill=args.skill)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
