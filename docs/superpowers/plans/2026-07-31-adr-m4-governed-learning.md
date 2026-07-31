# Plan: ADR-0001 M4 Governed Learning

**Spec:** [`../specs/2026-07-31-adr-m4-governed-learning-design.md`](../specs/2026-07-31-adr-m4-governed-learning-design.md)  
**ADR:** [`docs/adr/0001-l4-production-evidence-loop.md`](../../adr/0001-l4-production-evidence-loop.md) §M4

## Status

- [x] **W0** Spec + Plan
- [x] **W1** `scripts/governed_learning.py` + tests
- [x] **W2** CLI + fixture harvest
- [x] **W3** CI + ADR/maturity Progress

## Waves

### W1 — Core library

- [x] `CandidateRule`, harvest from traces + compensation failures
- [x] `dedupe_rate` / unique queue
- [x] `evaluate_candidate` before/after evidence (offline)
- [x] `approve` / `reject` — approve only path to `failure-patterns.md`
- [x] Assert no auto-promote helper exists as public API that writes patterns without approver

### W2 — CLI

- [x] `harvest --fixtures|--audit-dir`
- [x] `evaluate --queue`
- [x] `approve --id --approver`
- [x] `reject --id`
- [x] `report` (dup rate, auto_promo=0)

### W3 — Docs/CI

- [x] Extend `golden-high-risk.yml` or lint with governed_learning pytest
- [x] ADR §M4 Progress DONE; maturity next closed / post-M4 hygiene
- [x] AGENTS.md ADR blurb

## Non-goals

- AUTO_HEAL expansion
- Auto-write AGENTS.md

## Acceptance

```bash
pytest -p no:rerunfailures scripts/tests/test_governed_learning.py -q
python3 scripts/governed_learning.py report --queue /tmp/gl-queue.json
```

**Verified 2026-07-31**: 12 passed; fixture dup_rate=8%; auto_promotion_rate=0%.
