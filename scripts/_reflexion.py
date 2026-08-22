#!/usr/bin/env python3
"""Reflexion — auto-append GCL failure patterns to docs/failure-patterns.md.

L4 dim #3: failures should be persisted automatically, not manually.

dedup key = (skill, command, error_signature); counter self-increments.
Atomic write: tmp → rename.
"""
from __future__ import annotations

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
    """
    if path.suffix == ".jsonl":
        import failure_kb

        rec = failure_kb.FailureRecord(
            skill=pattern.skill,
            command=pattern.command,
            error=pattern.error,
            error_signature=pattern.error_signature,
            root_cause=pattern.root_cause,
            fix=pattern.fix,
            count=int(pattern.count) if str(pattern.count).isdigit() else 1,
            last_seen=pattern.timestamp,
            first_seen=pattern.timestamp,
        )
        return failure_kb.append_or_increment(rec, path)
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
