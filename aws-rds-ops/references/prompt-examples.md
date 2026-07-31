# RDS Skill — Prompt Examples

_Latest update: 2026-07-31_

典型 AIOps / FinOps 场景。日常语言 → Agent 解析；Aurora 集群故障切换见 **`aws-aurora-ops`**。

> **链接**：[SKILL.md](../SKILL.md) · [aws-cli-usage.md](aws-cli-usage.md) · [troubleshooting.md](troubleshooting.md)

## 场景 1：慢查询根因诊断

**Prompt**: `我的 RDS MySQL 最近变慢了，帮我查一下什么问题。`

| 步骤 | 操作 |
|------|------|
| 1 | `describe-db-instances` → 状态/规格 |
| 2 | CloudWatch `CPUUtilization` / `ReadLatency` / `DatabaseConnections` |
| 3 | Performance Insights → Top SQL |
| 4 | `describe-db-log-files` → 慢查询日志 |
| 5 | 输出 RCA：发现 → 根因 → 建议（索引/规格） |

→ `[AI_ASSIST]` · 委托 `aws-cloudwatch-ops` 拉指标

## 场景 2：存储自动扩容（AUTO_HEAL）

**Prompt**: `RDS 存储快满了，帮我看看并处理。`

| 步骤 | 操作 |
|------|------|
| 1 | CloudWatch `FreeStorageSpace` < 10% |
| 2 | `modify-db-instance --allocated-storage`（≥ max(当前×1.2, 当前+20GB)） |
| 3 | `describe-db-instances` 验证 `.AllocatedStorage` |

→ `[AUTO_HEAL]` 非破坏性写入

## 场景 3：连接数异常 + 自治愈

**Prompt**: `数据库连不上了，连接数太多了。`

| 步骤 | 操作 |
|------|------|
| 1 | `DatabaseConnections` vs 参数组 `max_connections` |
| 2 | ≥90% 阈值 → `modify-db-parameter-group` 上调 |
| 3 | 建议检查应用连接池泄漏 |

→ `[AI_ASSIST]`

## 场景 4：备份合规检查

**Prompt**: `检查所有 RDS 实例备份配置是否符合规范。`

```bash
aws rds describe-db-instances --query "DBInstances[*].{ID:DBInstanceIdentifier,Backup:BackupRetentionPeriod,Encrypted:StorageEncrypted,DeletionProtection:DeletionProtection}" --output table
```

检查：Prod `BackupRetentionPeriod≥7`、`StorageEncrypted=true`、`DeletionProtection=true`。

## 场景 5：闲置实例清理（FinOps）

**Prompt**: `找闲置 RDS 实例删掉省钱。`

| 步骤 | 操作 |
|------|------|
| 1 | `describe-db-instances` → 创建时间/状态 |
| 2 | CloudWatch `DatabaseConnections` 14 天 Maximum = 0 |
| 3 | 建议 stop/delete；删除需 confirm token |

→ 删除：`confirm=DELETE_DB_INSTANCE` 或 `DELETE_NO_SNAPSHOT`（skip snapshot）

## 场景 6：灾备 — 跨区域快照复制

**Prompt**: `把 prod-mysql-orders 快照复制到 eu-west-1 做灾备。`

| 步骤 | 操作 |
|------|------|
| 1 | `create-db-snapshot` → `wait db-snapshot-available` |
| 2 | `copy-db-snapshot --destination-region eu-west-1` |
| 3 | `describe-db-snapshots --region eu-west-1` 验证 |

## 场景 7：参数组性能调优

**Prompt**: `PostgreSQL 性能不佳，检查参数组并给优化建议。`

```bash
aws rds describe-db-parameters --db-parameter-group-name {{u.pg}}
```

关注：`shared_buffers`（内存 25%）、`work_mem`（25–50MB）、`max_connections`（按规格）。

## 场景 8：跨技能 CPU 飙升 RCA

**Prompt**: `RDS CPU 99%，是应用还是数据库问题？`

```
1. [rds-ops] Performance Insights → Top SQL / Wait Events
2. [cloudwatch-ops] CPU + Connections + ReadIOPS 趋势
3. [ec2-ops] SQL 正常时查底层
4. [lambda-ops] 连接突增时查调用量
```

## 场景 9：容量预测（FinOps）

**Prompt**: `看存储和 CPU 趋势，未来一个月要不要扩容？`

拉 30 天 CloudWatch → 线性拟合到期天数 → 建议扩容 / 清理 / 启用存储自动扩容。

## Quick Reference

| 用户说 | 场景 | 决策 | 模块 |
|--------|------|------|------|
| "数据库变慢" | 1 | `[AI_ASSIST]` | rds + cw |
| "存储快满了" | 2 | `[AUTO_HEAL]` | rds + cw |
| "连接数太多" | 3 | `[AI_ASSIST]` | rds |
| "备份合规检查" | 4 | `[AI_ASSIST]` | rds |
| "闲置实例清理" | 5 | `[MANUAL]` delete confirm | rds + cw |
| "跨区域灾备快照" | 6 | `[AI_ASSIST]` | rds |
| "参数组调优" | 7 | `[AI_ASSIST]` | rds |
| "CPU 飙升跨层 RCA" | 8 | `[AI_ASSIST]` | rds + cw + ec2 |
| "容量预测" | 9 | `[AI_ASSIST]` | rds + cw |
| Aurora 故障切换 | **非 RDS** | — | `aws-aurora-ops` |
