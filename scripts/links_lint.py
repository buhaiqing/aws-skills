#!/usr/bin/env python3
"""SR-4 verification: cross-file anchor links must point to real headings.

Scans every `aws-*-ops/SKILL.md` for `[...](references/<file>.md#<anchor>)`
links, then verifies that each anchor exists in the target file as a
heading. This closes the standing rule SR-4 from AGENTS.md §Operational
Guidelines.

Usage:
    python3 links_lint.py <skill-dir>          # check one skill
    python3 links_lint.py --all                # check every aws-*-ops/
    python3 links_lint.py --all --strict       # exit 1 if any skill fails
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

LINK_RE = re.compile(r"\]\(references/([\w-]+\.md)(?:#([\w-]+))?\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


def gh_anchor(text: str) -> str:
    """Convert heading text to GitHub-style anchor."""
    s = text.lower()
    s = s.replace(" ", "-")
    for ch in ":.,&()?!'/":
        s = s.replace(ch, "")
    while "--" in s:
        s = s.replace("--", "-")
    return s.strip("-")


def collect_anchors(ref_path: Path) -> set[str]:
    text = ref_path.read_text(encoding="utf-8")
    return {gh_anchor(m.group(2)) for m in HEADING_RE.finditer(text, re.MULTILINE)}


def check_skill(skill_dir: Path) -> tuple[list[str], list[str]]:
    """Return (errors, infos) for one skill directory."""
    errors: list[str] = []
    infos: list[str] = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return [f"{skill_dir.name}: SKILL.md missing"], []
    text = skill_md.read_text(encoding="utf-8")
    refs_dir = skill_dir / "references"
    for m in LINK_RE.finditer(text):
        ref = m.group(1)
        anchor = m.group(2)
        ref_path = refs_dir / ref
        if not ref_path.exists():
            errors.append(f"{skill_dir.name}/SKILL.md → references/{ref}: file missing")
            continue
        if not anchor:
            continue  # plain file link, OK
        anchors = collect_anchors(ref_path)
        if anchor not in anchors:
            errors.append(
                f"{skill_dir.name}/SKILL.md → {ref}#{anchor}: "
                f"anchor not found (target has {sorted(anchors)[:3]}...)"
            )
    return errors, infos


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("skills", nargs="*", help="skill dirs to check")
    p.add_argument("--all", action="store_true", help="check every aws-*-ops/")
    p.add_argument("--strict", action="store_true", help="exit 1 on any error")
    args = p.parse_args(argv[1:])

    repo = Path(__file__).resolve().parent.parent
    targets: list[Path] = []
    if args.all:
        targets = sorted([p for p in repo.glob("aws-*-ops") if p.is_dir()])
    elif args.skills:
        targets = [repo / s for s in args.skills]
    else:
        p.error("pass skill dirs, --all, or --help")
        return 2

    all_errors: dict[str, list[str]] = {}
    for t in targets:
        errs, _ = check_skill(t)
        all_errors[t.name] = errs
        if errs:
            print(f"\n=== {t.name} ({len(errs)} broken link(s)) ===")
            for e in errs:
                print(f"  [BROKEN] {e}")
        else:
            print(f"=== {t.name}: OK ===")

    total = sum(len(e) for e in all_errors.values())
    print(f"\n=== SUMMARY: {total} broken link(s) across {len(targets)} skill(s) ===")
    return 1 if (args.strict and total > 0) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
