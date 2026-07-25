# FinOps F-7 暴露真实差距 — 执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现 `scripts/finops_gap_audit.py`，自动诊断 FinOps 能力的真实差距，输出结构化报告。

**Architecture:** 纯 Python 脚本 + 单测。读取仓库文件（SKILL.md frontmatter、references/、scripts/、tests/、_inference.py），按 5 维度评分，输出 JSON/Markdown 报告。

**Tech Stack:** Python 3.10+、PyYAML（frontmatter 解析）、pytest。

**关联 Spec:** `docs/superpowers/specs/2026-07-25-finops-f4-f7-design.md`

---

## Task 1: 实现 finops_gap_audit.py 核心脚本

**Files:** Create `scripts/finops_gap_audit.py`

- [ ] **Step 1**: 创建脚本骨架（argparse + main + 5 个审计函数）
- [ ] **Step 2**: 实现 D1（能力声明 vs 实现）— 解析 `aws-finops-core/SKILL.md` frontmatter `provides`，对比 `references/` 文件
- [ ] **Step 3**: 实现 D2（路由覆盖）— grep orchestrator/cruise SKILL.md 中 `aws-finops-core` 引用
- [ ] **Step 4**: 实现 D3（自动化覆盖）— 检查 `scripts/finops_*.py` 存在性
- [ ] **Step 5**: 实现 D4（测试覆盖）— 检查 `tests/` 中 FinOps 相关测试
- [ ] **Step 6**: 实现 D5（推理规则覆盖）— grep `_inference.py` 中 `COST-*` 规则
- [ ] **Step 7**: 实现 JSON + Markdown 双格式输出 + 退出码逻辑

## Task 2: 编写单测

**Files:** Create `scripts/tests/test_finops_gap_audit.py`

- [ ] **Step 8**: 测试 D1 能力覆盖审计
- [ ] **Step 9**: 测试 D2 路由覆盖审计
- [ ] **Step 10**: 测试 D3 自动化覆盖审计
- [ ] **Step 11**: 测试 D4 测试覆盖审计
- [ ] **Step 12**: 测试 D5 推理规则覆盖审计
- [ ] **Step 13**: 测试 JSON/Markdown 输出格式

## Task 3: 验证与收尾

- [ ] **Step 14**: 运行脚本确认输出正确
- [ ] **Step 15**: 运行单测确认全部通过
- [ ] **Step 16**: 更新 finsecops-optimization-design.md 追加 F4–F7
- [ ] **Step 17**: 自审 2 轮（R1 结构 + R2 内容）

---

## 验收标准

| 验收项 | 标准 |
|--------|------|
| 脚本可运行 | `python3 scripts/finops_gap_audit.py` 输出结构化报告 |
| 5 维度覆盖 | D1–D5 均有评分和差距列表 |
| 双格式输出 | `--format json` / `--format md` 均支持 |
| 退出码 | 有差距 → exit 1；全覆盖 → exit 0 |
| 测试 | ≥ 5 个单测全部通过 |
| 不回归 | 未触碰任何 `aws-*-ops` 技能内容 |
