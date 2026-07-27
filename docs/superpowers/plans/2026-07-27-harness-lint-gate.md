# Harness Lint Gate (Layer 1 + Layer 2) — 执行计划 (Plan)

> 依据 [`specs/2026-07-27-harness-lint-gate.md`](../specs/2026-07-27-harness-lint-gate.md)。
> 每个任务带验收点;完成即勾选。按 GCL 规则走 worktree + Generator-Critic loop。

## Phase 1 — Spec 落地

- [x] **P0** 写 `specs/2026-07-27-harness-lint-gate.md`(目标/非目标/设计/验收 A1–A6/风险)

## Phase 2 — 实施 (worktree: feature/harness-lint-gate)

- [ ] **T1** Layer 1:`scripts/hooks/pre-commit` 在文件遍历循环前新增 ruff 全量检查(fail-closed)
  - 验收:A1(注入 error → exit 1)、A2(干净放行)
- [ ] **T2** Layer 2:新增 `scripts/tests/conftest.py` 统一注入 `scripts/` 到 sys.path
  - 验收:A3、A6
- [ ] **T3** 测试覆盖:为 Layer 1 新增 2 条 hook 测试(ruff 缺失→fail;ruff error→fail;干净→pass)
  - 验收:A4(既有 hook 测试仍绿)、新增测试绿
- [ ] **T4** 运行 `make ci`(lint + test + composite-lint + verify)全绿
  - 验收:A5

## Phase 3 — Critic 评审 + 收敛

- [ ] **C1** Critic 按 spec 评审 T1–T4(correctness / safety=fail-closed / 一致性 / 最小改动)
- [ ] **C2** 修复 Critic 指出的 [BLOCKER]/[MAJOR],回归 `make ci`
- [ ] **C3** 主 Agent 收尾:合并 worktree → 删 worktree → 报告证据

## 验收总览

| 验收 | 对应任务 |
|------|----------|
| A1 注入 error 阻断 | T1, T3 |
| A2 干净放行 | T1 |
| A3 pytest 全绿 | T2 |
| A4 既有 hook 测试绿 | T3 |
| A5 make ci 绿 | T4 |
| A6 conftest 零 ruff error | T2 |
