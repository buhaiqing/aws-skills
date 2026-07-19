# 技能即基础设施（Skill-as-Infrastructure）架构设计 — 设计文档

- **日期**: 2026-07-19
- **状态**: 已定稿（经仓库现状核验 + 用户确认方向）
- **范围**: 定义"复合 / copilot 型 skill"如何叠加在基础 `aws-<svc>-ops` skill 之上，
  保持 Agent Skill 架构不变，并为 OpenClaw / Hermes Agent 等多 agent 运行时集成预留一致入口。
- **方法论**: superpowers spec-driven；本文件为 Spec，后续独立 Plan + Implement。
- **先例**: `docs/superpowers/specs/2026-07-11-level3-coverage-design.md`、
  `docs/superpowers/specs/2026-07-19-finsecops-optimization-design.md`。

## 1. 背景与已核实现状（证据）

本仓库是**扁平的 AWS 运维 runbook 集合**：每个 `aws-<svc>-ops/` 是一个 skill
（Markdown `SKILL.md` + `references/`），**无 manifest / registry / 可执行加载器**，
agent 通过 glob `aws-*-ops/SKILL.md` 读取文件来"调用"。已核实：

| 事实 | 证据 |
|------|------|
| 基础 skill 结构 | `aws-skill-generator/references/aws-skill-template.md`（frontmatter：`name`/`description`/`license`/`compatibility`/`metadata`；强制 `## Trigger & Scope` + `## Variable Convention` + `## Execution Flow Pattern` Pre-flight→Execute→Validate→Recover；破坏性操作需人工确认） |
| 复合 skill **已存在且已打破扁平模式** | `aws-aiops-orchestrator`（`metadata.type: orchestrator-meta`，`cross_skill_deps` 30 个技能）、`aws-aiops-cruise`（`cross-product-aiops-cruise`）、`aws-topo-discovery`（均非 `aws-<svc>-ops` 命名） |
| 委派表达方式 | frontmatter `cross_skill_deps` / `delegate` 块（如 `aws-ec2-ops` 36–47 行）+ body Markdown 引用表（`## Cross-Skill References` / `## Cross-Skill Dependencies`）；**无机器可读路由索引文件** |
| agent 集成机制 | 纯文档式，无配置式 wiring；frontmatter 声明 `runtime: Harness AI Agent, Claude Code, Cursor, or compatible`（`aws-topo-discovery` 21–22 行）；`.opencode/` 仅含 plugin 依赖，无 skill 接线 |
| GCL 附加方式 | 每 skill `metadata.gcl` 块 + `## Quality Gate (GCL)` + `references/rubric.md` + `references/prompt-templates.md`；复合 skill 已自带（如 `aws-aiops-cruise` `class: recommended, max_iter=3`） |
| 设计约束 | `.agents/design.md`："core stays small, extend at edges" |

**关键结论**：用户提出的"copilot 复合 skill 叠加在基础 skill 之前"**不是新架构模式**，
而是对 `aws-aiops-*` 既有做法的**命名化与契约化**。基础架构无需改动。

## 2. 架构主张（Design Propositions）

### P1. 两层技能模型（不变基础 + 复合层）
- **基础层（L1）**：`aws-<svc>-ops`，单一职责、最小能力面（一个服务的运维 runbook）。
- **复合层（L2，即"copilot"）**：`aws-<domain>-*` 或 `aws-<x>-copilot`，**只编排不实现**
  —— 通过 `cross_skill_deps` / `delegate` 引用 L1，自身不含服务级操作逻辑。
- 检索/发现：仍靠 glob 目录约定；L2 在 frontmatter 标 `metadata.type: composite`
  （或 `orchestrator-meta` / `cross-product-*` 已有值），供 agent 区分层级。

### P2. 能力面契约（Capability Surface Contract）
L1 必须暴露**结构化能力声明**，使 L2 可机器组合：
- `metadata.provides`: 该 skill 能处理的操作列表（如 `terminate-instances`,
  `delete-bucket`），取自 `## Execution Flow Pattern` 下的 operation 名。
- `metadata.delegate`: L2→L1 的委派映射（已有雏形，需规范为必填 YAML 块）。
- 此契约写入 `aws-skill-generator/references/aws-skill-template.md`，由 generator 强制。

### P3. Agent 运行时无关（Runtime-Agnostic）
- 因无私有 registry，任何兼容 agent（OpenCode / Claude Code / Cursor /
  OpenClaw / Hermes Agent / Codex）只需：glob `aws-*-ops/SKILL.md` → 读 frontmatter
  → 按 `provides`/`delegate` 路由。**无需 per-agent 适配**。
- 集成方式二选一：(a) 文档式（agent 读 SKILL.md，现状）；(b) MCP 式（如 CodeGraph
  `codegraph_explore` 已落地，§12）——两者并存不冲突。

### P4. GCL 逐层独立
- L1 / L2 各自带 `metadata.gcl` + rubric + prompt-templates；L2 的 rubric 须覆盖
  "委派正确性"（被委派 skill 是否存在、操作是否在其 `provides` 内）。
- 破坏性操作的最终执行仍在 L1，沿用 A1–A16 安全规则与 fail-closed。

## 3. Scope（外科手术式）

**本 Spec 的 deliverable 是架构定义 + 契约规范**，不直接改造现有技能。后续 Plan 落地：

- **改（后续 Plan）**：
  - `aws-skill-generator/references/aws-skill-template.md`：增补 `metadata.provides`
    / `metadata.delegate` / `metadata.type: composite` 契约段。
  - `aws-skill-generator/SKILL.md`：在 generation 流程中强制契约校验（Charter 扩一条）。
  - `AGENTS.md`：新增"复合 / copilot 技能"小节，说明 L1/L2 分层与委派契约。
- **不改**：任何 `aws-<svc>-ops` 业务技能内容、AIOps 脚本、推理规则。
- **不引入**：私有 registry / 加载器 / 运行时专属适配层（违背 P3 与 `.agents/design.md`）。

## 4. 开发顺序（已与用户对齐，优化后）

| 顺序 | 阶段 | 内容 | 状态 |
|------|------|------|------|
| 0 | 基础设施 | Graph MCP 集成（`codegraph install -t opencode`，配置已写入 `~/.config/opencode/opencode.jsonc`，仓库索引 90 文件/595 节点） | ✅ 完成 2026-07-19 |
| 1 | 基础设施 | **本 Spec → Plan → Implement**：技能即基础设施契约（P1–P4），落在 `aws-skill-generator` | 下一步 |
| 2 | 复合层 | 基于契约构建 copilot / 复合 skill（如统一 FinOps/DevSecOps/AIOps 入口） | 待 1 完成后 |
| 3 | 应用层 | FinOps / AIOps / DevSecOps 的 AWS 落地集成（F1–F3 / S1–S3 / A1–A3，见 `2026-07-19-finsecops-optimization-design.md` 路线图） | 最后 |

**为何重排**：原隐含顺序（分析 → 直接 F/S/A 落地）把**应用层置于地基之前**。
正确依赖是 基础设施(0,1) → 复合层(2) → 应用落地(3)，使 F/S/A 有稳定基础层 +
可组合的复合层可插拔。

## 5. 验证标准（本 Spec 落地后，由后续 Plan 执行）

| 验收项 | 标准 |
|--------|------|
| 契约定义 | `aws-skill-template.md` 含 `provides`/`delegate`/`type: composite` 必填段；generator 校验逻辑注明 |
| 分层可识别 | 现有 `aws-aiops-*` 可在 frontmatter 标 `type: composite`，glob 可区分 L1/L2 |
| 运行时无关 | 文档式 + MCP 式集成并存；无私有 registry 依赖 |
| GCL 覆盖 | L2 rubric 含"委派正确性"维度；破坏性终执行仍在 L1 |
| 不回归 | 未改任何业务 skill / AIOps 脚本；`git diff --stat` 仅含 generator 模板 + AGENTS.md |

## 6. 风险与缓解

| 风险 | 缓解 |
|------|------|
| 契约过度设计（为未来扩展引入灵活度） | 仅规范 `provides`/`delegate` 两个最小 YAML 块，不引入通用框架（简单优先） |
| L2 与 L1 职责边界模糊 | P1 明确"L2 只编排不实现"；generator 校验 L2 不含服务级操作 |
| 多 agent 集成 drift | P3 禁止运行时专属适配；集成方式收敛到"读 frontmatter"单一契约 |
| 既有 `aws-aiops-*` 与新契约不一致 | Plan 阶段仅补 `type: composite` 标注，不改其既有 `cross_skill_deps` 逻辑（外科手术） |
