# Level 3 关联覆盖盲区补全 — 进度文档

- **设计文档**: `docs/superpowers/specs/2026-07-11-level3-coverage-design.md`
- **创建日期**: 2026-07-11
- **总目标**: 补全 8 个未接入技能（athena/cloudfront/dynamodb/eks/elasticache/opensearch/ram/secretsmanager）的委托路由 + inference rules，分 3 期迭代，每期 GCL 评审。

## 关键事实校准（实施中发现）

复核 HEAD 原始 `_inference.py` 后确认：
- 路由元数据表（cruise/orchestrator SKILL.md）对 8 个技能全部缺席 → **路由表全补（真实缺口）**。
- inference 检测代码在 HEAD 已覆盖：DYNAMO-THROTTLE-01、EC-MEM-01（及 EC-CPU/CONN/EVICT）、大量 CF-*、RDS-*、Aurora-* 等。
- **真正缺失的 inference 规则**：DYNAMO-GSI-01、EC-FAILOVER-01、OpenSearch 全段（OS-HEAP/OS-SHARD）、EKS 全段、Athena、RAM、SecretsManager。

因此每期工作量调整为"路由全补 + 仅补真实缺失的 inference 代码"，不重复实现已有规则。

## 分期总览

| 期 | 技能 | 状态 | GCL 轮次 | 测试结果 |
|----|------|------|----------|----------|
| 期 1 | dynamodb, elasticache, opensearch | 实现完成，GCL 评审中 | 1 (进行) | pytest 45 passed |
| 期 2 | eks, cloudfront | 待开始 | - | - |
| 期 3 | athena, ram, secretsmanager | 待开始 | - | - |

## 期 1 详情

- **范围**: 路由全 8 技能 + inference 补 DYNAMO-GSI-01 / EC-FAILOVER-01 / OS-HEAP-01 / OS-SHARD-01
- **改动文件**:
  - `aws-aiops-cruise/SKILL.md`（Cross-Skill References +8 行）
  - `aws-aiops-orchestrator/SKILL.md`（cross_skill_deps +8 行）
  - `aws-aiops-cruise/references/inference-rules-addendum.md`（新建，全 8 技能规则语义 + 实现状态表）
  - `aws-aiops-cruise/runbooks/scripts/_inference.py`（+4 段规则：DYNAMO-GSI-01/EC-FAILOVER-01/OS-HEAP-01/OS-SHARD-01，内联模式，未改动任何现有规则）
  - `aws-aiops-cruise/tests/test_inference_phase1.py`（新建，5 测试）
- **开始**: 2026-07-11
- **完成**: 进行中（GCL 评审后提交）
- **GCL 评审结论**: 2 个 Critic 子 Agent 并行评审中
- **测试**: 全量 45 passed（含新增 5）；Generator 自查 Safety/引用存在性/frontmatter 全 PASS
- **说明**: 未重复实现已有规则（DYNAMO-THROTTLE-01/EC-MEM-01/CF-* 均保留 HEAD 原状，仅新增 4 条缺失规则）。

## 期 2 详情

- **范围**: eks + cloudfront 路由已补；cloudfront inference 代码已存在（CF-*），eks inference 代码缺失需新建（EKS-NODE-01/EKS-OOM-01）
- **状态**: 待开始

## 期 3 详情

- **范围**: athena + ram + secretsmanager 路由已补；inference 代码均缺失需新建
- **状态**: 待开始
