# FinOps + DevSecOps + AIOps 优化 — 执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **Scope note:** 本 plan 只落地「规范 + 文档」，不实现 F/S/A 优化项。F1–F3 / S1–S3 / A1–A3 是后续独立 plan 的 scope（见文末路线图）。

**Goal:** 将设计文档 `docs/superpowers/specs/2026-07-19-finsecops-optimization-design.md` 的第三条 deliverable 落地——在 `AGENTS.md` 固化「任何非平凡 implement 必须先定义 spec + plan（均置于 `docs/superpowers/` 下）」的仓库纪律。

**Architecture:** 纯文档/规范改动。读取 `AGENTS.md` 现有 Operational Guidelines 小节，在 `### Pre-existing Lint Baseline` 之后追加一个新规范小节；不触碰任何 `aws-*-ops` 技能或 AIOps 脚本。

**Tech Stack:** Markdown、git（仅 commit 本 plan / spec / AGENTS.md）。

**关键事实（已核实磁盘）：**
- 设计文档已落盘：`docs/superpowers/specs/2026-07-19-finsecops-optimization-design.md`（84 行，含已核实证据表 + 三视角机会表 + 窄 scope 边界）
- 既有先例：`docs/superpowers/specs/2026-07-11-level3-coverage-design.md` + 对应 plan（同目录）
- `AGENTS.md` 当前约 526 行；Operational Guidelines 起始于 line 111；`### Pre-existing Lint Baseline` 起始于 line 150
- 仓库纪律：AGENTS.md 软门禁 ≤500 行（§14）；新增小节须精炼（数行），避免行数膨胀

---

## Task: 将 spec+plan-before-implement 固化为 AGENTS.md 规范

**Files:** Modify `AGENTS.md` (Operational Guidelines, 在 `### Pre-existing Lint Baseline` 小节之后插入)

- [ ] **Step 1**: 读取 `AGENTS.md` line 111–145 区域，确认插入锚点（Operational Guidelines 各 subsection 的实际边界与 `### Pre-existing Lint Baseline` 结束位置）。
- [ ] **Step 2**: 在 `### Pre-existing Lint Baseline` 小节之后，新增以下规范小节（保持既有 `###` 标题层级与表格格式一致）：
  ```
  ### Spec + Plan Before Implement (mandatory)

  Any non-trivial implementation MUST first define a spec and a plan under
  `docs/superpowers/` before writing code:

  - **Spec** → `docs/superpowers/specs/<YYYY-MM-DD>-<topic>-design.md`
    （差距/需求分析、已核实证据、scope 边界）
  - **Plan** → `docs/superpowers/plans/<YYYY-MM-DD>-<topic>.md`
    （checkbox 任务、引用对应 spec、给出验证标准）

  **触发条件**（满足任一即需 spec+plan）：
  - 代码/配置/技能改动 > 5 行
  - 新增功能模块
  - 跨文件或跨技能重构

  **豁免**：纯文档 typo 修复、单行常量增补、import 列表更新等纯增量改动。

  **先例**：`docs/superpowers/specs/2026-07-11-level3-coverage-design.md`
  与其 plan 即为本纪律的既有范本——任何新 implement 任务沿用同一路径。
  ```
- [ ] **Step 3**: 校验 markdown 仍合法解析（无断裂表格/未闭合代码块）：
  ```
  awk 'NR>=111 && NR<=170' AGENTS.md   # 目视确认新增小节与上下文结构连贯
  ```
  并确认 `### Pre-existing Lint Baseline` 之后的内容未被吞并。
- [ ] **Step 4**: 校验行数仍在合理范围：`wc -l AGENTS.md` 应接近当前 ~526（新增小节 ≤ 20 行），未触发 §14 软门禁（≤500 行）的硬性溢出风险。
- [ ] **Step 5**: 确认未触碰任何 `aws-*-ops` 技能或 AIOps 脚本：`git diff --stat` 应仅含 `AGENTS.md`（及本 plan / spec）。
- [ ] **Step 6**: commit：`git commit -m "docs(agents): require spec+plan in docs/superpowers before implement"`

---

## 每 Phase / Milestone 收尾：全面 Review + 修复（强制）

> **纪律**：每个 Phase（或 Milestone）的所有任务完成后，必须执行一轮**全面 review**，并**修复所有发现的问题**，方可进入下一 Phase 或交付。不得跳过、不得留待后续。

- [ ] **Step 7 (Phase Review)**: 本 Phase 全部任务（Step 1–6）完成后，执行全面 review：
  - **结构 review**：重读改动后的 `AGENTS.md` 目标小节，确认 markdown 表格/代码块闭合、标题层级连贯。
  - **一致性 review**：确认新增规范与 §11 GCL、§12 CodeGraph、§14 TE 门禁无冲突；与既有 level3 先例路径一致。
  - **scope review**：`git diff --stat` 确认仅含本 spec/plan/AGENTS.md，无 `aws-*-ops` 或 AIOps 脚本被触碰。
  - **门禁 review**：行数未触发 §14 软门禁溢出风险；frontmatter（如有）合法。
- [ ] **Step 8 (Fix & Re-verify)**: 对 Step 7 发现的**每一个**问题逐一修复，修复后复跑对应检查直至零问题；若有残留无法修复项，显式记录并升级人工裁决（不得静默忽略）。
- [ ] **Step 9 (Sign-off)**: 在进度文档（或本 plan 末尾）记录 Phase Review 结论：review 范围、发现问题数、已修复数、残留项（如有）。结论为「clean」方可视为本 Phase 完成。

---

## 后续优化路线图（NOT in scope — 后续独立 plan 执行）

> 以下 F1–F3 / S1–S3 / A1–A3 均来自设计文档 §2，本次 **不实现**，仅作可行动路线图。每一项需各自走「spec + plan 先于 implement」纪律后独立落地。

| id | 描述 | 建议落点 / 目标技能 | 优先级 | 备注 |
|----|------|---------------------|--------|------|
| F1 | 统一 FinOps 技能 | 新建 `aws-cost-ops`（Cost Explorer / Idle 识别 / Rightsize / 预算告警） | P1 | 后续独立 plan，不在本次 scope |
| F2 | 可执行成本优化 runbook | 在 F1 + 现有 elb/eks cost 引用上补 `delete idle LB`/`asg rightsize`（带 GCL 破坏性确认） | P1 | 后续独立 plan，不在本次 scope |
| F3 | 成本异常接入 AIOps | 新增 `COST-SPIKE-01`/`COST-IDLE-01` 推理规则（纯函数 + 单测），delegate `aws-cost-ops` | P2 | 后续独立 plan，不在本次 scope |
| S1 | 预防性安全（shift-left） | 强化 `aws-config-ops` conformance（CIS 基线）或新建 `aws-cis-benchmark-ops` | P1 | 后续独立 plan，不在本次 scope |
| S2 | 密钥泄露扫描 | 新建 `aws-secrets-scanner-ops`（Macie / 代码仓扫描）或扩展 `aws-secretsmanager-ops` | P2 | 后续独立 plan，不在本次 scope |
| S3 | 安全作为 GCL 显式维度 | 在 `governance-review.md` 加 "preventive guard 覆盖高风险资源" 校验 | P2 | 后续独立 plan，不在本次 scope |
| A1 | 消除路由漂移（补 ~20 技能进 AIOps） | 分期补 cruise/orchestrator 路由表 + 对齐 `_inference.py` 规则（外科手术式） | P0 | 后续独立 plan，不在本次 scope |
| A2 | self-heal 能力（受限 fail-closed） | cruise runbook 选 2–3 低风险自愈，强制 GCL + 人工二次确认 | P2 | 后续独立 plan，不在本次 scope |
| A3 | 预测性扩缩容前置 | FORECAST 结果 → delegate `aws-autoscaling-ops` 做 scale 建议（不自动执行） | P3 | 后续独立 plan，不在本次 scope |

---

## 本次验收标准

| 验收项 | 标准 |
|--------|------|
| spec 落地 | `docs/superpowers/specs/2026-07-19-finsecops-optimization-design.md` 存在、含已核实证据表、三视角机会表、scope 边界 |
| plan 落地 | 本文件存在、含 checkbox 任务、引用设计文档 |
| AGENTS.md 规范 | 新增 `### Spec + Plan Before Implement (mandatory)` 小节，要求 implement 前先定义 spec+plan，引用既有 level3 先例 |
| 不回归 | `git diff --stat` 仅含本 spec/plan/AGENTS.md；未触碰任何 `aws-*-ops` 或 AIOps 脚本 |
