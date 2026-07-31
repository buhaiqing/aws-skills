# Plan: Auto Skill Generation (O10 MVP)

**Spec:** [`../specs/2026-08-01-auto-skill-generation-design.md`](../specs/2026-08-01-auto-skill-generation-design.md)  
**Status**: **D0–D3 MVP DONE**（2026-08-01）；pytest 验证通过；**auto merge rate = 0**

## Status

- [x] **D0** Spec + Plan（本文件）
- [x] **D1** `skill_scaffold.py` + tests
- [x] **D2** `skill_gen_gate.py` + optional CI
- [x] **D3** Dry-run + README/maturity 指针

## Waves

### D0 — Design（DONE）

- [x] Goal / non-goals / ServiceSpec / exit criteria
- [x] Align P3.3 research positioning + M4-style human approve
- [x] Pointer from post-m2 backlog D3

### D1 — Scaffold（DONE）

- [x] CLI: `skill_scaffold.py init --spec path.json --out /tmp/...`
- [x] Copy template layout; refuse missing P0 fields
- [x] Hook `_gen_rubric` / prompt-templates when `destructive_ops` non-empty
- [x] Tests: happy path + refuse no docs_url

### D2 — Gate（DONE）

- [x] `skill_gen_gate.py --skill <dir> --strict`
- [x] Wrap `te_gate` + `links_lint` + golden yaml load (≥5)
- [x] Assert auto_merge_rate == 0（无 merge API）

### D3 — Dogfood（DONE）

- [x] One dry-run under `/tmp` or throwaway branch
- [x] Update maturity O10 row when MVP ships
- [x] CADL one-liner if new standing rule emerges

**Verified**: `pytest -p no:rerunfailures scripts/tests/test_skill_scaffold.py scripts/tests/test_skill_gen_gate.py -q`

## Non-goals

- AUTO_HEAL expansion
- Auto-merge main

## Approval gate

D1–D3 已交付。**LLM 填充**仍为人工/agent 步骤；**auto merge rate = 0%** 不变。
