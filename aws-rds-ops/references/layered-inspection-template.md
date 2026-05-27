# RDS 分层巡检 — 提示词模板（含根因分析与自治愈）

_Latest update: 2026-05-28_

> **关联**: [SKILL.md](../SKILL.md) → Cross-Skill Orchestration: RDS Inspection
> **关联**: 本模板 → [prompt-examples.md](prompt-examples.md) → 场景 9

---

## 模板：RDS 全面健康巡检 + 根因分析

### 一句话触发

> **"帮我巡检 RDS 并做根因分析和自治愈建议"**

### 巡检项目清单

```
自底向上三层检查:

1. 网络层: VPC 安全组规则(3306/5432端口)、DB Subnet Groups 子网状态
2. 资源层: RDS 实例状态、CPU/内存/存储/连接数指标、备份配置、快照状态
3. 应用层: Performance Insights Top SQL、慢查询日志、连接源分析

对每个异常按以下格式输出:
```

### 输出闭环格式

```
【发现】资源名 + 当前指标值 + 偏离标准
【RCA】根因分析
  ├─ 直接原因
  ├─ 关联下层(如有)
  └─ 判定依据(引用指标/日志)
【决策】[MANUAL]/[AI_ASSIST]/[AUTO_HEAL]
  ├─ 操作方案
  ├─ 预期效果
  └─ 失败回退
【SLA】P0(15min)/P1(2h)/P2(24h)/P3(下一迭代)
```

### RDS 检查项及标准

| 检查项 | 命令 | 健康标准 | 异常决策类型 |
|--------|------|---------|-------------|
| 实例状态 | `describe-db-instances` | Status=available | [AUTO_HEAL] failover |
| CPU 利用率 | `get-metric-statistics AWS/RDS CPUUtilization` | < 80% avg 1h | [AI_ASSIST] 扩容 |
| FreeStorageSpace | `get-metric-statistics` `FreeStorageSpace` | > 10% 或 > 10GB | [AUTO_HEAL] 自动扩容 |
| DatabaseConnections | `get-metric-statistics` `DatabaseConnections` | < 90% max_connections | [AUTO_HEAL] 调整 max_connections |
| BackupRetention | `describe-db-instances` `.BackupRetentionPeriod` | >= 7 (prod) / >=1 (dev) | [MANUAL] 修改配置 |
| ReadReplicaLag | `get-metric-statistics` `ReplicaLag` | < 1000ms | [AI_ASSIST] 扩副本 |
| Snapshot 状态 | `describe-db-snapshots` | 快照最近 7 天内创建 | [MANUAL] 补创建 |
| DeletionProtection | `describe-db-instances` `.DeletionProtection` | true (prod) | [AI_ASSIST] 启用 |
| StorageEncrypted | `describe-db-instances` `.StorageEncrypted` | true (prod) | [MANUAL] 需重建 |

### RDS 自治愈场景

| 异常 | 自治愈操作 | 前提 |
|------|-----------|------|
| FreeStorageSpace < 10% | `modify-db-instance --allocated-storage {{new}} --apply-immediately` | 存储未达实例上限 |
| Connections > 90% max | `modify-db-parameter-group` 增加 max_connections | 实例内存允许 |
| ReadReplicaLag > 5s | 扩副本实例规格 `modify-db-instance --db-instance-class {{bigger}}` | 有可用副本 |
| 实例故障(not available) | `reboot-db-instance` 或 `failover-db-cluster` (Aurora) | Multi-AZ 配置 |

**自治愈失败处理**: 同一异常重复失败 2 次 → 降级为 `[MANUAL]`

### 输出示例（RDS 巡检）

```
╔══════════════════════════════════════════════════════════╗
║  异常 #1                                                ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║ [发现] prod-mysql-orders / FreeStorageSpace               ║
║   当前: 2.1 GB (剩余 8%)                                 ║
║   正常: > 10% 或 > 10 GB                                  ║
║                                                          ║
║ [RCA] 根因分析                                            ║
║   ├─ 直接原因: 数据量增长超出预期, 无自动扩容策略         ║
║   ├─ 关联下层: N/A                                        ║
║   └─ 判定依据:                                            ║
║      FreeStorageSpace 30天趋势: 每月下降 15GB              ║
║      预测 7 天后耗尽                                       ║
║                                                          ║
║ [决策] [AUTO_HEAL]                                        ║
║   ├─ 操作: 自动扩容 500 → 600 GB                          ║
║   │  aws rds modify-db-instance                          ║
║   │    --db-instance-identifier prod-mysql-orders          ║
║   │    --allocated-storage 600                            ║
║   │    --apply-immediately                                ║
║   ├─ 预期: 存储扩容至 600 GB, 可用空间恢复至 ~17%         ║
║   └─ 失败: 确认是否达到实例存储上限, 考虑迁移到更大实例   ║
║                                                          ║
║ [SLA] P1 (2小时) — 存储即将耗尽                           ║
╚══════════════════════════════════════════════════════════╝
```

### 全局汇总报告示例

```
╔══════════════════════════════════════════════════════════════╗
║            RDS 巡检报告  2026-05-28 01:00 UTC               ║
╠══════════════════════════════════════════════════════════════╣
║ ┌─── 统计 ────────────────────────────────────────────┐     ║
║ │ 9项检查  ✅ 6  ⚠️ 2  ❌ 1                           │     ║
║ └─────────────────────────────────────────────────────┘     ║
║ ┌─── 决策分布 ────────────────────────────────────────┐     ║
║ │ [AUTO_HEAL] 1项 — 存储自动扩容                      │     ║
║ │ [AI_ASSIST] 1项 — CPU过高建议扩容                   │     ║
║ │ [MANUAL]    1项 — 备份保留期不足, 需人工调整        │     ║
║ └─────────────────────────────────────────────────────┘     ║
╚══════════════════════════════════════════════════════════════╝
```