# Layer 3 — 成熟度文档自动证据快照 (Plan)

> 依据 [`specs/2026-07-27-maturity-snapshot.md`](../specs/2026-07-27-maturity-snapshot.md)。
> 单耦合交付(脚本↔文档↔Makefile 共享契约),按 GCL worktree + 自审执行,不并行 fan-out。

## Phase 1 — Spec

- [x] P0 写 `specs/2026-07-27-maturity-snapshot.md`

## Phase 2 — 实施 (worktree: feature/maturity-snapshot)

- [ ] T1 写 `scripts/status_snapshot.py`(pytest/ruff/composite_lint/self_review 真实采集 + JSON + MD 输出)
  - 验收:A1(合法 JSON)、A2(生成带日期 MD)、A3(红时 all_ok=false)
- [ ] T2 加 `scripts/tests/test_status_snapshot.py`(覆盖解析函数 + 红/绿两条)
  - 验收:A6
- [ ] T3 `Makefile` 加 `status` / `snapshot` target;`ci` 追加 `snapshot`
  - 验收:A5
- [ ] T4 成熟度文档:新增"证据引用"段,弱化静态 "测试全绿" 硬断言
  - 验收:A4

## Phase 3 — Critic + 收尾

- [ ] C1 自审:correctness(safety 无关)/一致性/最小改动/文档同步
- [ ] C2 跑 `make ci`(含 snapshot)全绿;确认 `docs/status-snapshot.md` 真实生成
- [ ] C3 合并 worktree → 删 worktree → 报告证据

## 验收总览

| 验收 | 任务 |
|------|------|
| A1/A3 | T1, T2 |
| A2 | T1 |
| A4 | T4 |
| A5 | T3 |
| A6 | T2 |
