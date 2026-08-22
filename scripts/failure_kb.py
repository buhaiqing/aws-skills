#!/usr/bin/env python3
"""P0 Failure Knowledge Base — unified JSONL store with lexical retrieval."""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path

CATEGORIES = frozenset({
    "cli_parameter", "query_miss", "skill_generation",
    "cross_skill", "runtime", "token_efficiency",
})
SOURCES = frozenset({
    "gcl_trace", "self_review", "runtime_block", "manual", "governed_learning",
})

_WEIGHTS = {"command": 3.0, "error": 3.0, "skill": 2.0, "root_cause": 2.0, "fix": 1.0}
_TOKEN_RE = re.compile(r"\w+")


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


@dataclass
class FailureRecord:
    id: str = ""
    category: str = "cli_parameter"
    skill: str = ""
    command: str = ""
    error: str = ""
    error_signature: str = ""
    root_cause: str = ""
    fix: str = ""
    count: int = 1
    first_seen: str = ""
    last_seen: str = ""
    source: str = "manual"
    tags: list[str] = field(default_factory=list)
    vector: list[float] | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> FailureRecord:
        fields = {f.name for f in cls.__dataclass_fields__.values()}
        kwargs = {k: v for k, v in data.items() if k in fields}
        # defaults for missing keys
        kwargs.setdefault("count", 1)
        kwargs.setdefault("tags", [])
        kwargs.setdefault("vector", None)
        return cls(**kwargs)  # type: ignore[arg-type]


def load_jsonl(path: Path | str) -> list[FailureRecord]:
    p = Path(path)
    if not p.exists():
        return []
    text = p.read_text(encoding="utf-8")
    if not text.strip():
        return []
    records: list[FailureRecord] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {idx}: {exc}") from exc
        records.append(FailureRecord.from_dict(data))
    return records


def _next_id(existing: list[FailureRecord]) -> str:
    max_n = 0
    for r in existing:
        m = re.match(r"^fp-(\d{6})$", r.id)
        if m:
            max_n = max(max_n, int(m.group(1)))
    return f"fp-{max_n + 1:06d}"


def _atomic_write(path: Path, records: list[FailureRecord]) -> None:
    tmp = Path(str(path) + ".tmp")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(json.dumps(r.to_dict(), ensure_ascii=False) for r in records)
    if content:
        content += "\n"
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def append_or_increment(
    records: list[FailureRecord] | FailureRecord,
    path: Path | str,
    *_extra,
) -> str:
    # Flexible signature: support (records, path) or (record, path) or (path, record)
    # Detect swapped args
    if isinstance(records, (str, Path)) and isinstance(path, (FailureRecord, list)):
        records, path = path, records  # type: ignore[assignment]
    target = Path(path)  # type: ignore[arg-type]
    if isinstance(records, FailureRecord):
        incoming: list[FailureRecord] = [records]
    elif isinstance(records, list) and records and isinstance(records[0], FailureRecord):
        incoming = records  # type: ignore[assignment]
    else:
        incoming = list(records)  # type: ignore[arg-type]

    existing = load_jsonl(target) if target.exists() else []
    by_sig: dict[str, FailureRecord] = {r.error_signature: r for r in existing}
    result = "appended"

    for rec in incoming:
        # auto-generate id if empty
        if not rec.id or not re.match(r"^fp-\d{6}$", rec.id):
            rec.id = _next_id(list(by_sig.values()) + incoming)
        if rec.error_signature in by_sig:
            prev = by_sig[rec.error_signature]
            prev.count = int(prev.count) + int(rec.count) if rec.count else int(prev.count) + 1
            # update last_seen if provided
            if rec.last_seen:
                prev.last_seen = rec.last_seen
            result = "incremented"
        else:
            by_sig[rec.error_signature] = rec
            # result stays appended unless already incremented

    merged = sorted(by_sig.values(), key=lambda r: r.id)
    _atomic_write(target, merged)
    # determine final result: if any incoming was duplicate → incremented
    # check if incoming sig existed in original existing
    existing_sigs = {r.error_signature for r in existing}
    if any(r.error_signature in existing_sigs for r in incoming):
        return "incremented"
    return result if len(incoming) == 1 and result == "incremented" else "appended"


def search_lexical(
    query: str,
    records: list[FailureRecord],
    k: int = 5,
) -> list[FailureRecord]:
    q_tokens = _tokenize(query)
    if not q_tokens:
        return []
    scored: list[tuple[float, FailureRecord]] = []
    for rec in records:
        score = 0.0
        for tok in q_tokens:
            if tok in _tokenize(rec.command):
                score += _WEIGHTS["command"]
            if tok in _tokenize(rec.error):
                score += _WEIGHTS["error"]
            if tok in _tokenize(rec.skill):
                score += _WEIGHTS["skill"]
            if tok in _tokenize(rec.root_cause):
                score += _WEIGHTS["root_cause"]
            if tok in _tokenize(rec.fix):
                score += _WEIGHTS["fix"]
        if score > 0:
            scored.append((score, rec))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:k]]


def export_markdown(records: list[FailureRecord]) -> str:
    header = "# Failure Patterns (AUTO-GENERATED — DO NOT EDIT)\n\n"
    header += "> Generated from failure_kb JSONL — do not edit manually.\n\n"
    grouped: dict[str, list[FailureRecord]] = defaultdict(list)
    for r in records:
        grouped[r.category].append(r)
    if not records:
        return header + "_No records._\n"
    parts: list[str] = [header]
    for cat in sorted(grouped):
        rows = sorted(grouped[cat], key=lambda r: r.id)
        parts.append(f"## {cat}\n\n")
        parts.append("| id | skill | command | error | root_cause | fix | count | source |\n")
        parts.append("|----|-------|---------|-------|------------|-----|-------|--------|\n")
        for r in rows:
            parts.append(
                f"| {r.id} | {r.skill} | {r.command} | {r.error} | "
                f"{r.root_cause} | {r.fix} | {r.count} | {r.source} |\n"
            )
        parts.append("\n")
    return "".join(parts)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="failure_kb")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ex = sub.add_parser("export", help="Export JSONL to markdown")
    ex.add_argument("--input", required=True, help="Input JSONL path")
    ex.add_argument("--output", required=True, help="Output markdown path")
    args = ap.parse_args(argv)
    if args.cmd == "export":
        recs = load_jsonl(Path(args.input))
        md = export_markdown(recs)
        Path(args.output).write_text(md, encoding="utf-8")
        print(f"exported {len(recs)} records → {args.output}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
