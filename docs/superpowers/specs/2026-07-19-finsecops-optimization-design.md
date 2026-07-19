# FinOps + DevSecOps + AIOps 优化机会分析 — 设计文档

- **日期**: 2026-07-19
- **状态**: 已定稿（用户确认，经证据核验）
- **范围**: 对 aws-skills 仓库从 FinOps（成本）、DevSecOps（安全左移）、AIOps（观测/自动化）三个视角做差距分析，并给出可落地的优化项。
- **方法论**: superpowers spec-driven —— 先本设计文档（spec）+ 执行计划（plan），再 implement；本仓库既有先例 `docs/superpowers/specs/2026-07-11-level3-coverage-design.md`。

## 1. 背景与已核实现状

本仓库是扁平的 AWS 运维 runbook 集合：36 个 `aws-<svc>-ops` 技能 + AIOps 层
（`aws-aiops-cruise` / `aws-aiops-orchestrator`）+ 元技能 `aws-skill-generator`。

**已核实事实（grep / 目录 listing 权威统计）**：

| 维度 | 现状 | 证据 |
|------|------|------|
| 技能总数 | 36 个 `aws-*-ops` | `ls -d aws-*-ops \| wc -l` = 36 |
| AIOps inference 委托目标 | 仅 **8** 个技能被 `_inference.py` 路由 | `_inference.py` 中 `delegate_to` 去重 = aws-aurora/aws-dynamodb/aws-elasticache/aws-elb/aws-rds/aws-ssm/aws-vpc/aws-waf |
| cruise 路由表行数 | 27 行 | `aws-aiops-cruise/SKILL.md` grep `aws-.*-ops` = 27 |
| orchestrator 路由表行数 | 91 行 | `aws-aiops-orchestrator/SKILL.md` grep = 91 |
| 专属 FinOps 技能 | **无**（`aws-cost-ops`/`aws-finops-ops` 不存在） | 目录 listing |
| 成本内容分布 | 散落于 elb/eks 的 `cost-*.md` + orchestrator 5 条经济意图 | `aws-elb-ops/references/cost-tracking.md`、`aws-eks-ops/references/cost-optimization.md`、`delegate-routing.md` L234-241 |
| 安全技能 | 强（iam/kms/guardduty/securityhub/secretsmanager/waf/ram/config/cloudtrail） | 目录 listing |
| 安全范式 | **detect→remediate 为主，无 preventive/policy-as-code**（无 CIS、无 secret-scanning、无 IaC conformance） | 各安全 skill 内容复核 |
| AIOps 成熟度 | detect + forecast 存在；**无 self-heal 自动修复代码** | `_inference.py` / `delegate-routing.md` L221-226 FORECAST；无 `self-heal` 实现 |
| inference 规则数 | **47 条** chain-inference 规则 | `aws-aiops-cruise/runbooks/scripts/_inference.py` `apply_chain_inference()` |

**核心矛盾**：36 个技能中，AIOps 实际只把 8 个接进了检测→委托链路；
另有约 20 个技能（含 S3/DynamoDB/CloudFront 等已有规则 ID 却无路由条目的漂移）
完全游离于 AIOps 编排之外。

## 2. 三视角优化机会（按优先级）

### F. FinOps（成本优化）

| # | 机会 | 现状缺口 | 建议落点 | 优先级 |
|---|------|----------|----------|--------|
| F1 | **统一 FinOps 技能 `aws-cost-ops`** | 成本散落于 elb/eks 的 cost-*.md，无集中 runbook；无 RI/Savings Plans/Spot 指导 | 新建技能：Cost Explorer 查询、Idle 资源识别、Rightsize 建议、预算/告警 setup | P1 |
| F2 | **可执行的成本优化 runbook（非纯文本）** | orchestrator 5 条经济意图（Idle LB/NAT/RDS/Aurora/EC）仅 "recommend"，无对应可执行操作 | 在 F1 + 现有 elb/eks cost 引用基础上，补 `delete idle LB`、`asg rightsize` 的 Pre-flight→Execute→Validate→Recover（带 GCL 破坏性确认） | P1 |
| F3 | **成本异常检测接入 AIOps** | `_inference.py` 无 COST-* 规则；orchestrator 有 Cost anomaly 意图但无 inference 实现 | 新增 `COST-SPIKE-01` / `COST-IDLE-01` 规则（纯函数 + 单测），delegate `aws-cost-ops` | P2 |

### S. DevSecOps（安全左移）

| # | 机会 | 现状缺口 | 建议落点 | 优先级 |
|---|------|----------|----------|--------|
| S1 | **预防性安全检查（shift-left）** | 安全技能皆为 detect→remediate，无 preventive/policy-as-code | 在 `aws-config-ops` 基础上强化 conformance（CIS 基线对照），或新建 `aws-cis-benchmark-ops` | P1 |
| S2 | **密钥泄露扫描（secret-scanning）** | 无 secret-scanning 技能；GCL 仅做明文 masking，不主动扫仓库/资源 | 新建 `aws-secrets-scanner-ops`（对接 Macie / 代码仓扫描），或扩展 `aws-secretsmanager-ops` | P2 |
| S3 | **安全作为 GCL 门禁的显式维度** | GCL rubric 有 Safety 维度但偏运行时；缺 "preventive config drift" 检查 | 在 governance-review 加一条 "preventive guard 是否覆盖高风险资源" 校验 | P2 |

### A. AIOps（观测/自动化）

| # | 机会 | 现状缺口 | 建议落点 | 优先级 |
|---|------|----------|----------|--------|
| A1 | **消除路由漂移：补齐 ~20 个技能到 cruise/orchestrator** | 36 技能仅 8 个进 inference 委托；S3/DynamoDB/CloudFront 有规则 ID 却无路由条目 | 分期补路由表 + 对齐 inference 规则（外科手术式，沿用 level3 方案模式） | P0 |
| A2 | **self-heal 能力（受限、fail-closed）** | 无自动修复代码；全部人工确认 | 在 cruise runbook 选 2-3 个低风险自愈（如空闲 LB 标记、告警静默），强制 GCL + 人工二次确认；不自动执行破坏性操作 | P2 |
| A3 | **预测性扩缩容前置** | FORECAST 已支持 CPU/存储/连接数，但未闭环到 `aws-autoscaling-ops` | 预测结果 → delegate `aws-autoscaling-ops` 做 scale 建议（不自动执行） | P3 |

## 3. 本次 scope（外科手术式）

**本设计文档的 deliverable 是「分析 + 规范」**，不直接实现 F1/S1/A1 等大型改造（那是后续独立 plan 的 scope）。本次严格落地的只有：

1. **本 spec**（`docs/superpowers/specs/2026-07-19-finsecops-optimization-design.md`）
2. **对应 plan**（`docs/superpowers/plans/2026-07-19-finsecops-optimization.md`）
3. **AGENTS.md 新增规范**：将 "spec + plan in `docs/superpowers/` 先于 implement" 固化为仓库纪律（用户的明确指令）。

**不改**：任何 `aws-*-ops` 技能内容、AIOps 脚本、推理规则。本任务是纯规范/文档动作。

## 4. 验证标准

| 验收项 | 标准 |
|--------|------|
| spec 落地 | 文件存在、含已核实证据表、三视角机会表、scope 边界 |
| plan 落地 | 文件存在、含 checkbox 任务、引用本 spec |
| AGENTS.md 规范 | 新增一节明确要求 implement 前先定义 spec+plan；给出 `docs/superpowers/{specs,plans}` 路径与既有先例引用 |
| 不回归 | 未触碰任何技能/AIOps 代码；`git diff --stat` 仅含本 spec/plan/AGENTS.md |

## 5. 风险与缓解

| 风险 | 缓解 |
|------|------|
| 优化建议脱离实际（hallucination） | 所有缺口均来自磁盘 grep/目录 listing 核验，非凭记忆 |
| scope 膨胀到实现 F/S/A 改造 | 明确本任务只产规范+文档，实现项列为后续独立 plan |
| AGENTS.md 行数超 §14 软门禁（≤500） | 新增规范精炼，控制在数行；当前 526 行，接近上限，优先复用既有小节 |
