#!/usr/bin/env python3
"""Memory Retrieval Eval — Session Memory retrieval quality verification.

L4 #10 补全：session_memory 写了但没有机制检验 memory 是否改善了后续决策。
本模块用 GCL 映射验证 memory 检索有效性，并驱动 auto-derive 筛选。

GCL mapping:
- **Generator**: ``retrieve`` — 将 query 与所有 memory record 按
  (keyword overlap × scope match × confidence) 加权排序，返回 top-k 对。
- **Critic**: ``eval_retrieval`` — 对 golden eval cases 评分
  (hit_rate / precision@k / MRR)；``gcl_gate_memory`` 基于检索效果
  衰减低utility记录的 confidence、提升高utility记录，筛选 auto-derive 候选。
- **Termination**: report metrics；``--decay`` 原子写回衰减后的 memory。

Auto-derive 支撑：gate 后 confidence ≥ 0.6 的 records 才有资格作为
``derive_candidates`` 的种子来源（高 utility = 有证据表明该知识影响了决策）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_MEMORY = REPO / ".omc" / "conventions.json"

# Scope relevance tiers: "convention" and "repo-fact" are always relevant;
# "user-pref" and "tool-choice" are query-dependent.
_SCOPE_BOOST: dict[str, float] = {"convention": 1.2, "repo-fact": 1.1}

# Confidence below this after gate → eligible for removal
CONFIDENCE_FLOOR = 0.3
# Confidence above this after gate → auto-derive eligible
AUTO_DERIVE_THRESHOLD = 0.6


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class EvalCase:
    """One labeled retrieval scenario: a query and its known-relevant record IDs."""

    query: str
    relevant_ids: list[str] = field(default_factory=list)


@dataclass
class RetrievalMetrics:
    """Aggregate retrieval quality over a set of eval cases."""

    hit_rate: float = 0.0      # fraction of cases with ≥1 relevant in top-k
    precision_at_k: float = 0.0  # avg (relevant_in_top_k / k)
    mrr: float = 0.0           # mean reciprocal rank of first relevant
    cases_total: int = 0
    cases_with_hit: int = 0


@dataclass
class GateResult:
    """One record's confidence adjustment from the GCL critic gate."""

    record_id: str
    old_confidence: float
    new_confidence: float
    decision: str  # "promote" | "decay" | "unchanged"


# ---------------------------------------------------------------------------
# Generator: scoring retrieval
# ---------------------------------------------------------------------------


def _tokenize(text: str) -> list[str]:
    """Lowercase tokenization; min 2 chars."""
    return [t for t in re.split(r"\W+", text.lower()) if len(t) >= 2]


def retrieve(
    records: list,  # MemoryRecord-like (duck-typed by field names)
    query: str,
    *,
    top_k: int = 3,
) -> list[tuple[object, float]]:
    """Rank records by (keyword_overlap × scope_boost × confidence).

    Returns list of (record, score) pairs sorted desc, length ≤ top_k.
    Score 0 records are excluded.
    """
    q_tokens = _tokenize(query)
    if not q_tokens:
        return []
    scored: list[tuple[float, object]] = []
    for r in records:
        text = " ".join([
            getattr(r, "summary", ""),
            getattr(r, "detail", ""),
            " ".join(getattr(r, "tags", [])),
            getattr(r, "scope", ""),
        ]).lower()
        matched = sum(1 for t in q_tokens if t in text)
        if matched == 0:
            continue
        raw_score = matched / len(q_tokens)
        scope = getattr(r, "scope", "")
        boosted = raw_score * _SCOPE_BOOST.get(scope, 1.0)
        confidence = float(getattr(r, "confidence", 1.0))
        final = boosted * confidence
        scored.append((final, r))
    scored.sort(key=lambda x: (-x[0], getattr(x[1], "id", "")))
    return [(r, s) for s, r in scored[:top_k]]


# ---------------------------------------------------------------------------
# Critic: evaluate retrieval quality
# ---------------------------------------------------------------------------


def eval_retrieval(
    cases: list[EvalCase],
    records: list,
    *,
    top_k: int = 3,
) -> RetrievalMetrics:
    """Score retrieval against labeled golden cases.

    Metrics:
    - **hit_rate**: fraction of cases with ≥1 relevant ID in top-k results
    - **precision@k**: avg (count(relevant in top-k) / k)
    - **MRR**: 1/rank_of_first_relevant (0 if none)
    """
    if not cases:
        return RetrievalMetrics()
    hits = 0
    precisions = []
    rr_sum = 0.0
    for case in cases:
        ranked = retrieve(records, case.query, top_k=top_k)
        ranked_ids = [getattr(r, "id", "") for r, _ in ranked]
        relevant_set = set(case.relevant_ids)
        found = [rid for rid in ranked_ids if rid in relevant_set]
        if found:
            hits += 1
        precisions.append(len(found) / top_k if top_k > 0 else 0.0)
        # MRR: reciprocal rank of first relevant
        rr = 0.0
        for rank, rid in enumerate(ranked_ids, start=1):
            if rid in relevant_set:
                rr = 1.0 / rank
                break
        rr_sum += rr
    n = len(cases)
    return RetrievalMetrics(
        hit_rate=round(hits / n, 4),
        precision_at_k=round(sum(precisions) / n, 4),
        mrr=round(rr_sum / n, 4),
        cases_total=n,
        cases_with_hit=hits,
    )


# ---------------------------------------------------------------------------
# Critic gate: confidence decay / promote
# ---------------------------------------------------------------------------


def _record_retrieval_stats(
    records: list, cases: list[EvalCase], *, top_k: int = 3,
) -> dict[str, dict]:
    """Per-record retrieval stats: times retrieved, times relevant."""
    stats: dict[str, dict] = {
        getattr(r, "id", ""): {"retrieved": 0, "relevant": 0}
        for r in records
    }
    for case in cases:
        ranked = retrieve(records, case.query, top_k=top_k)
        relevant_set = set(case.relevant_ids)
        for r, _ in ranked:
            rid = getattr(r, "id", "")
            if rid in stats:
                stats[rid]["retrieved"] += 1
                if rid in relevant_set:
                    stats[rid]["relevant"] += 1
    return stats


def gcl_gate_memory(
    records: list,
    cases: list[EvalCase],
    *,
    top_k: int = 3,
    decay_rate: float = 0.1,
    promote_boost: float = 0.05,
) -> list[GateResult]:
    """Adversarial critic gate on memory confidence.

    - **never retrieved** (retrieved=0, evidence_count=0) → decay
    - **retrieved but never relevant** (relevant=0) → decay (retrieved but useless)
    - **retrieved + relevant** (relevant ≥ 1) → promote (useful knowledge)
    - **no eval cases provided** → all unchanged (no signal)

    Confidence is clamped to [0.0, 1.0] after adjustment.
    Records below CONFIDENCE_FLOOR after decay are flagged but NOT deleted
    (deletion is a human decision; agent only recommends).
    """
    if not cases:
        return [
            GateResult(
                record_id=getattr(r, "id", ""),
                old_confidence=float(getattr(r, "confidence", 1.0)),
                new_confidence=float(getattr(r, "confidence", 1.0)),
                decision="unchanged",
            )
            for r in records
        ]

    stats = _record_retrieval_stats(records, cases, top_k=top_k)
    results: list[GateResult] = []
    for r in records:
        rid = getattr(r, "id", "")
        old = float(getattr(r, "confidence", 1.0))
        s = stats.get(rid, {"retrieved": 0, "relevant": 0})
        if s["relevant"] > 0:
            new = min(1.0, old + promote_boost)
            decision = "promote"
        elif s["retrieved"] > 0:
            # Retrieved but never relevant — weak signal
            new = max(0.0, old - decay_rate * 0.5)
            decision = "decay"
        elif s["retrieved"] == 0 and len(cases) > 0:
            # Never retrieved across all cases — no utility
            new = max(0.0, old - decay_rate)
            decision = "decay"
        else:
            new = old
            decision = "unchanged"
        results.append(GateResult(
            record_id=rid, old_confidence=old,
            new_confidence=round(new, 4), decision=decision,
        ))
    return results


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def report(
    metrics: RetrievalMetrics, gate_results: list[GateResult],
) -> dict:
    """Aggregate eval report."""
    promoted = sum(1 for g in gate_results if g.decision == "promote")
    decayed = sum(1 for g in gate_results if g.decision == "decay")
    auto_derive_eligible = sum(
        1 for g in gate_results if g.new_confidence >= AUTO_DERIVE_THRESHOLD
    )
    return {
        "retrieval": asdict(metrics),
        "gate": {
            "total": len(gate_results),
            "promoted": promoted,
            "decayed": decayed,
            "auto_derive_eligible": auto_derive_eligible,
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="memory_eval",
        description="L4 #10: verify memory retrieval quality (GCL-gated).",
    )
    sub = ap.add_subparsers(dest="command")

    # eval subcommand
    ev = sub.add_parser("eval", help="Run retrieval eval against golden cases")
    ev.add_argument("--memory", default=str(DEFAULT_MEMORY),
                    help="Path to conventions.json")
    ev.add_argument("--cases", default=None,
                    help="Path to eval-cases.json (list of {query, relevant_ids})")
    ev.add_argument("--top-k", type=int, default=3)
    ev.add_argument("--decay", action="store_true",
                    help="Apply confidence decay/promote to memory file")
    ev.add_argument("--decay-rate", type=float, default=0.1)
    ev.add_argument("--promote-boost", type=float, default=0.05)

    args = ap.parse_args(argv)

    if args.command != "eval":
        ap.print_help()
        return 1

    # Load memory records
    mem_path = Path(args.memory)
    try:
        from session_memory import load_memory, save_memory
    except ImportError:
        print("error: session_memory.py not importable", file=sys.stderr)
        return 1

    records = load_memory(mem_path)
    if not records:
        print(json.dumps({"error": f"no records in {mem_path}"}, indent=2))
        return 0

    # Load eval cases
    cases_path = Path(args.cases) if args.cases else None
    if cases_path and cases_path.exists():
        raw = json.loads(cases_path.read_text(encoding="utf-8"))
        cases = [EvalCase(query=c["query"], relevant_ids=c.get("relevant_ids", []))
                 for c in raw]
    else:
        # Auto-generate cases from records: each record's summary is a query,
        # its own ID is the only relevant result.
        cases = [
            EvalCase(query=r.summary, relevant_ids=[r.id])
            for r in records if r.summary
        ]

    # Run eval
    metrics = eval_retrieval(cases, records, top_k=args.top_k)
    gate_results = gcl_gate_memory(
        records, cases, top_k=args.top_k,
        decay_rate=args.decay_rate, promote_boost=args.promote_boost,
    )
    rep = report(metrics, gate_results)

    # Apply decay if requested
    if args.decay and records:
        id_to_new = {g.record_id: g.new_confidence for g in gate_results}
        for r in records:
            if r.id in id_to_new:
                r.confidence = id_to_new[r.id]
        save_memory(records, mem_path)
        rep["decay_applied"] = True

    print(json.dumps(rep, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
