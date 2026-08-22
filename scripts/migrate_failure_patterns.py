#!/usr/bin/env python3
"""Migrate docs/failure-patterns.md (6 sections) -> docs/failure-patterns.jsonl."""
from __future__ import annotations

import argparse
import datetime
import re
from pathlib import Path

from failure_kb import FailureRecord, append_or_increment, export_markdown

CHINESE_HEADER_MAP = {
    "场景": "scene",
    "错误模式": "error_mode",
    "根因": "root_cause",
    "修复": "fix",
    "计数": "count",
}

SECTION_CATEGORY = {
    "1": "cli_parameter",
    "1.5": "query_miss",
    "2": "skill_generation",
    "3": "cross_skill",
    "4": "runtime",
    "5": "token_efficiency",
}

_HEADING_RE = re.compile(r"^##\s+(?:Section\s+)?(\d+(?:\.\d+)?)\b")


def _strip_backticks(s: str) -> str:
    s = s.strip()
    if s.startswith("`") and s.endswith("`") and len(s) >= 2:
        return s[1:-1].strip()
    return s


def _parse_count(raw: str) -> int:
    raw = raw.strip()
    if not raw or raw in {"—", "-", "--", "–"}:
        return 1
    m = re.search(r"\d+", raw)
    if m:
        try:
            return int(m.group(0))
        except ValueError:
            return 1
    return 1


def _clean_cell(v: str) -> str:
    return _strip_backticks(v.strip())


def parse_sections(text: str) -> dict[str, list[dict]]:
    """Parse each section's markdown table into raw rows.

    Returns dict keyed by section id (e.g. "1", "1.5", "2" ...).
    Chinese headers in 1.5 are mapped to English equivalents.
    """
    sections: dict[str, list[dict]] = {}
    current: str | None = None
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        hm = _HEADING_RE.match(line.strip())
        if hm:
            current = hm.group(1)
            # normalize: ensure container exists even if no table follows
            if current not in sections:
                sections[current] = []
            i += 1
            continue
        # table detection: line starting with | and we are inside a section
        if current is not None and line.strip().startswith("|"):
            # collect contiguous table block
            block: list[str] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(lines[i].strip())
                i += 1
            if len(block) >= 2:
                header_cells = [c.strip() for c in block[0].split("|")[1:-1]]
                # map Chinese headers
                mapped_headers: list[str] = []
                for h in header_cells:
                    hs = h.strip()
                    mapped_headers.append(CHINESE_HEADER_MAP.get(hs, hs))
                # second row is separator, skip it
                for row_line in block[2:]:
                    cells = [c.strip() for c in row_line.split("|")[1:-1]]
                    # pad if fewer cells than headers
                    if len(cells) < len(mapped_headers):
                        cells += [""] * (len(mapped_headers) - len(cells))
                    row = {mapped_headers[j]: cells[j] for j in range(len(mapped_headers))}
                    sections[current].append(row)
            continue
        i += 1
    # keep only known sections that were actually defined
    # filter to keys in SECTION_CATEGORY that have entries, but also return all discovered
    # to satisfy the 6-section expectation, ensure keys 1,1.5,2,3,4,5 are present even if empty
    for k in SECTION_CATEGORY:
        sections.setdefault(k, [])
    return sections


def _today_iso() -> str:
    return datetime.date.today().isoformat()


def normalize_to_records(sections: dict[str, list[dict]]) -> list[FailureRecord]:
    """Convert raw rows to unified FailureRecord schema."""
    today = _today_iso()
    records: list[FailureRecord] = []
    seq = 1

    def _next_id() -> str:
        nonlocal seq
        rid = f"fp-{seq:06d}"
        seq += 1
        return rid

    for sec_id in ["1", "1.5", "2", "3", "4", "5"]:
        category = SECTION_CATEGORY[sec_id]
        rows = sections.get(sec_id, [])
        for row in rows:
            # normalize keys lower for flexible matching
            # create lower-key lookup
            lk = {k.lower().strip(): v for k, v in row.items()}
            # helper to get value by possible keys
            def _get(*keys: str) -> str:
                for kk in keys:
                    if kk.lower() in lk:
                        return lk[kk.lower()]
                    # also try exact
                    for rk, rv in row.items():
                        if rk.lower() == kk.lower():
                            return rv
                return ""

            if sec_id == "1":
                skill = _clean_cell(_get("Skill", "skill"))
                command = _clean_cell(_get("Command", "command"))
                error = _clean_cell(_get("Error Pattern", "Error", "error"))
                root_cause = _clean_cell(_get("Root Cause", "root_cause"))
                fix = _clean_cell(_get("Fix", "fix"))
                count = _parse_count(_get("Count", "count"))
                first_seen = today
                last_seen = today
                error_sig = f"{category}|{skill}|{command}|{error}".lower().replace(" ", "-") if error else f"{category}|{skill}|{command}".lower()
            elif sec_id == "1.5":
                scene = _clean_cell(_get("scene", "场景"))
                error_mode = _clean_cell(_get("error_mode", "错误模式"))
                root_cause = _clean_cell(_get("root_cause", "根因"))
                fix = _clean_cell(_get("fix", "修复"))
                count = _parse_count(_get("count", "计数"))
                skill = scene[:64] if scene else "query"
                command = scene
                error = error_mode
                first_seen = today
                last_seen = today
                error_sig = f"{category}|{scene}|{error_mode}".lower().replace(" ", "-")[:120]
            elif sec_id == "2":
                issue_type = _clean_cell(_get("Issue Type", "issue_type", "issue type"))
                frequency = _get("Frequency", "frequency")
                fix_pat = _clean_cell(_get("Fix Pattern", "Fix", "fix_pattern", "fix"))
                first_seen_raw = _clean_cell(_get("First Seen", "first_seen", "first seen"))
                count = _parse_count(frequency)
                skill = "skill-generator"
                command = issue_type
                error = issue_type
                root_cause = issue_type
                fix = fix_pat
                first_seen = first_seen_raw if first_seen_raw else today
                last_seen = today
                error_sig = f"{category}|{issue_type}".lower().replace(" ", "-")[:120]
            elif sec_id == "3":
                src = _clean_cell(_get("Source Skill", "source_skill", "source skill"))
                tgt = _clean_cell(_get("Target Skill", "target_skill", "target skill"))
                failure = _clean_cell(_get("Failure Pattern", "Failure", "failure", "failure pattern"))
                resolution = _clean_cell(_get("Resolution", "resolution"))
                count = _parse_count(_get("Count", "count"))
                skill = src
                command = tgt
                error = failure
                root_cause = failure
                fix = resolution
                first_seen = today
                last_seen = today
                error_sig = f"{category}|{src}|{tgt}|{failure}".lower().replace(" ", "-")[:120]
            elif sec_id == "4":
                skill = _clean_cell(_get("Skill", "skill"))
                operation = _clean_cell(_get("Operation", "operation"))
                failure = _clean_cell(_get("Failure Pattern", "Failure", "failure", "failure pattern"))
                root_cause = _clean_cell(_get("Root Cause", "root_cause"))
                prevention = _clean_cell(_get("Prevention", "prevention"))
                count = 1
                # try count if present
                c_raw = _get("Count", "count")
                if c_raw:
                    count = _parse_count(c_raw)
                command = operation
                error = failure
                fix = prevention
                first_seen = today
                last_seen = today
                error_sig = f"{category}|{skill}|{operation}|{failure}".lower().replace(" ", "-")[:120]
            else:  # sec_id == "5"
                te_rule = _clean_cell(_get("TE Rule", "te_rule", "te rule"))
                violation = _clean_cell(_get("Common Violation", "Violation", "violation", "common violation"))
                fix_v = _clean_cell(_get("Fix", "fix"))
                freq = _get("Frequency", "frequency")
                count = _parse_count(freq)
                skill = te_rule if te_rule else "te"
                command = te_rule
                error = violation
                root_cause = violation
                fix = fix_v
                first_seen = today
                last_seen = today
                error_sig = f"{category}|{te_rule}|{violation}".lower().replace(" ", "-")[:120]

            # ensure non-empty signature
            if not error_sig:
                error_sig = f"{category}|{seq}"

            rec = FailureRecord(
                id=_next_id(),
                category=category,
                skill=skill,
                command=command,
                error=error,
                error_signature=error_sig,
                root_cause=root_cause,
                fix=fix,
                count=count,
                first_seen=first_seen,
                last_seen=last_seen,
                source="manual",
                tags=[],
                vector=None,
            )
            records.append(rec)
    return records


def _is_newer(path_newer: Path, path_older: Path) -> bool:
    try:
        return path_newer.stat().st_mtime > path_older.stat().st_mtime
    except FileNotFoundError:
        return False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="migrate_failure_patterns")
    ap.add_argument("--input", required=True, help="Input markdown path")
    ap.add_argument("--output", required=True, help="Output JSONL path")
    args = ap.parse_args(argv)

    in_path = Path(args.input)
    out_path = Path(args.output)

    if not in_path.exists():
        print(f"input not found: {in_path}")
        return 2

    # idempotent skip
    if out_path.exists() and _is_newer(out_path, in_path):
        print(f"skip: {out_path} is newer than {in_path}")
        return 0

    text = in_path.read_text(encoding="utf-8")
    sections = parse_sections(text)
    records = normalize_to_records(sections)

    # write via append_or_increment atomically (avoid duplicates on re-run)
    # Use direct write for first migration: clear existing then append
    # If output exists but is older, we overwrite
    if out_path.exists():
        out_path.unlink()
    for rec in records:
        append_or_increment(rec, out_path)

    # also generate markdown view via export_markdown
    try:
        md = export_markdown(records)
        md_path = out_path.with_suffix(".md")
        # avoid overwriting input markdown; only write if different path
        if md_path.resolve() != in_path.resolve():
            md_path.write_text(md, encoding="utf-8")
            print(f"markdown view -> {md_path}")
    except Exception as exc:  # noqa: BLE001
        print(f"markdown export warning: {exc}")

    print(f"migrated {len(records)} records -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
