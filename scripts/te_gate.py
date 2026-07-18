#!/usr/bin/env python3
"""
Helper: Token Efficiency (C6) objective gate for AWS skills.

Verifies the machine-checkable Token Efficiency gates defined in
`aws-skill-generator/SKILL.md` §Token Efficiency Requirements and
`AGENTS.md` §14. This turns the C6 MUST-PASS gate from a declarative
checklist into a runnable, CI-friendly hard gate.

Gates checked (objective, machine-verifiable):
  G1  SKILL.md <= 120 lines
  G3  JSON paths declared once at file top (no per-command duplication)
  G4  No cross-file duplicated GCL template body in skill references/

Usage:
    python3 te_gate.py <skill-dir>          # check one skill
    python3 te_gate.py --all                # check every aws-*-ops/
    python3 te_gate.py --all --strict       # exit 1 if any skill fails

Exit code: 0 if all checked skills pass every gate, 1 otherwise
(so it can gate a CI pipeline or a pre-merge hook).

Note: G2/G5/G6 (hard-coded static tables, boto3 docstrings, error-table
compactness) require LLM + human review and are intentionally NOT
machine-checked here — see AGENTS.md §14.2.
"""
import re
import sys
from pathlib import Path

MAX_SKILL_LINES = 120

# Marker lines that introduce the single source-of-truth JSON-path block.
JSON_PATH_HEADER_RE = re.compile(r"^#{1,3}\s*Common JSON Paths\b", re.IGNORECASE)
# A JSON-path-looking declaration line, e.g.  `.Instances[].InstanceId`
JSON_PATH_LINE_RE = re.compile(r"^\s*[\w.\[\]]+\s*[=|—-]?\s*`?\.[\w.\[\]]+`?")

# GCL template body fragments that must NOT appear inline in a skill's
# prompt-templates.md (they live only in prompt-skeletons.md).
GCL_BODY_MARKERS = ("You are the Generator", "You are the Critic", "You are the Orchestrator")


def check_g1(skill_dir: Path) -> tuple[bool, str]:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return False, "SKILL.md missing"
    lines = skill_md.read_text(encoding="utf-8").count("\n") + 1
    if lines <= MAX_SKILL_LINES:
        return True, f"{lines} lines (<= {MAX_SKILL_LINES})"
    return False, f"{lines} lines (> {MAX_SKILL_LINES})"


def check_g3(skill_dir: Path) -> tuple[bool, str]:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return False, "SKILL.md missing"
    text = skill_md.read_text(encoding="utf-8")
    lines = text.splitlines()

    header_idx = next((i for i, ln in enumerate(lines) if JSON_PATH_HEADER_RE.match(ln)), None)
    if header_idx is None:
        # No centralized block declared. If there are no JSON paths at all,
        # that's fine (skill may not need them); if there ARE, it's a FAIL.
        has_paths = any(JSON_PATH_LINE_RE.match(ln) for ln in lines)
        if has_paths:
            return False, "JSON paths present but no 'Common JSON Paths' header (TE-4)"
        return True, "no JSON paths needed"

    # Count JSON-path declaration lines inside the header block (until next
    # blank-line-delimited section or next '##' header).
    block = []
    for ln in lines[header_idx + 1:]:
        if ln.startswith("##") and not JSON_PATH_HEADER_RE.match(ln):
            break
        block.append(ln)
    declared = [ln for ln in block if JSON_PATH_LINE_RE.match(ln)]
    if not declared:
        return False, "Common JSON Paths header present but empty (TE-4)"

    # Verify each declared path does not re-appear scattered in the body
    # (per-command duplication). Collect the path tokens after '=' or '—'.
    declared_tokens = set()
    for ln in declared:
        m = re.split(r"[=|—-]", ln)
        if len(m) >= 2:
            declared_tokens.add(m[-1].strip().strip("`").strip())

    body_dupe = []
    for i, ln in enumerate(lines):
        if i <= header_idx:
            continue
        for tok in declared_tokens:
            if tok and len(tok) > 3 and tok in ln and JSON_PATH_LINE_RE.match(ln):
                body_dupe.append((i + 1, ln.strip()))
                break
    if body_dupe:
        sample = "; ".join(f"L{ln}:{txt[:40]}" for ln, txt in body_dupe[:3])
        return False, f"JSON path re-declared in body (TE-4): {sample}"
    return True, f"{len(declared)} path(s) declared once at top"


def check_g4(skill_dir: Path) -> tuple[bool, str]:
    refs = skill_dir / "references"
    if not refs.is_dir():
        return True, "no references/ dir"
    pt = refs / "prompt-templates.md"
    if not pt.exists():
        return True, "no prompt-templates.md (not a GCL skill)"
    text = pt.read_text(encoding="utf-8")
    found = [m for m in GCL_BODY_MARKERS if m in text]
    if found:
        return False, f"GCL template body duplicated inline: {found} (TE-6, use skeleton)"
    return True, "no GCL template body duplicated"


def gate_skill(skill_dir: Path) -> dict:
    results = {
        "skill": skill_dir.name,
        "G1": check_g1(skill_dir),
        "G3": check_g3(skill_dir),
        "G4": check_g4(skill_dir),
    }
    return results


def main(argv: list[str]) -> int:
    args = argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    strict = "--strict" in args
    check_all = "--all" in args
    roots = [a for a in args if not a.startswith("--")]

    repo = Path(__file__).resolve().parent.parent
    targets = []
    if check_all:
        targets = sorted([p for p in repo.glob("aws-*-ops") if p.is_dir()])
    elif roots:
        targets = [repo / r for r in roots]

    if not targets:
        print("ERROR: pass a skill dir, --all, or --help", file=sys.stderr)
        return 2

    all_pass = True
    for t in targets:
        r = gate_skill(t)
        print(f"\n=== {r['skill']} ===")
        for gate in ("G1", "G3", "G4"):
            ok, msg = r[gate]
            status = "PASS" if ok else "FAIL"
            print(f"  [{status}] {gate}: {msg}")
            all_pass = all_pass and ok

    print("\n=== SUMMARY ===")
    print("PASS" if all_pass else "FAIL")
    if strict and not all_pass:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
