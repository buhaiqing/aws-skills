# Reflexion Staleness Implementation Plan

> For agentic workers. **Spec is the single source of truth** (CP-6): see
> `docs/superpowers/specs/2026-09-24-reflexion-staleness-design.md` — §4 Implementation, §5 Verification, §6 Tests.
> This plan records task slicing + DoD only; no content duplicated.

**Goal:** G1 `check-reflexion-freshness` CLI (stale JSONL → exit 1) + G2 item-level
staleness flagging + G3 zero regression on existing 4 tests.

| Task | Scope (spec C1) | DoD | Status |
|---|---|---|---|
| T1 | `self_review.py` §4.1 freshness subcommand | 4 new tests green; Gate 1/2 (stale=1, fresh=0) | [x] |
| T2 | `self_review.py` §4.2 item-level scan | 2 new + 4 original green; Gate 3 flags §6.3 | [x] |
| T3 | `test_rubric_completeness.py` worktree-safe glob (C5) | 96 rubric cases green in worktree | [x] |
| T4 | GCL + gates | 3 critics satisfied; pytest 577; ruff clean | [x] |

**GCL trace:** `audit-results/gcl-trace-2026-09-25-reflexion-staleness.json` (decision `dec-f52623aa0496`).
