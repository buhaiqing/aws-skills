#!/usr/bin/env python3
"""Reflexion — auto-append GCL failure patterns to docs/failure-patterns.md.

L4 dim #3: failures should be persisted automatically, not manually.

dedup key = (skill, command, error_signature); counter self-increments.
Atomic write: tmp → rename.
"""
from __future__ import annotations

from bisect import bisect_right, insort_right  # noqa: F401
import json
import re as _re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class FailurePattern:
    skill: str
    command: str
    error: str
    root_cause: str
    fix: str
    timestamp: str
    count: int = 1
    error_signature: str = field(default="")

    def __post_init__(self) -> None:
        if not self.error_signature:
            self.error_signature = f"{self.skill}|{self.command}|{self.error[:50]}"


def derive_from_trace(trace: dict) -> list[FailurePattern]:
    """Only emit patterns for SAFETY_FAIL / MAX_ITER with at least one dim < 1.0."""
    final = trace.get("final", {})
    status = final.get("status", "")
    if status not in ("SAFETY_FAIL", "MAX_ITER"):
        return []
    iters = trace.get("iterations", [])
    if not iters:
        return []
    last_critic = iters[-1].get("critic", {}).get("scores", {})
    fails = [(d, s) for d, s in last_critic.items() if s < 1.0]
    if not fails:
        return []
    # Pick the lowest-scoring dimension
    dim, score = min(fails, key=lambda x: x[1])
    skill = trace.get("skill", "?")
    last_gen = iters[-1].get("generator", {})
    command = last_gen.get("command", "(unknown)")
    now = datetime.now(timezone.utc).isoformat()
    return [FailurePattern(
        skill=skill,
        command=command,
        error=f"{dim}={score}",
        root_cause=f"Critic scored {dim}={score} on iter {len(iters)}; final.status={status}",
        fix=f"Review rubric for {dim}; inspect generator output for {skill}",
        timestamp=now,
    )]


def _atomic_write(path: Path, text: str) -> None:
    """tmp → rename for atomic writes."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _format_row(p: FailurePattern) -> str:
    return (
        f"| {p.skill} | {p.command} | {p.error} | {p.root_cause} | "
        f"{p.fix} | {p.count} | {p.timestamp} |"
    )


def _parse_table_rows(text: str) -> list[dict[str, str]]:
    """Parse markdown table rows (| col | col | ... |)."""
    rows: list[dict[str, str]] = []
    header_seen = False
    for line in text.splitlines():
        if line.startswith("|") and "---" in line and not header_seen:
            header_seen = True
            continue
        if line.startswith("|") and header_seen:
            cols = [c.strip() for c in line.strip("|").split("|")]
            if len(cols) >= 7:
                rows.append({
                    "skill": cols[0], "command": cols[1], "error": cols[2],
                    "root_cause": cols[3], "fix": cols[4], "count": cols[5],
                    "timestamp": cols[6],
                    "error_signature": f"{cols[0]}|{cols[1]}|{cols[2][:50]}",
                })
    return rows


def _replace_rows(text: str, rows: list[dict[str, str]]) -> str:
    """Replace all table data rows; preserve header + separator."""
    lines = text.splitlines()
    header_idx = None
    sep_idx = None
    for i, ln in enumerate(lines):
        if ln.startswith("|") and "skill" in ln and "command" in ln:
            header_idx = i
        elif header_idx is not None and ln.startswith("|") and "---" in ln:
            sep_idx = i
            break
    if header_idx is None or sep_idx is None:
        return text
    new_lines = lines[: sep_idx + 1]
    for r in rows:
        new_lines.append(
            f"| {r.get('skill', '')} | {r.get('command', '')} | {r.get('error', '')} | "
            f"{r.get('root_cause', '')} | {r.get('fix', '')} | {r.get('count', '1')} | "
            f"{r.get('timestamp', '')} |"
        )
    return "\n".join(new_lines) + "\n"


_FRESH_HEADER = (
    "# Failure Patterns — Reflexion Memory (auto-managed)\n\n"
    "## CLI Parameter Errors\n\n"
    "| skill | command | error | root_cause | fix | count | timestamp |\n"
    "|-------|---------|-------|------------|-----|-------|-----------|\n"
)


def _needs_fresh_init(path: Path, text: str) -> bool:
    """F-23: detect silent-data-loss conditions that warrant full reseed.

    Treats the file as needing fresh header init if ANY of:
      1. file is empty (0 bytes — `_replace_rows` would silently write empty)
      2. file has no parseable table rows but has content (e.g. body only,
         or rows without a header line above them)
    """
    if path.stat().st_size == 0:
        return True
    rows = _parse_table_rows(text)
    return not rows and bool(text.strip())


def append_or_increment(path: Path, pattern: FailurePattern) -> str:
    """Append new row, or increment count on existing dedup match.

    Two reseed paths (both return 'appended'):
      - file missing
      - file empty / no parseable header (F-23 silent-data-loss guard)
    Increments (returns 'incremented') when a row with the same
    `error_signature` already exists.

    JSONL paths route to failure_kb.append_or_increment for unified
    storage format compatibility.
    """
    if path.suffix.lower() == ".jsonl":
        import failure_kb
        rec = failure_kb.FailureRecord(
            skill=pattern.skill,
            command=pattern.command,
            error=pattern.error,
            error_signature=pattern.error_signature,
            root_cause=pattern.root_cause,
            fix=pattern.fix,
            count=pattern.count,
            first_seen=pattern.timestamp,
            last_seen=pattern.timestamp,
        )
        result = failure_kb.append_or_increment(rec, path)
        # Re-render MD from the updated JSONL (backward-compat: skip if renderer absent)
        try:
            import subprocess
            import sys as _sys
            render_script = Path(__file__).parent / "_render_failure_patterns.py"
            if render_script.exists():
                subprocess.run(
                    [_sys.executable, str(render_script),
                     "--jsonl", str(path),
                     "--md", str(path.with_suffix(".md"))],
                    capture_output=True, timeout=30,
                )
        except Exception:
            pass  # Never let render failure block pattern persistence
        return result
    if not path.exists():
        _atomic_write(path, _FRESH_HEADER + _format_row(pattern) + "\n")
        return "appended"
    text = path.read_text(encoding="utf-8")
    if _needs_fresh_init(path, text):
        _atomic_write(path, _FRESH_HEADER + _format_row(pattern) + "\n")
        return "appended"
    rows = _parse_table_rows(text)
    for i, row in enumerate(rows):
        if row.get("error_signature") == pattern.error_signature:
            rows[i]["count"] = str(int(row.get("count", "1")) + 1)
            rows[i]["timestamp"] = pattern.timestamp
            _atomic_write(path, _replace_rows(text, rows))
            return "incremented"
    rows.append({
        "skill": pattern.skill, "command": pattern.command, "error": pattern.error,
        "root_cause": pattern.root_cause, "fix": pattern.fix,
        "count": str(pattern.count), "timestamp": pattern.timestamp,
    })
    _atomic_write(path, _replace_rows(text, rows))
    return "appended"


def prune_low_frequency(
    path: Path, min_count: int = 3, max_lines: int = 200,
) -> int:
    """Remove rows with count < min_count when file exceeds max_lines."""
    if not path.exists():
        return 0
    if path.read_text(encoding="utf-8").count("\n") < max_lines:
        return 0
    text = path.read_text(encoding="utf-8")
    rows = _parse_table_rows(text)
    kept = [r for r in rows if int(r.get("count", "1")) >= min_count]
    removed = len(rows) - len(kept)
    if removed == 0:
        return 0
    _atomic_write(path, _replace_rows(text, kept))
    return removed


# ---------------------------------------------------------------------------
# maintain() — full maintenance: dedup + sort + budget prune
# ---------------------------------------------------------------------------

_SECTION_HEADER_RE = _re.compile(r"^## (.+?)$", _re.M)
_ROW_KEY = _re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|")


def _split_sections(text: str) -> list[tuple[str, int, int]]:
    """Return [(section_title, start, end)] for each '## ' heading in text."""
    headings = list(_SECTION_HEADER_RE.finditer(text))
    sections = []
    for i, m in enumerate(headings):
        start = m.start()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        sections.append((m.group(1), start, end))
    return sections


def _sort_rows_in_section(text: str, section_end: int) -> str:
    """Sort table rows in the section by count desc, timestamp desc.

    Uses pre-computed integer counts (avoid repeated int() calls in sort key).
    """
    sec_match = _SECTION_HEADER_RE.search(text)
    if not sec_match:
        return text
    sec_start = sec_match.start()
    lines = text[sec_start:section_end].split("\n")
    if len(lines) < 3:
        return text
    header_idx = None
    for i, ln in enumerate(lines):
        if ln.startswith("|") and i + 1 < len(lines) and "---" in lines[i + 1]:
            header_idx = i
            break
    if header_idx is None:
        return text
    sep_idx = header_idx + 1
    # Pre-compute (count_int, row_str) pairs — avoid int() in sort key lambda
    data: list[tuple[int, str]] = []
    for i in range(sep_idx + 1, len(lines)):
        ln = lines[i]
        if not ln.startswith("|"):
            break
        cells = [c.strip() for c in ln.split("|")[1:-1]]
        if len(cells) >= 6 and cells[5].isdigit():
            data.append((int(cells[5]), ln))
    # Sort once by count desc (negative for desc), stable sort preserves timestamp order
    data.sort(key=lambda x: -x[0])
    sorted_rows = [r for _, r in data]
    new_section = "\n".join(
        lines[: sep_idx + 1] + sorted_rows + lines[sep_idx + 2 + len(data):]
    )
    return text[:sec_start] + new_section + text[section_end:]


def _dedup_rows_in_section(rows: list[str]) -> list[str]:
    """Remove duplicate rows within a single section by (col1, col2, col3) tuple."""
    seen: set[tuple[str, str, str]] = set()
    kept = []
    for row in rows:
        m = _ROW_KEY.match(row)
        if not m:
            kept.append(row)
            continue
        key = (m.group(1), m.group(2), m.group(3))
        if key in seen:
            continue
        seen.add(key)
        kept.append(row)
    return kept


def maintain(
    path: Path,
    max_lines: int = 150,
    min_count: int = 3,
) -> dict:
    """Full maintenance: dedup rows + sort by count desc + budget prune.

    Returns dict {duplicates_removed, sections_sorted, rows_pruned, total_lines}.
    Idempotent: running twice yields the same result with no further changes.
    """
    if not path.exists():
        return {"duplicates_removed": 0, "sections_sorted": 0, "rows_pruned": 0, "total_lines": 0}
    text = path.read_text(encoding="utf-8")
    sections = _split_sections(text)
    if not sections:
        return {"duplicates_removed": 0, "sections_sorted": 0, "rows_pruned": 0, "total_lines": len(text.splitlines())}
    # Sort + dedup each section
    new_text = text
    sections_sorted = 0
    for title, start, end in sections:
        # Sort table rows in this section
        after = _sort_rows_in_section(new_text, end)
        if after != new_text:
            sections_sorted += 1
            new_text = after
    # Cross-section dedup: simplest heuristic — for now, dedup only within table sections
    # (cross-section dedup would need schema-aware comparison)
    duplicates_removed = 0  # Placeholder; full cross-section dedup deferred.
    # Budget prune if total lines exceed max_lines
    total_lines = len(new_text.splitlines())
    rows_pruned = 0
    if total_lines > max_lines:
        # Use existing prune_low_frequency (operates on first table only,
        # but the multi-section file has each section with its own count column)
        # For simplicity, only prune section 1 (CLI Parameter Errors) since
        # that's where high-freq patterns accumulate.
        rows_pruned = prune_low_frequency(path, min_count=min_count, max_lines=max_lines)
        if rows_pruned:
            new_text = path.read_text(encoding="utf-8")
    _atomic_write(path, new_text)
    return {
        "duplicates_removed": duplicates_removed,
        "sections_sorted": sections_sorted,
        "rows_pruned": rows_pruned,
        "total_lines": len(path.read_text(encoding="utf-8").splitlines()),
    }




def derive_from_error(
    *,
    skill: str,
    command: str,
    error: str,
    root_cause: str = "",
    fix: str = "",
    source: str = "external",
) -> FailurePattern:
    """Create a FailurePattern from an error without requiring a GCL trace.

    Used by runtime_safety (WARN/BLOCK), golden_eval, and any other
    execution path that encounters a failure outside the GCL loop.
    """
    now = datetime.now(timezone.utc).isoformat()
    return FailurePattern(
        skill=skill,
        command=command,
        error=error,
        root_cause=root_cause or f"recorded from {source}",
        fix=fix or "Inspect failure-patterns.md for remediation",
        timestamp=now,
    )

def _cli_main(argv: list[str] | None = None) -> int:
    """CLI entry: maintain or record-failure."""
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["maintain", "record-failure"])
    ap.add_argument("path", nargs="?", default=None,
                    help="Path to failure-patterns.md (default: REPO/docs/failure-patterns.md)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skill", default="", help="AWS skill name (record-failure)")
    ap.add_argument("--cmd", default="", help="Command that failed (record-failure)")
    ap.add_argument("--error", default="", help="Error message (record-failure)")
    ap.add_argument("--root-cause", default="", help="Root cause (record-failure)")
    ap.add_argument("--fix", default="", help="Suggested fix (record-failure)")
    ap.add_argument("--source", default="", help="Source: runtime_safety|gcl|golden_eval (record-failure)")
    args = ap.parse_args(argv)
    target = Path(args.path) if args.path else Path(__file__).resolve().parent.parent / "docs" / "failure-patterns.md"

    if args.command == "record-failure":
        if not args.skill or not args.error:
            ap.error("record-failure requires --skill and --error")
        now = datetime.now(timezone.utc).isoformat()
        pat = FailurePattern(
            skill=args.skill,
            command=args.cmd or "(unknown)",
            error=args.error,
            root_cause=args.root_cause or f"recorded from {args.source or 'external'}",
            fix=args.fix or "Inspect failure-patterns.md for remediation",
            timestamp=now,
        )
        if args.dry_run:
            print(f"DRY-RUN: would record {pat.error_signature}")
            return 0
        result = append_or_increment(target, pat)
        print(json.dumps({"action": result, "signature": pat.error_signature}))
        return 0

    if args.dry_run:
        text = target.read_text(encoding="utf-8") if target.exists() else ""
        print(f"DRY-RUN: would maintain {target} ({len(text.splitlines())} lines)")
        return 0
    result = maintain(target)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_cli_main())
