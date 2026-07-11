# Level 3 关联覆盖盲区补全 — 设计文档

- **日期**: 2026-07-11
- **状态**: 已定稿（用户确认）
- **目标等级**: Gartner AIOps 成熟度 Level 3（事件关联 / 部分 AIOps）
- **方案**: 方案 B（按服务分组、分 3 期迭代）

## 1. 背景与问题

本仓库（aws-skills）在 Level 3 的感知与关联主干已建立：

- 7 个 Perceive Agent 多源信号感知
- 14 条 inference rules（CF-/CW-/DG-/RDS-/EBS-/XRAY-）
- `aws-aiops-orchestrator` 跨服务 RCA + 多技能修复编排
- `aws-aiops-cruise` 7 个 runbook（含 self-heal）

**已核实的缺口**（grep 权威统计 + `_inference.py` 源码复核）：34 个 `aws-<svc>-ops` 技能中，
cruise/orchestrator 的**路由元数据表**对以下 8 个完全缺席：

```
aws-athena-ops, aws-cloudfront-ops, aws-dynamodb-ops, aws-eks-ops,
aws-elasticache-ops, aws-opensearch-ops, aws-ram-ops, aws-secretsmanager-ops
```

进一步复核 `_inference.py` 源码发现：inference **检测代码**实际已覆盖其中 4 个
（DynamoDB/ElasticCache/OpenSearch/CloudFront 的规则段已存在），仅路由元数据表缺。
真正**检测代码也缺失**的只有 4 个：**EKS / Athena / RAM / SecretsManager**。

因此分两组处理：
- 路由表：8 个全补（真实缺口）。
- inference 代码：仅补 EKS/Athena/RAM/SecretsManager 4 个；其余 4 个代码已存在，
  只补路由 + 写测试验证现有代码工作（不重复实现）。

## 2. 目标与范围（Scope）

**目标**：消除上述 8 个技能的关联覆盖盲区，补全委托路由 + inference rules。

**范围边界（外科手术式）**：
- **改**：
  - `aws-aiops-cruise/SKILL.md`（Cross-Skill References 表，+8 行）
  - `aws-aiops-orchestrator/SKILL.md`（cross_skill_deps 表，+8 行）
  - `aws-aiops-cruise/references/inference-rules-addendum.md`（新建，Markdown 规则语义）
  - `aws-aiops-cruise/runbooks/scripts/_inference.py`（增补 8 套规则实现 + 单测）
- **不改**：感知层 Perceive Agent 脚本、现有 14 条 inference rules、
  各 `aws-*-ops` 技能自身。
- **不引入**：预测性能力、自愈自动化（后续独立方案）。

## 3. 分期（迭代交付，每期独立 GCL）

| 期 | 技能 | 说明 |
|----|------|------|
| 期 1 | dynamodb, elasticache, opensearch | 数据层三件套，规则模式相似 |
| 期 2 | eks, cloudfront | 计算/边缘，模式不同 |
| 期 3 | athena, ram, secretsmanager | 边缘，规则较薄 |

每期独立：Markdown 规则 → Python 实现 → GCL 评审（≥2 Critic 子 Agent，
`reflect-until-clean`，直到零问题）→ 单测 → commit。

## 4. inference rule 统一规范

每条新增规则遵循与现有 14 条一致的结构，命名 `服务前缀-维度-序号`
（序号避开已有编号，如 CF 已用 -01 则新增用 -02）。

| 技能 | 规则 ID 示例 | 检测维度 |
|------|------------|----------|
| dynamodb | `DYNAMO-THROTTLE-01`, `DYNAMO-GSI-01` | 限流、GSI 热点 |
| elasticache | `EC-MEM-01`, `EC-FAILOVER-01` | 内存压力、故障转移 |
| opensearch | `OS-HEAP-01`, `OS-SHARD-01` | 堆压力、分片不均 |
| eks | `EKS-NODE-01`, `EKS-OOM-01` | 节点 NotReady、OOM |
| cloudfront | `CF-ORIGIN-02`, `CF-CACHE-01` | 源站延迟、缓存命中率 |
| athena | `ATHENA-COST-01` | 查询成本异常 |
| ram | `RAM-SHARE-01` | 资源共享冲突 |
| secretsmanager | `SEC-ROTATE-01` | 密钥轮转过期 |

每条规则 Markdown 语义 + Python 实现一一对应，包含：
- **ID / 名称 / 触发信号**（CloudWatch 命名空间或事件源）
- **判定逻辑**（阈值/模式，纯函数式，便于单测）
- **关联动作**：推荐措施 + 升级路径（指向对应 `aws-*-ops` 委托，不自动写操作）
- **Python 实现**：`_inference.py` 中每规则一个 `detect_*` 函数，
  返回 `{rule_id, severity, evidence, recommend, delegate_to}`

**关键约束**：规则只做"检测 + 推荐 + 升级"，绝不自动执行破坏性操作
（与 self-heal runbook 现有模式及 GCL fail-closed 一致）。

**实现模式（已对齐磁盘现有代码）**：现有 14 条规则全部内联在
`aws-aiops-cruise/runbooks/scripts/_inference.py` 的 `apply_chain_inference()`
单一函数内，按 `resource_type` 分组循环，用 `existing_rule_ids` 开关控制。
新增 8 套规则**沿用此内联模式**（不另起 `detect_*` 函数，避免偏离既有架构）：
每段为 `for rid, metrics in signals.get("<ResourceType>", {}).items():` 循环，
命中阈值则 `make_incident(...)`，字段对齐 `make_incident` 签名
（`rule_id, title, level, metric, current_value, recommendation` 等）。
`resource_type` 统一用大驼峰（DynamoDB / ElastiCache / OpenSearch / EKS /
CloudFront / Athena / RAM / SecretsManager）。

## 5. 路由接入与端到端数据流

### A. 路由表接入（元数据改动）
1. cruise `Cross-Skill References` 表：8 个技能各加一行，格式对齐现有。
2. orchestrator `cross_skill_deps` 表：8 个技能各加一行 `aws-<svc>-ops # <用途>`。

### B. 端到端数据流
```
感知层 (7 Perceive Agents, 不改)
   │  采集 CloudWatch/EventBridge/CloudTrail 信号
   ▼
_inference.py (本期在 apply_chain_inference() 内增补 8 段内联规则)
   │  输入信号 → 匹配规则 ID → make_incident 输出结构化结果
   │  {rule_id, level, metric, current_value, recommendation, delegate_to}
   ▼
cruise runbook / orchestrator
   │  读规则结果，按 delegate_to 路由
   ▼
对应 aws-<svc>-ops (委托执行, 不改)
   │  推荐措施 / 升级 (不自动写操作)
   ▼
人工确认 (GCL fail-closed)
```

新增规则只在 `_inference.py` 与 Markdown 规则表生效，不影响感知层调用方式。

### C. 与 CodeGraph（AGENTS.md §12）协同
新增路由/规则后，改 cruise/orchestrator SKILL.md 时按 §12 用
`codegraph explore` 校验新增 `aws-*-ops` 引用真实存在。

## 6. 测试与验收标准（每期）

| 验收项 | 标准 |
|--------|------|
| 路由表正确性 | cruise + orchestrator 各 +8 行；grep 确认 8 个 `aws-*-ops` 均出现；CodeGraph `explore` 确认目录真实存在 |
| 规则语义完整 | 每套规则含 ID/触发/判定/关联动作四要素 |
| Python 实现 | 每规则在 `apply_chain_inference()` 内一段内联逻辑，走 `make_incident` |
| 单测 | 合成信号验证命中/不命中；`pytest` 全绿 |
| 不回归 | 现有 14 条规则行为不变，现有测试零 failure |
| 不自动执行 | 新增规则无 `modify-/delete-/terminate-` 调用（grep 验证） |
| GCL 评审 | 每期 `reflect-until-clean` 跑通（Generator + ≥2 Critic，直到零问题） |

## 7. 流程纪律（含进度文档）

- 设计文档：本文件 `docs/superpowers/specs/2026-07-11-level3-coverage-design.md`
- 进度文档：`docs/level3-progress.md`，记录每期：范围、起止、改动文件、
  GCL 评审轮次与结论、测试结果
- 每期 commit 前更新进度文档对应段落；期与期之间不积压
- 每期独立 commit + 独立 GCL 评审（AGENTS.md §16.1）

## 8. 风险与缓解

| 风险 | 缓解 |
|------|------|
| `_inference.py` 改动触发 GCL，评审负担集中 | 分期交付，每期仅 2-3 个技能 |
| 规则阈值不合理导致误报 | 纯函数式 + 单测覆盖命中/不命中边界 |
| 编号与现有规则冲突 | 命名时避开已有序号（如 CF-ORIGIN-02） |
| 引用目录不存在 | CodeGraph `explore` 校验 + grep 存在性 |
