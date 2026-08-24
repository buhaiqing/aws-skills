#!/usr/bin/env python3
"""Render failure-patterns.md from failure-patterns.jsonl (canonical store).

Usage:
    python3 scripts/_render_failure_patterns.py [--jsonl PATH] [--md PATH]

The MD output preserves the original 6-section structure from docs/failure-patterns.md:
  §1  CLI Parameter Errors
  §1.5 Query/Search Silent Miss
  §2  Skill Generation Issues
  §3  Cross-Skill Composition Failures
  §4  Runtime Execution Patterns
  §5  Token Efficiency Violations
  + Usage Guidelines + GCL trace example block
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running as script from repo root or as module from scripts/
if __name__ == "__main__" and __file__:
    sys.path.insert(0, str(Path(__file__).parent))

from failure_kb import FailureRecord, load_jsonl


# ---------------------------------------------------------------------------
# Section definitions — maps category → (heading, column_spec, rows_fmt)
# ---------------------------------------------------------------------------
# column_spec: list of (header, field_key) pairs
# rows_fmt: callable(record) → formatted table row string

_SECTIONS = [
    {
        "category": "cli_parameter",
        "heading": "## 1. CLI Parameter Errors",
        "preamble": (
            "> Extracted from GCL traces. High-frequency patterns first.\n\n"
        ),
        "columns": [
            ("Skill", "skill"),
            ("Command", "command"),
            ("Error Pattern", "error"),
            ("Root Cause", "root_cause"),
            ("Fix", "fix"),
            ("Count", "count_fmt"),
        ],
        "header": "| Skill | Command | Error Pattern | Root Cause | Fix | Count |",
        "separator": "|-------|---------|---------------|------------|-----|-------|",
    },
    {
        "category": "query_miss",
        "heading": "## 1.5. Query / Search Silent Miss（烂查询 > 错工具）",
        "preamble": (
            "> 来源：2026-07-19 CodeGraph A/B 对比实验 E3-Q5。"
            "最隐蔽的失败模式——**查询构造错（烂 glob/正则）比工具选错更危险，"
            "因为它静默错答、不报错**。\n\n"
        ),
        "columns": [
            ("场景", "skill"),       # skill holds the query scenario
            ("错误模式", "command"), # command holds the error pattern
            ("根因", "root_cause"),
            ("修复", "fix"),
            ("计数", "count_fmt"),
        ],
        "header": "| 场景 | 错误模式 | 根因 | 修复 | 计数 |",
        "separator": "|------|----------|------|------|------|",
        # No backtick stripping for this section
        "no_backtick": True,
    },
    {
        "category": "skill_generation",
        "heading": "## 2. Skill Generation Issues",
        "preamble": "> Common structural errors from the skill generator.\n\n",
        "columns": [
            ("Issue Type", "error"),
            ("Frequency", "count_fmt"),
            ("Fix Pattern", "fix"),
            ("First Seen", "first_seen"),
        ],
        "header": "| Issue Type | Frequency | Fix Pattern | First Seen |",
        "separator": "|------------|-----------|-------------|------------|",
    },
    {
        "category": "cross_skill",
        "heading": "## 3. Cross-Skill Composition Failures",
        "preamble": "> Failure patterns in cross-skill orchestration chains.\n\n",
        "columns": [
            ("Source Skill", "skill"),
            ("Target Skill", "command"),
            ("Failure Pattern", "error"),
            ("Resolution", "fix"),
            ("Count", "count_fmt"),
        ],
        "header": "| Source Skill | Target Skill | Failure Pattern | Resolution | Count |",
        "separator": "|--------------|--------------|-----------------|------------|-------|",
    },
    {
        "category": "runtime",
        "heading": "## 4. Runtime Execution Patterns",
        "preamble": "> Runtime failure patterns discovered during GCL execution.\n\n",
        "columns": [
            ("Skill", "skill"),
            ("Operation", "command"),
            ("Failure Pattern", "error"),
            ("Root Cause", "root_cause"),
            ("Prevention", "fix"),
        ],
        "header": "| Skill | Operation | Failure Pattern | Root Cause | Prevention |",
        "separator": "|-------|-----------|-----------------|------------|------------|",
    },
    {
        "category": "token_efficiency",
        "heading": "## 5. Token Efficiency Violations",
        "preamble": "> Common violations of Token Efficiency rules.\n\n",
        "columns": [
            ("TE Rule", "skill"),
            ("Common Violation", "error"),
            ("Fix", "fix"),
            ("Frequency", "count_fmt"),
        ],
        "header": "| TE Rule | Common Violation | Fix | Frequency |",
        "separator": "|---------|------------------|-----|-----------|",
    },
]


def _fmt_count(rec: FailureRecord) -> str:
    c = rec.count
    return f"{c}x" if c > 1 else str(c)


def _cell(rec: FailureRecord, key: str, no_backtick: bool = False) -> str:
    val: str = getattr(rec, key, "")
    if not val:
        return "—"
    if not no_backtick:
        # jsonl stores `\`foo\`` as escaped sequences — unescape all \` pairs first,
        # then strip any remaining leading/trailing backticks.
        val = val.replace("\\`", "`")
        val = val.strip("`")
    # Escape pipe characters in cell content
    val = val.replace("|", "\\|")
    return val


def _render_section(
    section: dict,
    records: list[FailureRecord],
    all_records: list[FailureRecord],
) -> str:
    cat = section["category"]
    heading = section["heading"]
    preamble = section.get("preamble", "")
    columns = section["columns"]
    header = section["header"]
    sep = section["separator"]
    no_backtick = section.get("no_backtick", False)

    # Filter to this category
    cat_records = [r for r in records if r.category == cat]
    if not cat_records and cat != "query_miss":
        # query_miss section is optional — skip if empty
        return ""

    # Sort by count desc, then id
    cat_records = sorted(cat_records, key=lambda r: (-r.count, r.id))

    lines = [heading, "", preamble]

    if cat == "query_miss":
        # §1.5 uses a custom narrative table with Chinese headers
        if not cat_records:
            return ""
        lines.append(header + "")
        lines.append(sep)
        for r in cat_records:
            # skill=scenario, command=error_pattern, root_cause, fix, count
            scenario = _cell(r, "skill", no_backtick)
            err_pat = _cell(r, "command", no_backtick)
            root = _cell(r, "root_cause", no_backtick)
            fix = _cell(r, "fix", no_backtick)
            cnt = _cell(r, "count_fmt", no_backtick)
            lines.append(f"| {scenario} | {err_pat} | {root} | {fix} | {cnt} |")
        lines.append("")
        lines.append(
            '> **判别口诀**：工具返回"无结果"时，先怀疑**自己的查询形状**'
            "（glob/正则/参数），再怀疑工具能力。"
            "烂查询会同时骗过 Grep 和 CodeGraph——与工具无关。\\n"
        )
        return "\n".join(lines) + "\n"

    # Standard table sections
    lines.append(header)
    lines.append(sep)
    for r in cat_records:
        cells = []
        for _col_header, key in columns:
            if key == "count_fmt":
                cells.append(_fmt_count(r))
            else:
                cells.append(_cell(r, key, no_backtick))
        lines.append("| " + " | ".join(cells) + " |")

    lines.append("")
    return "\n".join(lines) + "\n"


def render_markdown(records: list[FailureRecord]) -> str:
    """Render the full failure-patterns.md from a list of FailureRecord."""
    parts = [
        "# Failure Patterns — Reflexion Memory",
        "",
        (
            "> **Purpose**: Structured failure memory extracted from GCL traces "
            "and Self-Review records.\n"
            "> Agents can optionally load this file during Pre-flight to prevent "
            "known errors.\n"
            ">\n"
            "> **Maintenance**: Updated automatically via Self-Review Round 3 "
            "(Lessons Learned).\n"
            "> **Canonical store**: `docs/failure-patterns.jsonl` — edits should "
            "go there; this file is auto-generated.\n"
            "> **Token budget**: ≤ 200 lines. When exceeded, prune low-frequency "
            "patterns (count < 3).\n"
        ),
        "",
        "---",
        "",
    ]

    for section in _SECTIONS:
        rendered = _render_section(section, records, records)
        parts.append(rendered)

    # Usage guidelines — always appended after all sections
    parts.extend([
        "---",
        "",
        "## Usage Guidelines",
        "",
        "### For Agents (Pre-flight)",
        "",
        "```",
        "# Optional: Load failure patterns before executing a skill",
        "# 1. Read this file (lazy-load, ~150 lines)",
        "# 2. Filter patterns by current skill name",
        "# 3. Inject relevant patterns into Generator context as prevention hints",
        "```",
        "",
        "### For Self-Review (Round 3: Lessons Learned)",
        "",
        "```",
        "# After completing R1 + R2:",
        "# 1. Extract new failure patterns from this session",
        "# 2. Check if pattern already exists (dedup by error_signature)",
        "# 3. If new: append to failure-patterns.jsonl with count=1",
        "# 4. If existing: count is incremented automatically",
        "# 5. Run: python3 scripts/_render_failure_patterns.py",
        "# 6. If total lines > 200: prune patterns with count < 3",
        "```",
        "",
        "### For GCL Traces",
        "",
        "```",
        "# When a GCL iteration fails, record the failure pattern:",
        "{",
        '  "failure_pattern": {',
        '    "category": "cli_parameter" | "skill_generation" | "cross_skill" | "runtime" | "token_efficiency",',
        '    "skill": "aws-xxx-ops",',
        '    "command": "aws xxx ...",',
        '    "error": "MissingParameter: ...",',
        '    "fix": "Added correct parameter format",',
        '    "reusable": true | false',
        "  }",
        "}",
        "```",
        "",
    ])

    return "\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="_render_failure_patterns.py",
        description="Render failure-patterns.md from failure-patterns.jsonl",
    )
    base = Path(__file__).parent.parent / "docs"
    ap.add_argument(
        "--jsonl",
        type=Path,
        default=base / "failure-patterns.jsonl",
        help="Path to failure-patterns.jsonl",
    )
    ap.add_argument(
        "--md",
        type=Path,
        default=base / "failure-patterns.md",
        help="Path to output failure-patterns.md",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print to stdout instead of writing file",
    )
    args = ap.parse_args(argv)

    if not args.jsonl.exists():
        print(f"ERROR: {args.jsonl} does not exist — nothing to render", file=sys.stderr)
        return 1

    records = load_jsonl(args.jsonl)
    md = render_markdown(records)

    if args.dry_run:
        sys.stdout.write(md)
        return 0

    args.md.write_text(md, encoding="utf-8")
    print(f"Rendered {len(records)} records → {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
