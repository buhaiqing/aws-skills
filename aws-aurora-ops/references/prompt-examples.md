# Aurora Skill — Prompt Examples (AIOps)

_Latest update: 2026-06-13_

Concrete user prompts that activate `aws-aurora-ops`. For standalone RDS instances, use `aws-rds-ops`.

> **Links**: [SKILL.md](../SKILL.md) · [layered-inspection-template.md](layered-inspection-template.md)

---

## 场景 1：Replica Lag 根因诊断

### Prompt
```
Aurora 集群 prod-aurora-app 读延迟很高，reader 好像跟不上 writer。
```

### 流程
| 步骤 | 操作 |
|------|------|
| 1 | `describe-db-clusters` → members、writer/reader 状态 |
| 2 | CloudWatch `AuroraReplicaLag`（集群维度，1h） |
| 3 | Writer `CPUUtilization` + `CommitLatency` |
| 4 | PI（writer `DbiResourceId`）→ wait event / top SQL |
| 5 | 输出 RCA + tier |

### 输出示例
```
【发现】prod-aurora-app AuroraReplicaLag=8500ms (1h avg), writer CPU=72%
【RCA】写负载突增 + 单 reader 规格偏小
【决策】[AI_ASSIST] 添加 reader 或升级 reader 实例 class
【SLA】P1 (2h)
```

---

## 场景 2：写节点故障 / Failover 决策

### Prompt
```
Aurora 集群 prod-aurora-catalog 写节点挂了，帮我检查并故障切换。
```

### 流程
| 步骤 | 操作 |
|------|------|
| 1 | `describe-db-clusters` → `.DBClusterMembers`, `Status` |
| 2 | 各 member `describe-db-instances` → `DBInstanceStatus` |
| 3 | 若 Aurora 未自动 failover 且存在 healthy reader → `failover-db-cluster`（**MANUAL** + confirm） |
| 4 | 验证 cluster `Endpoint` 可达 |

> **决策树**: `Status=available` 且 writer healthy → 无需切换；writer failed + reader available → `[MANUAL]` failover；无 healthy reader → `[MANUAL]` 创建实例或 PITR 恢复。

---

## 场景 3：Serverless v2 容量顶满

### Prompt
```
Aurora Serverless 数据库一直很慢，是不是 ACU 不够了？
```

### 流程
| 步骤 | 操作 |
|------|------|
| 1 | `describe-db-clusters` + serverless 实例 class |
| 2 | CloudWatch `ServerlessDatabaseCapacity` vs configured MaxCapacity |
| 3 | `CPUUtilization` + PI db.load |
| 4 | 若 capacity ≥ 95% MaxCapacity 持续 15min → `[AUTO_HEAL]` 提高 MaxCapacity（≤ `{{user.serverless_max_cap_ceiling}}`） |

---

## 场景 4：Global Database 复制 Lag

### Prompt
```
Aurora Global Database  secondary 区域延迟很大，有没有问题？
```

### 流程
| 步骤 | 操作 |
|------|------|
| 1 | `describe-global-clusters` → members |
| 2 | CloudWatch `AuroraGlobalDBReplicationLag`（primary region） |
| 3 | Primary write IOPS / `CommitLatency` |
| 4 | 输出 `[MANUAL]` 建议：排查网络、写入 burst、考虑 promote secondary |

---

## 场景 5：RDS Proxy + Aurora 连接风暴

### Prompt
```
应用通过 RDS Proxy 连 Aurora，报 too many connections。
```

### 流程
| 步骤 | 操作 |
|------|------|
| 1 | `describe-db-proxies` + `describe-db-proxy-targets` |
| 2 | Proxy metrics: `ClientConnections`, `DatabaseConnectionsSetupFailed` |
| 3 | Aurora 集群 `DatabaseConnections`（`DBClusterIdentifier` 维度） |
| 4 | 集群参数 `max_connections` via `describe-db-cluster-parameters` |
| 5 | `[AI_ASSIST]` 调 proxy pool / 建议应用连接池；见 `aws-aiops-cruise` runbook 06 |

---

## 场景 6：集群备份 / PITR 合规扫描

### Prompt
```
检查所有 Aurora 集群备份配置是否符合生产规范。
```

```bash
aws rds describe-db-clusters --query "DBClusters[?Engine=='aurora-mysql' || Engine=='aurora-postgresql'].{ID:DBClusterIdentifier,Backup:BackupRetentionPeriod,Encrypted:StorageEncrypted,DeletionProtection:DeletionProtection,Engine:Engine}" --output table
```

检查项: BackupRetention ≥ 7 (prod) · StorageEncrypted=true · DeletionProtection=true · 近 7 天有 cluster snapshot → `[MANUAL]` 不合规清单。

---

## 场景 7：FinOps — Reader / ACU 过度预留

### Prompt
```
Aurora 成本能不能优化？reader 和 Serverless 配置是不是过大？
```

| 检查 | 命令/指标 | 建议 tier |
|------|-----------|-----------|
| Reader CPU < 10% (14d) | CloudWatch per instance | `[AI_ASSIST]` 减少 reader 或降规格 |
| 单 reader 无流量 | PI `db.host` 维度 | `[AI_ASSIST]` 移除 idle reader |
| Serverless MaxCapacity >> p99 capacity | `ServerlessDatabaseCapacity` | `[AI_ASSIST]` 降低 MaxCapacity |

---

## 场景 8：跨技能 — 全链路延迟 RCA

### Prompt
```
API 延迟高，怀疑是 Aurora 拖后腿，帮我从 ALB 到数据库查一遍。
```

```
1. [aws-elb-ops] TargetResponseTime + 5xx
2. [aws-ec2-ops] 应用 EC2 CPU / 连接数
3. [aws-aurora-ops] AuroraReplicaLag + PI top SQL + DatabaseConnections
4. [aws-vpc-ops] SG 3306/5432 若连接 timeout
```

---

## 设计原则

1. 每个 Prompt 对应一个 AIOps 场景 + 明确 `decision_tier`
2. Failover / Backtrack / 删集群 → 永远 `[MANUAL]`
3. Serverless MaxCapacity 上调 → 唯一默认 `[AUTO_HEAL]`（带上限）
4. PI 慢查询细节 → 引用 `aws-rds-ops` §SQL Slow Query（集群 writer 的 `DbiResourceId`）
