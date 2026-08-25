#!/usr/bin/env python3
"""Cross-Skill Knowledge Transfer - L4 Gap 5: 37-skill experience sharing.

Each skill currently learns in isolation: a lesson harvested in
``aws-ec2-ops`` never reaches the skills that depend on it. This module
proposes harvested failure-pattern facts to dependent skills and gates
promotion through an adversarial critic (GCL mapping):

- **Generator**: ``harvest_transfer_candidates`` proposes facts downstream
  along ``cross_skill_deps`` edges (knowledge flows source -> dependents).
- **Critic**: ``gcl_gate_transfer`` rejects weak (evidence < min) or
  generic facts; only accepted candidates are promotable.
- **Termination**: every candidate ends ``accepted`` or ``rejected``.

Atomic output: ``audit-results/cross-skill-transfer.json`` (tmp + rename).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_PATTERNS = REPO / "docs" / "failure-patterns.md"
DEFAULT_OUT = REPO / "audit-results" / "cross-skill-transfer.json"

MIN_EVIDENCE = 2
# Generic facts carry no transferable signal unless heavily evidenced.
GENERIC_BLOCKLIST = frozenset({"rate limit", "throttling", "timeout"})

_SKILL_NAME_RE = re.compile(r"aws-[a-z0-9]+(?:-[a-z0-9]+)*-ops")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class TransferCandidate:
    """A fact proposed for transfer from one skill to a dependent skill."""

    source_skill: str
    target_skill: str
    fact: str
    evidence_count: int
    source_refs: list[str] = field(default_factory=list)
    status: str = "pending"  # pending | accepted | rejected


# ---------------------------------------------------------------------------
# Dependency graph
# ---------------------------------------------------------------------------


def _parse_deps(text: str, self_skill: str) -> list[str]:
    """Tolerantly extract dependent skill names after a cross_skill_deps marker.

    Scans from the marker until the next ``## `` heading (or 40 lines,
    whichever first). Unknown formats degrade to an empty list.
    """
    out: list[str] = []
    in_section = False
    scanned = 0
    for line in text.splitlines():
        if not in_section:
            if "cross_skill_deps" in line:
                in_section = True
            continue
        scanned += 1
        if line.startswith("## ") or scanned > 40:
            break
        for match in _SKILL_NAME_RE.finditer(line):
            name = match.group(0)
            if name != self_skill and name not in out:
                out.append(name)
    return out


def load_skill_deps(repo_root: Path) -> dict[str, list[str]]:
    """Parse cross_skill_deps declarations from aws-*-ops/SKILL.md files.

    Returns ``{skill: [skills it depends on]}``; skills without a
    declaration are absent. Missing/empty repo root yields ``{}``.
    """
    deps: dict[str, list[str]] = {}
    if not repo_root.exists():
        return deps
    for skill_md in sorted(repo_root.glob("aws-*-ops/SKILL.md")):
        skill = skill_md.parent.name
        try:
            text = skill_md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        targets = _parse_deps(text, skill)
        if targets:
            deps[skill] = targets
    return deps


# ---------------------------------------------------------------------------
# Generator: propose candidates
# ---------------------------------------------------------------------------


def harvest_transfer_candidates(
    repo_root: Path, patterns: list[dict],
) -> list[TransferCandidate]:
    """Propose each failure-pattern fact to every dependent skill.

    Knowledge flows downstream: a pattern harvested in skill S is proposed
    to every skill T whose cross_skill_deps lists S. Dedup key is
    ``(source_skill, target_skill, fact)``.
    """
    deps = load_skill_deps(repo_root)
    dependents: dict[str, list[str]] = {}
    for skill, targets in deps.items():
        for target in targets:
            dependents.setdefault(target, []).append(skill)

    seen: set[tuple[str, str, str]] = set()
    out: list[TransferCandidate] = []
    for row in patterns:
        source = str(row.get("skill", "")).strip()
        command = str(row.get("command", "")).strip()
        if not source or not command:
            continue
        fix = str(row.get("fix", "")).strip()
        root_cause = str(row.get("root_cause", "")).strip()
        fact = f"{command}: {fix or root_cause}"
        try:
            count = int(row.get("count", 1))
        except (TypeError, ValueError):
            count = 1
        ref = str(row.get("timestamp", "")) or "undated"
        for target in dependents.get(source, []):
            key = (source, target, fact)
            if key in seen:
                continue
            seen.add(key)
            out.append(TransferCandidate(
                source_skill=source,
                target_skill=target,
                fact=fact,
                evidence_count=count,
                source_refs=[ref],
            ))
    return out


# ---------------------------------------------------------------------------
# Critic: adversarial gate
# ---------------------------------------------------------------------------


def gcl_gate_transfer(
    candidate: TransferCandidate, *, min_evidence: int = MIN_EVIDENCE,
) -> TransferCandidate:
    """Adversarial critic gate: weak or generic facts never promote.

    - self-transfer (source == target) -> rejected
    - evidence_count < min_evidence -> rejected
    - generic fact (blocklist hit) needs >= 2x min_evidence
    - otherwise accepted
    """
    if candidate.source_skill == candidate.target_skill:
        candidate.status = "rejected"
        return candidate
    if candidate.evidence_count < min_evidence:
        candidate.status = "rejected"
        return candidate
    fact_lower = candidate.fact.lower()
    generic_hit = any(g in fact_lower for g in GENERIC_BLOCKLIST)
    if generic_hit and candidate.evidence_count < 2 * min_evidence:
        candidate.status = "rejected"
        return candidate
    candidate.status = "accepted"
    return candidate


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def report(candidates: list[TransferCandidate]) -> dict:
    """Aggregate gate outcome into a summary dict."""
    total = len(candidates)
    accepted = sum(1 for c in candidates if c.status == "accepted")
    rejected = sum(1 for c in candidates if c.status == "rejected")
    rate = (accepted / total) if total else 0.0
    return {
        "total": total,
        "accepted": accepted,
        "rejected": rejected,
        "acceptance_rate": round(rate, 4),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="cross_skill_transfer",
        description="L4 Gap 5: cross-skill knowledge transfer (GCL-gated).",
    )
    ap.add_argument("command", choices=["harvest"])
    ap.add_argument("--patterns", default=str(DEFAULT_PATTERNS))
    ap.add_argument("--min-evidence", type=int, default=MIN_EVIDENCE)
    ap.add_argument(
        "--apply", action="store_true",
        help="Write gated candidates to audit-results/cross-skill-transfer.json",
    )
    args = ap.parse_args(argv)

    from runtime_safety import load_failure_patterns

    patterns = load_failure_patterns(Path(args.patterns))
    candidates = harvest_transfer_candidates(REPO, patterns)
    gated = [
        gcl_gate_transfer(c, min_evidence=args.min_evidence)
        for c in candidates
    ]
    payload = {
        "report": report(gated),
        "candidates": [asdict(c) for c in gated],
    }
    if args.apply:
        DEFAULT_OUT.parent.mkdir(parents=True, exist_ok=True)
        tmp = DEFAULT_OUT.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8",
        )
        tmp.replace(DEFAULT_OUT)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
