#!/usr/bin/env python3
"""Cross-Session Memory — L4 #10.

Stores agent-derived project facts (preferences, conventions, tool choices)
in `.omc/conventions.json`. Survives session restarts; queryable by keyword.

Contract: `docs/superpowers/specs/2026-07-25-cross-session-memory-design.md`.

CLI:
    python3 scripts/session_memory.py record \\
        --path .omc/conventions.json \\
        --scope convention \\
        --summary "..."

    python3 scripts/session_memory.py query "aws region" --top 5
    python3 scripts/session_memory.py list
    python3 scripts/session_memory.py render --max-chars 2000
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

_VALID_SCOPES = frozenset({"user-pref", "repo-fact", "convention", "tool-choice"})

# Heuristic patterns for derive_candidates (Phase v0)
_DECLARATIVE_PATTERNS = [
    re.compile(r"\b(convention|约定)[:：]\s*(.+)", re.IGNORECASE),
    re.compile(r"\b(always|never)\s+(.+)", re.IGNORECASE),
    re.compile(r"\b(我们用|we use|we always)\s+(.+)", re.IGNORECASE),
    re.compile(r"\b(the rule is|规则是)\s+(.+)", re.IGNORECASE),
    re.compile(r"\b(user prefers?|user wants?)\s+(.+)", re.IGNORECASE),
]


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class MemoryRecord:
    id: str
    timestamp: str
    scope: str
    summary: str
    detail: str = ""
    confidence: float = 1.0
    source_session: str = ""
    tags: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def load_memory(path: Path) -> list[MemoryRecord]:
    """Load records from `.omc/conventions.json`. Empty list if file missing/empty."""
    p = Path(path)
    if not p.exists():
        return []
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    out: list[MemoryRecord] = []
    for r in payload.get("records", []) or []:
        out.append(MemoryRecord(
            id=str(r.get("id", "")),
            timestamp=str(r.get("timestamp", "")),
            scope=str(r.get("scope", "")),
            summary=str(r.get("summary", "")),
            detail=str(r.get("detail", "")),
            confidence=float(r.get("confidence", 1.0)),
            source_session=str(r.get("source_session", "")),
            tags=list(r.get("tags", []) or []),
        ))
    return out


def save_memory(records: list[MemoryRecord], path: Path) -> None:
    """Persist records; atomic write via tmp+rename."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": "1.0.0",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "records": [asdict(r) for r in records],
    }
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    tmp.replace(p)


# ---------------------------------------------------------------------------
# Mutation
# ---------------------------------------------------------------------------

def next_id(records: list[MemoryRecord]) -> str:
    """Return the next sequential id, e.g. mem-007."""
    n = 1
    for r in records:
        if r.id.startswith("mem-") and r.id[4:].isdigit():
            n = max(n, int(r.id[4:]) + 1)
    return f"mem-{n:03d}"


def add_record(records: list[MemoryRecord],
               scope: str, summary: str,
               detail: str = "", confidence: float = 0.6,
               source_session: str = "",
               tags: Iterable[str] = (),
               ) -> MemoryRecord:
    """Append a new MemoryRecord; return the appended record (with new id)."""
    if scope not in _VALID_SCOPES:
        raise ValueError(f"scope must be one of {sorted(_VALID_SCOPES)}; got {scope!r}")
    rec = MemoryRecord(
        id=next_id(records),
        timestamp=datetime.now(timezone.utc).isoformat(),
        scope=scope,
        summary=summary[:300] if len(summary) > 300 else summary,
        detail=detail,
        confidence=max(0.0, min(1.0, confidence)),
        source_session=source_session,
        tags=list(tags),
    )
    records.append(rec)
    return rec


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def query_memory(records: list[MemoryRecord], q: str,
                 top_k: int = 5) -> list[MemoryRecord]:
    """Keyword-based retrieval: token overlap ranking.

    Splits query into lowercase tokens, scores each record by
    (matched tokens / total query tokens), returns top_k sorted desc.
    No result if no overlap.
    """
    q_tokens = [t for t in re.split(r"\W+", q.lower()) if len(t) >= 2]
    if not q_tokens:
        return []

    scored: list[tuple[int, MemoryRecord]] = []
    for r in records:
        text = (r.summary + " " + r.detail + " " +
                " ".join(r.tags) + " " + r.scope).lower()
        matched = sum(1 for t in q_tokens if t in text)
        if matched > 0:
            scored.append((matched, r))
    scored.sort(key=lambda x: (-x[0], x[1].id))
    return [r for _, r in scored[:top_k]]


def format_for_prompt(records: list[MemoryRecord],
                      max_chars: int = 2000) -> str:
    """Render up to `max_chars` worth of records as plain text for prompt injection.

    Always includes the first record; truncates record detail when budget tight.
    """
    lines: list[str] = ["# Project Conventions (auto-loaded)"]
    total = len(lines[0]) + 1
    for r in records:
        line = f"- [{r.scope}] {r.id}: {r.summary}"
        if total + len(line) + 1 > max_chars:
            break
        lines.append(line)
        total += len(line) + 1
        if r.detail and total < max_chars - 80:
            detail_line = f"  ↳ {r.detail[:120]}"
            lines.append(detail_line)
            total += len(detail_line) + 1
    if len(lines) == 1:
        lines.append("(no records)")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Heuristics: derive candidates from session transcript
# ---------------------------------------------------------------------------

def derive_candidates(transcript: list[dict],
                      source_session: str = "unknown") -> list[MemoryRecord]:
    """Heuristic v0: extract declarative sentences matching known patterns.

    Patterns: `convention:`, `always`, `never`, `我们用`, `we use`,
    `the rule is`, `user prefers`. Returns MemoryRecord candidates with
    `confidence=0.6` (advisory, agent reviews before save).
    """
    out: list[MemoryRecord] = []
    seen: set[str] = set()
    for msg in transcript:
        content = (msg.get("content") or "").strip()
        if not content:
            continue
        for pat in _DECLARATIVE_PATTERNS:
            m = pat.search(content)
            if not m:
                continue
            # Whole sentence after the trigger
            sentence = m.group(2).strip()
            # Truncate to 1-2 sentences (rough heuristic)
            sentence = re.split(r"[.;!?。！？]", sentence)[0].strip()
            if len(sentence) < 6 or len(sentence) > 200:
                continue
            if sentence.lower() in seen:
                continue
            seen.add(sentence.lower())
            # Scope heuristic
            sc = "convention"
            lc = sentence.lower()
            if "user" in lc or "prefer" in lc or "want" in lc:
                sc = "user-pref"
            out.append(MemoryRecord(
                id="",  # to be assigned by add_record
                timestamp=datetime.now(timezone.utc).isoformat(),
                scope=sc,
                summary=sentence,
                confidence=0.6,
                source_session=source_session,
                tags=[],
            ))
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="session_memory")
    sub = ap.add_subparsers(dest="cmd", required=True)

    rec_p = sub.add_parser("record",
                           help="Append a new MemoryRecord.")
    rec_p.add_argument("--path", default=".omc/conventions.json")
    rec_p.add_argument("--scope", required=True)
    rec_p.add_argument("--summary", required=True)
    rec_p.add_argument("--detail", default="")
    rec_p.add_argument("--confidence", type=float, default=0.6)
    rec_p.add_argument("--source-session", default="")
    rec_p.add_argument("--tag", action="append", default=[],
                       help="Repeatable; each adds one tag")

    q_p = sub.add_parser("query", help="Keyword search.")
    q_p.add_argument("query_text")
    q_p.add_argument("--path", default=".omc/conventions.json")
    q_p.add_argument("--top", type=int, default=5)

    list_p = sub.add_parser("list", help="List all records.")
    list_p.add_argument("--path", default=".omc/conventions.json")

    render_p = sub.add_parser("render",
                              help="Render as prompt-injectable text.")
    render_p.add_argument("--path", default=".omc/conventions.json")
    vs_p = sub.add_parser("verify-startup",
                           help="Check if conventions.json is from current session.")
    vs_p.add_argument("--path", default=".omc/conventions.json")
    vs_p.add_argument("--required", action="store_true",
                      help="Exit 2 if file is missing entirely (hard requirement).")

    args = ap.parse_args(argv)

    if args.cmd == "record":
        records = load_memory(Path(args.path))
        rec = add_record(records, scope=args.scope, summary=args.summary,
                        detail=args.detail, confidence=args.confidence,
                        source_session=args.source_session,
                        tags=args.tag)
        save_memory(records, Path(args.path))
        print(f"recorded: {rec.id} ({rec.scope}, conf={rec.confidence})")
        return 0

    if args.cmd == "query":
        records = load_memory(Path(args.path))
        hits = query_memory(records, args.query_text, top_k=args.top)
        if not hits:
            print("(no matches)")
            return 0
        for h in hits:
            print(f"[{h.scope}] {h.id} (conf={h.confidence:.2f}) {h.summary}")
            if h.detail:
                print(f"  ↳ {h.detail[:200]}")
        return 0

    if args.cmd == "list":
        records = load_memory(Path(args.path))
        if not records:
            print("(empty)")
            return 0
        for h in records:
            print(f"[{h.scope}] {h.id} {h.summary}")
        return 0
    if args.cmd == "verify-startup":
        p = Path(args.path)
        current_session = os.environ.get("OMC_SESSION_ID", "")
        if not current_session:
            last_session_file = Path(".omc/.last_session")
            if last_session_file.exists():
                current_session = last_session_file.read_text().strip()
        if not p.exists():
            if args.required:
                return 2
            return 1
        records = load_memory(p)
        if not records:
            return 1
        for rec in records:
            if rec.source_session == current_session:
                return 0
        return 1
    if args.cmd == "render":
        records = load_memory(Path(args.path))
        sys.stdout.write(format_for_prompt(records, max_chars=args.max_chars))
        return 0

    ap.error(f"unknown command: {args.cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
