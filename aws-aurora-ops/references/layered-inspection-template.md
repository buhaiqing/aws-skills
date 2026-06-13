# Aurora 分层巡检 — AIOps 模板

_Latest update: 2026-06-13_

> **关联**: [SKILL.md](../SKILL.md) · [prompt-examples.md](prompt-examples.md)

---

## 一句话触发

> **"帮我巡检 Aurora 集群并做根因分析和自治愈建议"**

## 巡检层次

```
1. 网络层: SG (3306/5432)、DB subnet group、RDS Proxy target SG
2. 集群层: describe-db-clusters、members 状态、Global DB membership
3. 指标层: AuroraReplicaLag、DatabaseConnections、ServerlessDatabaseCapacity、BufferCacheHitRatio
4. 应用层: PI (writer DbiResourceId) top SQL / wait events
```

## 输出闭环格式

```
【发现】集群/实例 + 指标值 + 偏离标准
【RCA】直接原因 → 关联下层 → 判定依据
【决策】[AUTO_HEAL] / [AI_ASSIST] / [MANUAL]
【SLA】P0(15min) / P1(2h) / P2(24h)
```

## 检查项及决策

| 检查项 | 命令/指标 | 健康标准 | 决策 |
|--------|-----------|---------|------|
| 集群状态 | `describe-db-clusters` | Status=available | MANUAL failover |
| Writer 状态 | members `IsClusterWriter` | DBInstanceStatus=available | MANUAL |
| AuroraReplicaLag | CW `AuroraReplicaLag` | < {{user.replica_lag_threshold_ms}}ms | AI_ASSIST 加 reader |
| DatabaseConnections | CW dim `DBClusterIdentifier` | < 90% max_connections | AI_ASSIST pool/proxy |
| ServerlessDatabaseCapacity | CW vs MaxCapacity | < 90% max | AUTO_HEAL 提 MaxCapacity |
| BufferCacheHitRatio | CW | > 99% | AI_ASSIST 升实例 class |
| GlobalDBReplicationLag | CW (Global DB) | < 1000ms | MANUAL |
| BackupRetention | describe-db-clusters | ≥ 7 (prod) | MANUAL |
| DeletionProtection | describe-db-clusters | true (prod) | AI_ASSIST 启用 |
| PI enabled | describe-db-instances (writer) | true | AUTO_HEAL 启用 PI |

## 自治愈边界

| 异常 | 操作 | Tier | 前提 |
|------|------|------|------|
| Serverless 顶满 | `modify-db-cluster` 提高 MaxCapacity | AUTO_HEAL | 新值 ≤ ceiling，非 prod 或 confirm |
| PI 未启用 | `modify-db-instance --enable-performance-insights` | AUTO_HEAL | writer 实例 |
| ReplicaLag 高 | 添加 reader 实例 | AI_ASSIST | 需 confirm |
| Failover | `failover-db-cluster` | MANUAL | 必须 confirmation_token |
| max_connections | 修改 cluster parameter group | AI_ASSIST | 内存允许 |

同一异常自治愈失败 2 次 → 降级 `[MANUAL]`。

## 汇总报告示例

```
╔════════════════ Aurora 巡检 — prod-aurora-app — 2026-06-13 ════════════════╗
║ 检查 8 项  ✅ 5  ⚠️ 2  ❌ 1                                                ║
║ [AUTO_HEAL] 1 — Serverless MaxCapacity 16→24                               ║
║ [AI_ASSIST] 1 — AuroraReplicaLag 12s，建议加 reader                        ║
║ [MANUAL]    1 — Global DB secondary lag 3.2s                               ║
╚════════════════════════════════════════════════════════════════════════════╝
```
