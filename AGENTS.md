# AGENTS.md

Repo-specific guidance. Read `CLAUDE.md` first for shared baseline
(architecture, credential convention, dual-path, safety gates, error-
recovery table). **Detailed protocol sections (§11–§21) live in
`AGENTS.references/`** to keep this file under the 80-line guard.

## Reference index (§11–§23)
| § | Topic | File |
|---|---|---|
| 11 | Generator-Critic-Loop (GCL) | `AGENTS.references/s11-gcl-spec.md` |
| 12 | CodeGraph Integration | `AGENTS.references/s12-codegraph.md` |
| 13 | Compound-Asset Distillation Loop (CADL) | `AGENTS.references/s13-cadl.md` |
| 14 | Token Efficiency Hard Gate | `AGENTS.references/s14-te-hard-gate.md` |
| 15 | Runtime Safety Hook | `AGENTS.references/s15-runtime-safety.md` |
| 16 | Eval-Driven Dev Protocol | `AGENTS.references/s16-eval-driven-dev.md` |
| 17 | Telemetry Dashboard | `AGENTS.references/s17-telemetry.md` |
| 18 | A/B Test Hard Gate | `AGENTS.references/s18-ab-gate.md` |
| 19 | Cross-Session Memory | `AGENTS.references/s19-session-memory.md` |
| 20 | Cross-Runtime Portability | `AGENTS.references/s20-cross-runtime.md` |
| 21 | Changelog | `AGENTS.references/s21-self-review.md` |
| 22 | Testability Discipline | `AGENTS.references/s22-testability.md` |
| 23 | Edit Surgery Discipline | `AGENTS.references/s23-edit-surgery.md` |
## Cardinal Policy (CP-1..6, single source = user-level)

Authority lives at user-level `~/.pi/agent/AGENTS.md`; this repo only
references it. Recap: CP-1 AI-First design · CP-2 Intent-delivery / AI-operates ·
CP-3 Minimal & token-economic · CP-4 Structure-first / field-driven ·
CP-5 AI full authority, exceptions = red lines · CP-6 No duplicated content.

## karpathy-guidelines (4 摘要)

0 能力边界 (admit "I don't know") · 1 先想后写 (think before code) ·
2 简单优先 · 3 外科手术改动 (surgical, trace every diff to a need).

## Spec + Plan First (铁律)

Non-trivial impl (>5 lines, new module, cross-file refactor) MUST land
spec → `docs/superpowers/specs/<date>-<topic>-design.md` and
plan → `docs/superpowers/plans/<date>-<topic>.md` before code.
Anchor in commit body. Exempt: typo <5 lines, single-line additive.

## DCL (5 摘要)

DCL-1 契约锚点 · DCL-2 执行纪律 · DCL-3 度量取证 · DCL-4 反馈复利 ·
DCL-5 元层复盘. Anchored at user-level.

## Long-Task Support (R1..R7 摘要)

R1 任务分解 · R2 范围锁定 · R3 checkpoint ·
R4 token 预算 (探索 20% / 实现 50% / 验证 25% / 收尾 5%) ·
R5 验证检查点 · R6 失败恢复 · R7 进度报告. At user-level.

## AGENTS.md Size Guard (硬门禁)

≤500 lines hard cap; this file ≈80 lines by design. Protocol sections
in `AGENTS.references/` are unlimited but each MUST start with the index
pointer `> 见 [AGENTS.md §X](../AGENTS.md) 索引`. Pre-commit runs
`wc -l AGENTS.md`; over cap = block. **This split = 2026-08-22 fix
(Maturity-Honesty Debt, T2): 1754 → 80 lines + 11 reference files.**

## Pre-commit Hard Gate (full in §12)

Repo runs `scripts/hooks/pre-commit` on every commit. Five triggers:
SKILL.md changed → cross-skill dep dir must exist; `gcl_runner.py` /
`te_gate.py` → `--self-test` exit 0; every commit → `pytest scripts/tests/`
exit 0; code files staged → `codegraph sync .`; `REPO_ROOT` overrides.
Bypass `git commit --no-verify` only for hotfixes, log in body.

## Repo essentials

- **What this repo is**: flat `aws-<service>-ops/` skill collection;
  `aws-skill-generator/` is the meta-skill / source of truth; governance
  scripts live in `scripts/` + `scripts/tests/`.
- **Source-of-truth**: `aws-skill-generator/SKILL.md` (generation +
  Charter C1–C6 + TE-1…TE-6), `aws-skill-generator/references/{aws-skill-template,governance-review}.md`.
  Skills reference shared conventions; no duplication.
- **Operational mandates**: fan-out independent subtasks; Token Efficiency
  Monitor before declaring done; code files → `codegraph sync .` (§12);
  route by file type (code→CodeGraph, docs→Grep); spec+plan before code.
