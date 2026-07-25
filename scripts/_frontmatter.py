#!/usr/bin/env python3
"""Frontmatter dependency extractor for SKILL.md files.

L4 #4 (pre-commit hard gate) requires extracting `metadata.cross_skill_deps`
(and `metadata.delegate`) to verify each referenced directory actually exists
in the repo.

The legacy bash awk parser mis-handled markdown-link syntax:

    cross_skill_deps:
      - aws-foo-ops                          # plain label
      - [aws-foo-ops](../aws-foo-ops)        # markdown link  ← silently dropped

This module supports BOTH forms. It is invoked from
`scripts/hooks/pre-commit`:

    python3 scripts/_frontmatter.py <SKILL.md>
    # stdout: one dep per line
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# `- [name](target)`  OR  `- plain-label`
_LIST_ITEM = re.compile(
    r"""^\s*-\s+"""
    r"""(?:
        \[([^\]]+)\]\([^)]+\)        # group 1: markdown link text
        |
        ([A-Za-z][A-Za-z0-9_-]*)     # group 2: plain label
    )""",
    re.VERBOSE,
)

# Keys whose list values are filesystem deps that must exist in the repo.
_DEP_KEYS = ("cross_skill_deps", "delegate")


def _walk(items: list[str]) -> list[str]:
    """Read YAML list items until the first non-list, non-empty, non-comment line."""
    out: list[str] = []
    for line in items:
        stripped = line.rstrip()
        if not stripped:
            continue
        if stripped.lstrip().startswith("#"):
            continue
        m = _LIST_ITEM.match(stripped)
        if not m:
            # End of the list block
            break
        label = (m.group(1) or m.group(2) or "").strip()
        if label:
            out.append(label)
    return out


def extract_deps(path: Path) -> list[str]:
    """Return deduped dep labels in source order from `path`.

    Empty list if path lacks a YAML frontmatter block or no known dep keys.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or not lines[0].startswith("---"):
        return []
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return []

    deps: list[str] = []
    seen: set[str] = set()
    for i in range(1, end_idx):
        head = lines[i].split(":", 1)[0].strip()
        if head not in _DEP_KEYS:
            continue
        for label in _walk(lines[i + 1 : end_idx]):
            if label not in seen:
                seen.add(label)
                deps.append(label)
    return deps


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("usage: _frontmatter.py <SKILL.md> [<SKILL.md>...]", file=sys.stderr)
        return 1
    rc = 0
    for raw in argv:
        try:
            deps = extract_deps(Path(raw))
        except FileNotFoundError:
            print(f"error: {raw} not found", file=sys.stderr)
            rc = 1
            continue
        for d in deps:
            print(d)
    return rc


if __name__ == "__main__":
    sys.exit(main())
