---
id: F-006
severity: P2
title: 10-patch sequence creates overlapping file diffs
status: open
added: 2026-07-26
closed:
phase: l4-98-consolidation
---

## Root cause

Final consolidation (2026-07-26) shows 5 files modified by multiple patches in
the 10-patch sequence:

- `AGENTS.md` (8 patches: l3-p1 → p3-4)
- `TODO.md` (10 patches: ALL of them)
- `docs/agentic-maturity-model.md` (10 patches: ALL of them)
- `docs/superpowers/findings/F-005-*.md` (2 patches)
- `scripts/golden_eval.py` (2 patches: p2-2 + p2-3)

Each phase appends rows to TODO.md + maturity-model.md, forcing re-diff of the
entire file. Acceptable for sandbox-out apply (consolidated mega-patch handles
it correctly), but creates 8-10x churn in any git history that applies
patches individually.

## Fix (recommended, not blocking)

For future phases:
1. Avoid appending to shared changelog files in every patch — consolidate
   changelog updates into a single end-of-phase patch
2. Document in AGENTS.md §21 that "consolidated patch" is the canonical
   artifact; individual phase patches are for archival

## Lesson

Cross-cutting artifacts (changelog, TODO, maturity-model) accumulate diffs
across every phase. Either consolidate changelog updates into a single
end-of-phase patch, OR rely on a final consolidated patch for clean apply.
For this repo, the `l4-98-consolidated.patch` mega-patch captures the final
state and is the canonical apply path.
