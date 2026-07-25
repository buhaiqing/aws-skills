"""Composite skill lint — closes L2.2 (per maturity-2026-07-26.md).

Composite / orchestrator-meta skills declare a `delegate:` block mapping target
skill names to operation lists. This linter statically verifies:

1. Each target skill directory exists
2. Each (target, operation) resolves in the target's `provides:` or
   `delegate.accepts:` (whichever the target uses)

Run as a CLI for local checks or as a CI gate (see .github/workflows/setup-hooks.yml).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

KNOBS = {
    "composite_types": ("composite", "orchestrator-meta"),
    "score_per_ref": 1.0,
}

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


@dataclass(frozen=True)
class DelegateRef:
    parent: str
    target: str
    operation: str
    line_number: int


@dataclass(frozen=True)
class CompositeIssue:
    parent: str
    target: str
    operation: str
    issue: str  # "target_dir_missing" | "operation_not_provided"
    detail: str


@dataclass(frozen=True)
class CompositeLintReport:
    parent: str
    score: float
    refs: list[DelegateRef] = field(default_factory=list)
    issues: list[CompositeIssue] = field(default_factory=list)


def _parse_frontmatter(text: str) -> dict[str, object]:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    fm: dict[str, object] = {}
    current_key: str | None = None
    current_list: list[str] | None = None
    current_dict_key: str | None = None
    current_dict_ops: list[str] | None = None
    current_dict: dict[str, list[str]] = {}
    for line in m.group(1).splitlines():
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if indent == 0 and ":" in stripped:
            key, _, value = stripped.partition(":")
            value = value.strip()
            if value:
                fm[key.strip()] = value
                current_key = None
            else:
                current_key = key.strip()
                current_list = []
                fm[current_key] = current_list
        elif indent == 2 and stripped.startswith("- "):
            if current_list is not None:
                current_list.append(stripped[2:].strip())
        elif indent == 2 and ":" in stripped and current_list is not None:
            # New dict under current_key
            key, _, _ = stripped.partition(":")
            current_dict_key = key.strip()
            current_dict_ops = []
            current_dict[current_dict_key] = current_dict_ops
            current_list = None  # stop appending to list
        elif indent == 4 and stripped.startswith("- ") and current_dict_ops is not None:
            current_dict_ops.append(stripped[2:].strip())
    # If we built a dict for delegate, store it
    if "delegate" in fm and isinstance(fm["delegate"], list):
        # list form — convert; otherwise keep as dict
        pass
    if current_dict:
        # Merge dict-form into last list-key in fm (usually "delegate")
        for k in fm:
            if isinstance(fm[k], list) and current_dict:
                # heuristic: replace last list with dict if we saw dict-form entries
                fm[k] = current_dict
                break
    return fm


def _is_composite(fm: dict[str, object]) -> bool:
    md = fm.get("metadata")
    if not isinstance(md, str):
        # metadata is a nested structure (str repr); not parsed in this minimal impl
        return False
    return False  # we'll parse metadata properly via _parse_metadata


def _parse_metadata(text: str) -> dict[str, object]:
    """Extract metadata block as a dict (light YAML-ish parser for our shape).

    Recognized shapes:
      metadata:
        type: composite          # scalar
        provides:                # flat list
        - op1
        - op2
        delegate:                # dict[target, list[op]]
          target-skill:
          - op1
          - op2
          other-target:
          - op3
    """
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    body = m.group(1)
    md_match = re.search(r"^metadata:\s*\n((?:  .*\n?)+)", body, re.MULTILINE)
    if not md_match:
        return {}
    md: dict[str, object] = {}
    # state: which container the next `- item` should land in
    flat_list: list[str] | None = None  # for `provides:` / `accepts:`
    dict_target: dict[str, list[str]] | None = None  # for `delegate:`
    dict_ops: list[str] | None = None  # for `target-skill:` under delegate
    for raw in md_match.group(1).splitlines():
        if not raw.strip():
            continue
        indent = len(raw) - len(raw.lstrip())
        s = raw.strip()
        if indent == 2 and ":" in s and not s.startswith("-"):
            # New top-level key under metadata
            key, _, value = s.partition(":")
            key = key.strip()
            value = value.strip()
            flat_list = None
            dict_target = None
            dict_ops = None
            if value:
                # Inline list form: key: ["a", "b", "c"]
                m = re.match(r"^\[(.*)\]$", value)
                if m:
                    raw = m.group(1)
                    items = []
                    for x in raw.split(","):
                        s = x.strip().strip('"').strip("'")
                        if s:
                            items.append(s)
                    md[key] = items
                else:
                    md[key] = value
            elif key in ("provides", "accepts"):
                flat_list = []
                md[key] = flat_list
            elif key == "delegate":
                dict_target = {}
                md[key] = dict_target
            # else: ignore unknown list/dict (environment, etc.)
        elif s.startswith("- "):
            item = s[2:].strip()
            if flat_list is not None:
                flat_list.append(item)
            elif dict_ops is not None:
                dict_ops.append(item)
        elif indent >= 4 and ":" in s and dict_target is not None and not s.startswith("-"):
            # New target under delegate: (target key is at indent 4)
            k, _, v = s.partition(":")
            k = k.strip()
            v = v.strip()
            dict_ops = []
            # Inline list form: accepts: ["a", "b"]
            m = re.match(r"^\[(.*)\]$", v)
            if m:
                for x in m.group(1).split(","):
                    s2 = x.strip().strip('"').strip("'")
                    if s2:
                        dict_ops.append(s2)
            dict_target[k] = dict_ops
    return md


def _get_target_operations(target_fm_meta: dict[str, object], target_dir: Path) -> set[str]:
    """Collect ops from target's provides: OR delegate.accepts:."""
    ops: set[str] = set()
    prov = target_fm_meta.get("provides")
    if isinstance(prov, list):
        ops.update(prov)
    # aiops-cruise style: delegate.accepts
    delegate = target_fm_meta.get("delegate")
    if isinstance(delegate, dict):
        accepts = delegate.get("accepts")
        if isinstance(accepts, list):
            ops.update(accepts)
    return ops


def _line_number(text: str, marker: str) -> int:
    for i, line in enumerate(text.splitlines(), 1):
        if marker in line:
            return i
    return 0


def lint_composite(skill_md: Path, repo: Path | None = None) -> CompositeLintReport:
    repo = repo or skill_md.parent.parent
    parent_name = skill_md.parent.name
    text = skill_md.read_text(encoding="utf-8")
    md = _parse_metadata(text)

    type_ = md.get("type", "")
    if type_ not in KNOBS["composite_types"]:
        return CompositeLintReport(parent=parent_name, score=1.0)

    delegate = md.get("delegate")
    if not isinstance(delegate, dict):
        return CompositeLintReport(parent=parent_name, score=1.0)

    refs: list[DelegateRef] = []
    issues: list[CompositeIssue] = []
    for target, ops in delegate.items():
        if not isinstance(ops, list):
            continue
        target_dir = repo / target
        if not target_dir.is_dir():
            for op in ops:
                issues.append(CompositeIssue(
                    parent=parent_name,
                    target=target,
                    operation=op,
                    issue="target_dir_missing",
                    detail=f"target skill directory {target_dir} does not exist",
                ))
            continue
        target_md = target_dir / "SKILL.md"
        if not target_md.exists():
            for op in ops:
                issues.append(CompositeIssue(
                    parent=parent_name,
                    target=target,
                    operation=op,
                    issue="target_dir_missing",
                    detail=f"target SKILL.md missing at {target_md}",
                ))
            continue
        target_text = target_md.read_text(encoding="utf-8")
        target_meta = _parse_metadata(target_text)
        target_ops = _get_target_operations(target_meta, target_dir)
        for op in ops:
            line_no = _line_number(target_text, op) or _line_number(text, op)
            refs.append(DelegateRef(
                parent=parent_name,
                target=target,
                operation=op,
                line_number=line_no,
            ))
            if op not in target_ops:
                issues.append(CompositeIssue(
                    parent=parent_name,
                    target=target,
                    operation=op,
                    issue="operation_not_provided",
                    detail=f"{target} does not declare {op!r} in provides: or accepts:",
                ))

    n_refs = len(refs) if refs else 1  # avoid div-by-zero; score=1.0 if no refs
    score = 1.0 - (len(issues) / n_refs) if issues else 1.0
    return CompositeLintReport(parent=parent_name, score=score, refs=refs, issues=issues)


def lint_repo(repo: Path) -> dict[str, CompositeLintReport]:
    out: dict[str, CompositeLintReport] = {}
    for skill_md in sorted(repo.glob("aws-*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8")
        md = _parse_metadata(text)
        if md.get("type") in KNOBS["composite_types"]:
            report = lint_composite(skill_md, repo=repo)
            out[skill_md.parent.name] = report
    return out


# ---------- CLI ----------
def _cli(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="composite_lint")
    sub = p.add_subparsers(dest="cmd", required=True)
    p_lint = sub.add_parser("lint")
    p_lint.add_argument("--skill", default=None)
    p_lint.add_argument("--all", action="store_true")
    p_lint.add_argument("--repo", default=".")
    p_lint.add_argument("--out", default=None)
    p_lint.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    repo = Path(args.repo).resolve()
    if args.cmd == "lint":
        reports: dict[str, CompositeLintReport] = {}
        if args.skill:
            skill_md = repo / args.skill / "SKILL.md"
            reports[args.skill] = lint_composite(skill_md, repo=repo)
        else:
            reports = lint_repo(repo)
        if args.json:
            payload = {
                name: {
                    "score": r.score,
                    "refs": [{"target": x.target, "operation": x.operation} for x in r.refs],
                    "issues": [{"target": i.target, "operation": i.operation,
                                "issue": i.issue, "detail": i.detail} for i in r.issues],
                }
                for name, r in reports.items()
            }
            print(json.dumps(payload, indent=2))
        else:
            print(f"# Composite Lint Report ({repo})\n")
            any_issue = False
            for name, r in sorted(reports.items()):
                status = "OK" if r.score == 1.0 else "FAIL"
                if r.score != 1.0:
                    any_issue = True
                print(f"## {name}  score={r.score:.2f} [{status}]")
                if r.refs:
                    print(f"  refs: {len(r.refs)}")
                for i in r.issues:
                    print(f"  ISSUE: [{i.issue}] {i.target}.{i.operation} — {i.detail}")
                print()
            if args.out:
                Path(args.out).write_text("\n".join(_render_md(reports)), encoding="utf-8")
                print(f"wrote {args.out}")
        return 1 if any_issue else 0
    return 2


def _render_md(reports: dict[str, CompositeLintReport]) -> list[str]:
    out = ["# Composite Lint Report", ""]
    for name, r in sorted(reports.items()):
        status = "OK" if r.score == 1.0 else "FAIL"
        out.append(f"## {name}  score={r.score:.2f} [{status}]")
        for i in r.issues:
            out.append(f"- [{i.issue}] {i.target}.{i.operation}: {i.detail}")
        out.append("")
    return out


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
