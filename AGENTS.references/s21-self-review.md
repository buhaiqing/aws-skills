> 见 [AGENTS.md §21](../AGENTS.md) 索引

## Changelog

| Date | Change |
|------|--------|
| 2026-07-04 | Added §Operational Guidelines: Task Tracking, GCL Skip Threshold, Pre-existing Lint Baseline |
| 2026-07-11 | Added §12 CodeGraph Integration: local code knowledge graph (colbymchenry/codegraph) for cross-skill reference consistency + blast-radius checks; `codegraph init .` indexed 564 nodes / 1,329 edges |
| 2026-07-18 | Added §13 Compound-Asset Distillation Loop (CADL); wires the extract→decide-landing→write→gate loop into every substantial task; generator injects the CADL hook line into new skills' SKILL.md |
| 2026-07-19 | Added §Operational Guidelines `### Fan-out Subagents (as much as feasible) — MANDATORY`; user hard constraint: fan out independent subtasks to parallel subagents, main Agent only orchestrates+synthesizes, strictly enforced in every subsequent action |
| 2026-07-19 | CodeGraph A/B comparison experiment (spec+plan+record three-piece set, `99adbde`+`f3f66c9`; data-decision commits `d1f0daa`/`4d77f57`): conclusion = route by file type (code files→CodeGraph, non-code docs `.md`/`.yaml`→Grep), not either/or; 5 reviewers unanimously backed the decision. The gate was merged into §12 Mandatory Split Gate and made language-agnostic (tree-sitter covers all supported languages, not just Python) |
| 2026-07-19 | Added §Operational Guidelines `### Token Efficiency Monitor (MANDATORY GATE)`; user hard constraint: every task must pass an independent Token Efficiency Monitor subagent (OPTIMAL / REFACTOR-NOW / ACCEPT-SUBOPTIMAL) before being declared done; strictly enforced from next task |

## 21. Self-Reflection Protocol (L4 #12)

> **Rule**: After every Phase (P0/P1/P2/P3) completes, the main Agent **MUST**
> run the Self-Reflection Protocol via `scripts/self_review.py`. Findings are
> **never** left in chat context — they go to `docs/superpowers/findings/F-NNN-*.md`
> so the next session can learn from them.

### 21.1 Why this exists

L3 closure + P0~P3.2 surfaced 23 findings (F-1 ~ F-23). Most lived only in
chat context — they vanish with the session. **CADL violation** (experience
must compound, not evaporate). §21 makes self-review a **protocol**, not a
one-off gesture.

### 21.2 The 4 finding fields (machine-checkable contract)

Every finding has frontmatter:

| Field | Allowed | Example |
|---|---|---|
| `id` | `F-NNN` (3-digit zero-pad) | `F-001` |
| `severity` | `P0` / `P1` / `P2` | `P0` |
| `status` | `open` / `fixed` / `accepted` | `fixed` |
| `phase` | the Phase that produced it | `l3-closure` |

### 21.3 Severity semantics

| Severity | Meaning | When to use |
|---|---|---|
| `P0` | Block release. Must have a passing test or fix commit before phase closes | Bugs that cause silent data loss (e.g. F-23 0-byte file), or false-positive safety blocks (F-3 substring matcher) |
| `P1` | Process / convention bug. No code fix possible; document the convention | F-1 multi-replace state desync — fix is "always reverse-verify" |
| `P2` | Improvement / hygiene. May stay open across phases | F-23 still open if no follow-up committed |

### 21.4 Protocol — when to run

| Trigger | Required action |
|---|---|
| End of P0 / P1 / P2 / P3 phase | `python3 scripts/self_review.py record ...` for each new finding |
| Before declaring phase "DONE" | `python3 scripts/self_review.py verify` must exit `0` (no stale P0) |
| Before merge to main | `python3 scripts/self_review.py report --phase <id> --out docs/superpowers/reports/<id>.md` |

### 21.5 CLI cheat-sheet

```bash
# Record a finding (auto-increment id, write .md file)
python3 scripts/self_review.py record \
    --severity P0 --title "..." --root-cause "..." \
    --fix "..." --lesson "..." --phase <phase-id>

# List all P0 (or any severity)
python3 scripts/self_review.py list --severity P0

# Verify — exit 0 iff no stale P0
python3 scripts/self_review.py verify

# Generate phase-level Markdown report
python3 scripts/self_review.py report --phase l4-closure \
    --out docs/superpowers/reports/l4-closure.md
```

### 21.6 Reverse-verification principle (the F-1 lesson)

Any time the Agent does multi-step file mutation (heredoc, sed, multi-replace),
**the protocol demands a reverse-verify step at the end**:

1. `git grep` for stale markers
2. `pytest` to confirm tests still pass
3. `ruff check` for new lint regressions

If any reverse-verify fails, the previous mutations are **untrusted** — re-run
them in a fresh `exec_command`. This is the F-1 lesson codified.

### 21.7 Worked example (F-3 record)

```bash
python3 scripts/self_review.py record \
    --severity P0 \
    --title "runtime_safety substring matcher" \
    --root-cause "substring match of terminate-instances also hits describe-instances" \
    --fix "switch to token-level regex \\b\\b in runtime_safety.detect_destructive()" \
    --lesson "destructive-op detection must use regex word boundary, never str.find()" \
    --phase l3-closure
# → writes docs/superpowers/findings/F-001-runtime-safety-substring-matcher.md
# → returns "F-001"
```

### 21.8 Cross-references

- §13 CADL — findings are CADL artifacts (experience must compound)
- §11 GCL — GCL `SAFETY_FAIL` and `MAX_ITER` MUST auto-record as P0 finding
  via `_reflexion.append_or_increment` integration (already wired in P1)
- §16 Eval-Driven Dev — golden scenarios that fail repeatedly must record a P2 finding

### 21.9 Final closure archive

The full L3 → L4 closure process is archived at
[`docs/superpowers/reports/l4-final.md`](docs/superpowers/reports/l4-final.md).
That document contains the complete timeline, phase-by-phase deliverables,
tooling stack, patch inventory, codified findings, and verification commands.
Future agents reproducing or auditing the L4 closure should start there.
