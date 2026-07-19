# 技能即基础设施（Skill-as-Infrastructure）契约 — 执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **Scope note:** 本 plan 只落地基础设施第 1 步——在 `aws-skill-generator` 中固化"复合 / copilot 技能"契约（P1–P4，见对应 Spec）。**不实现**任何业务技能或 F/S/A 落地（那是顺序第 2、3 步）。

**Goal:** 在 `aws-skill-generator` 的模板与生成流程中，增补最小契约
（`metadata.type: composite` / `metadata.provides` / `metadata.delegate`），使复合层技能可机器识别、可组合，且对所有 coding agent 运行时无关。

**Architecture:** 纯模板 + 生成流程 + AGENTS.md 文档改动。复用既有 frontmatter
`metadata:` 块与 Charter C1–C6 自检框架；新增契约作为 C 系列之后的"分层契约"校验，
不引入私有 registry / 加载器（违背 Spec P3）。

**Tech Stack:** Markdown（模板/文档）、grep/sed 校验、git。

**关键事实（已核实磁盘）：**
- 模板 frontmatter：`aws-skill-generator/references/aws-skill-template.md` 1–21 行，`metadata:` 含 author/version/last_updated/runtime/cli_applicability/environment。
- Charter 自检表：`aws-skill-generator/SKILL.md` 91–103 行（C1–C6），C6 为 MUST-PASS 硬门禁。
- GCL frontmatter 模板：`aws-skill-generator/SKILL.md` 314–336 行（`metadata.gcl` block）。
- 既有复合 skill 已用 `metadata.type: orchestrator-meta` / `cross-product-*`（`aws-aiops-orchestrator` / `aws-aiops-cruise` / `aws-topo-discovery`），本契约将其统一为可选值 `composite`。
- AGENTS.md 当前 557 行，§14 软门禁 ≤500（溢出源为 §11 GCL 表，本 plan 新增小节须精炼）。

---

## Task 1: 模板增补分层契约段

**Files:** Modify `aws-skill-generator/references/aws-skill-template.md` (frontmatter `metadata:` 块, ~14–21 行)

- [ ] **Step 1**: 在 `metadata:` 块内、`environment:` 之后追加契约字段（对齐现有缩进）：
  ```
  metadata:
    author: aws
    version: "1.0.0"
    last_updated: "2026-05-10"
    runtime: Harness AI Agent
    cli_applicability: dual-path
    type: base            # base | composite  —— 复合/copilot 技能填 composite
    provides:             # 本 skill 能处理的操作列表（取自下方 Execution Flow 的 operation 名）
      - "<operation-1>"
      - "<operation-2>"
    delegate:             # 仅 composite 填：委派的下游 skill → 操作映射
      aws-<svc>-ops:
        - "<operation>"
    environment:
      - AWS_ACCESS_KEY_ID
      ...
  ```
- [ ] **Step 2**: 在模板 body（frontmatter 之后、`## Overview` 之前或 `## Trigger & Scope` 附近）补一段简短说明，解释 `type/provides/delegate` 语义与 L1(base)/L2(composite) 分层，一段话即可（不超过 8 行，守 TE-6/简单优先）。
- [ ] **Step 3**: 校验 frontmatter 仍单块合法：`awk '/^---$/{c++; if(c==2)exit} c==1' aws-skill-generator/references/aws-skill-template.md | head -1` 应为 `---`，且 YAML 可解析（用 `python3 -c "import yaml,sys; yaml.safe_load(open(...))"` 校验 frontmatter 段）。
- [ ] **Step 4**: commit `git commit -m "docs(generator): add base/composite skill contract to template"`

---

## Task 2: 生成流程强制契约校验（Charter 扩展）

**Files:** Modify `aws-skill-generator/SKILL.md` (Charter Compliance Checklist, ~91–103 行)

- [ ] **Step 1**: 在 C6 之后新增一行 **C7（分层契约，仅 composite 必填）**：
  ```
  | C7 | 分层契约 | 若 metadata.type == composite，则必含 delegate 且 delegate 指向的 aws-<svc>-ops 目录真实存在；base 技能可选填 provides | composite 缺失则 HALT 报告 |
  ```
- [ ] **Step 2**: 在 `## Skill metadata`（~401 行）的 `{{skill.*}}` 占位符表下方，补 3 行说明 `{{skill.type}}` / `{{skill.provides}}` / `{{skill.delegate}}` 取自 frontmatter（供 prompt-templates 引用，保持与现有 `{{skill.max_iter}}` 同模式）。
- [ ] **Step 3**: 确认不改动 C1–C6 既有逻辑（外科手术）；grep 确认 C7 仅追加、未删改现有行。
- [ ] **Step 4**: commit `git commit -m "docs(generator): enforce base/composite contract in Charter (C7)"`

---

## Task 3: AGENTS.md 新增复合技能小节

**Files:** Modify `AGENTS.md` (Operational Guidelines 区域，紧邻 "### Per-Phase / Milestone Full Review (mandatory)" 之后，或 §11 GCL 之前；新增精炼小节)

- [ ] **Step 1**: 在合适锚点后插入（≤15 行）：
  ```
  ### Composite / Copilot Skills (L2)

  Base skills (`aws-<svc>-ops`, L1) are single-service runbooks. Composite
  skills (L2, `metadata.type: composite`) **orchestrate only** — they declare
  `delegate:` to L1 skills and contain no service-level operation logic.

  Contract (enforced by aws-skill-generator Charter C7):
  - `metadata.type`: `base` | `composite`
  - `metadata.provides`: operations this skill handles
  - `metadata.delegate`: composite→base skill/operation map (dirs must exist)

  Runtime-agnostic: any agent globs `aws-*-ops/SKILL.md` and reads frontmatter
  — no per-agent loader (see §12 CodeGraph for cross-agent MCP discovery).
  ```
- [ ] **Step 2**: 校验 markdown 表格/代码块闭合、标题层级连贯（`###` 在 `##` 下）。
- [ ] **Step 3**: 校验行数未触发 §14 硬溢出风险：`wc -l AGENTS.md` 应 ≤ ~575（本次新增 ≤15 行）。
- [ ] **Step 4**: commit `git commit -m "docs(agents): document composite/copilot skill layering + contract"`

---

## Task 4: 每 Phase 全面 Review + 修复（强制，按 AGENTS.md 新规范）

- [ ] **Step 1 (Review)**: 重读 Task 1–3 改动的三个文件；确认：
  - 模板 frontmatter 合法（Step 3 的 yaml 解析通过）；
  - C7 仅追加、C1–C6 未动；
  - AGENTS.md 新小节结构与 §11/§12/§14 无冲突；
  - `git diff --stat` 仅含 3 个目标文件，无业务 skill / AIOps 脚本被触碰。
- [ ] **Step 2 (Fix)**: 对发现的每个问题修复，复跑对应检查至零问题。
- [ ] **Step 3 (Sign-off)**: 记录 review 结论（scope / found / fixed / residue），结论为 clean 方视为本 Phase 完成。
- [ ] **Step 4**: 无需额外 commit（修复已在 Task 1–3 的 commit 中或补一个 `git commit -m "fix(generator/agents): address phase review findings"`）。

---

## 本次验收标准

| 验收项 | 标准 |
|--------|------|
| 契约定义 | 模板 `metadata` 含 `type`/`provides`/`delegate`；`python3 yaml.safe_load` 解析 frontmatter 通过 |
| 分层可识别 | `aws-skill-generator/SKILL.md` 新增 C7；composite 必填 delegate 且目录存在性可查 |
| 运行时无关 | AGENTS.md 明确"glob + 读 frontmatter，无 per-agent loader" |
| 不回归 | `git diff --stat` 仅含 `aws-skill-generator/references/aws-skill-template.md` + `aws-skill-generator/SKILL.md` + `AGENTS.md` |
| 门禁 | C6（≤120 行 SKILL.md）不受影响；AGENTS.md 行数未硬溢出 §14 |
