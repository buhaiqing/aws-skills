# Token Efficiency 硬性要求与去重规范（TE Hard Gate）

> 权威定义见根 `AGENTS.md` §14（摘要）。本文件承载完整细节，供 PR review 与 generator 自检引用。
> 与 `aws-skill-generator/SKILL.md` §Token Efficiency Requirements（C6 MUST-PASS）同源。

## 1. 为什么是硬性要求

扫描现状（2026-07-18）：README 规定 `SKILL.md ~70-120 lines`，但存量 34 个 `aws-*-ops` 中绝大多数远超此限（ec2 1015、cloudwatch 1028、cloudtrail 783、dynamodb 782、config 623、ram 608、acm 563、waf 563…）。说明 TE 过去只是 generator 的**声明式声明**，无客观门禁，故在存量中普遍未落实。

**硬性 = 有可 machine-verify 的门槛，而非靠 LLM 自觉。** 任何新 skill / 修改 skill 的 PR，未过以下门槛不得 merge。

## 2. Token Efficiency 客观门槛（C6 硬指标）

| Gate | 硬性标准 | 检查方式 |
|------|----------|----------|
| G1 | `SKILL.md` ≤ 120 行（超长 = 内容未拆到 `references/`） | `[ "$(wc -l < SKILL.md)" -le 120 ]` |
| G2 | 无硬编码静态大表（>5 行且能用 API 查询替代，如引擎版本/端口/配额） | 人工 + LLM 双检（TE-1） |
| G3 | JSON paths 仅在文件顶部集中声明一次，不随每个命令重复 | `awk` 计数声明块（TE-4） |
| G4 | 无跨文件重复流程 / boilerplate（含 GCL 模板正文） | `grep` 重复体（TE-6） |
| G5 | boto3 代码无 docstring，仅 inline comment | 人工 + LLM（TE-2） |
| G6 | 错误表为紧凑表格，非每错误 8-15 行散文 | 人工 + LLM（TE-3） |

**不可压缩内容（即使超 token 也保留）**：Agent 可执行命令本身（参数、JSON paths）、错误恢复逻辑、安全门、Credential 规则、跨技能编排链、AIOps 场景定义。详见 generator §Token Efficiency Requirements 的 "TE Side Effects" 表。

## 3. 去重规范（Dedup as Requirement）

**原则**：任何内容若出现在 ≥2 个 skill，必须抽到单一真相源（single source of truth），禁止复制粘贴。

| 内容类型 | 去重落点 | 先例 |
|----------|----------|------|
| GCL Generator/Critic/Orchestrator 模板 | `aws-skill-generator/references/prompt-skeletons.md`（单一骨架），各 skill 的 `prompt-templates.md` 仅留 service-specific delta | `_sync_prompt_skeletons.py` 将 31 skill 的 ~5,800 行 boilerplate 抽到 231 行骨架 + 薄 delta（-78%） |
| 共享 CLI/SDK 约定 | `aws-skill-generator/references/aws-cli-conventions.md` / `boto3-sdk-usage.md` | 既有 |
| 跨 skill 委托引用 | 通过 CodeGraph（§12）校验引用存在性，删除死引用 | 既有 |
| 重复执行流程（Pre-flight→Execute→Validate→Recover） | 每 skill SKILL.md 仅留该服务特化步骤，通用骨架不复制 | TE-6 |

**去重反模式**：

| 反模式 | 正确做法 |
|--------|----------|
| 在 N 个 skill 复制同一段 GCL/流程/约定 | 抽到共享文件，skill 引用之 |
| 为"省事"复制整段文档而非引用 | 引用路径 + 薄 delta |
| 重复声明已存在于 skeleton 的 Variable Convention | 仅列本 skill 独有 delta |

## 4. 存量整改策略（渐进式）

- **新 skill / 修改 skill**：G1-G6 必须达标，否则不得 merge（generator C6 自检 + 人工 review 双闸）。
- **存量 skill（34 个 `aws-*-ops`）**：允许渐进整改，不强制批量重写（避免破坏已评审内容）。
  - 触发整改的时机：该 skill 被修改、被 CADL 沉淀触及、或被纳入下一轮模板对齐重构时，顺带把 `SKILL.md` 压回 ≤120 行、抽出去重内容。
  - 整改优先级：超长最严重（>500 行）的先处理（ec2/cloudwatch/cloudtrail/dynamodb/config/ram/acm/waf）。
- **去重审计**：每次大改后用 CodeGraph（§12）或 `grep` 扫描跨 skill 重复块，确认无回归。

## 5. 落实机制（Enforcement）

1. **生成时**：`aws-skill-generator` C6 自检跑 §2 的 G1/G3/G4 客观命令，任一失败 HALT→REPORT→FIX→LOOP（见 generator §Token Efficiency Requirements）。
2. **修改时**：PR review 必须核对 G1-G6；reviewer 发现超 120 行或未去重内容，打回。
3. **沉淀时（CADL）**：CADL 提取的资产若与现有内容重复，必须先去重再写入（根 AGENTS.md §13 反模式"重复已有条目"同此理）。
