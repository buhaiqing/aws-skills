# Aurora Skill — Prompt Examples (AIOps)

_Latest update: 2026-07-31_

User prompts that activate `aws-aurora-ops`. Standalone RDS → `aws-rds-ops`. Links: [SKILL.md](../SKILL.md) · [layered-inspection-template.md](layered-inspection-template.md)

---

## 1 — Replica Lag RCA

**Prompt:** `Aurora 集群 prod-aurora-app 读延迟很高，reader 跟不上 writer。`

| Step | Action |
|---|---|
| 1 | `describe-db-clusters` → members, writer/reader |
| 2 | CloudWatch `AuroraReplicaLag` (1h) |
| 3 | Writer `CPUUtilization` + `CommitLatency`; PI top SQL |
| 4 | Output RCA + tier |

**Sample:** `AuroraReplicaLag=8500ms, writer CPU=72% → [AI_ASSIST] add/upgrade reader`

---

## 2 — Writer Failure / Failover

**Prompt:** `Aurora 集群 prod-aurora-catalog 写节点挂了，检查并故障切换。`

| Step | Action |
|---|---|
| 1 | `describe-db-clusters` → `.DBClusterMembers`, `Status` |
| 2 | Member `describe-db-instances` → `DBInstanceStatus` |
| 3 | No auto-failover + healthy reader → `failover-db-cluster` (**MANUAL** + `confirm=FAILOVER_CLUSTER <id>`) |
| 4 | Validate cluster `Endpoint` |

**Tree:** writer healthy → no switch; writer failed + reader ok → `[MANUAL]` failover; no reader → create instance or PITR.

---

## 3 — Serverless v2 Capacity

**Prompt:** `Aurora Serverless 很慢，ACU 不够？`

`describe-db-clusters` → CloudWatch `ServerlessDatabaseCapacity` vs MaxCapacity → if ≥95% MaxCapacity 15min → `[AUTO_HEAL]` raise MaxCapacity (≤ `{{user.serverless_max_cap_ceiling}}`).

---

## 4 — Global DB Replication Lag

**Prompt:** `Aurora Global Database secondary 区域延迟大。`

`describe-global-clusters` → `AuroraGlobalDBReplicationLag` (primary) → primary write IOPS → `[MANUAL]` network/write burst or promote secondary.

---

## 5 — RDS Proxy Connection Storm

**Prompt:** `RDS Proxy 连 Aurora 报 too many connections。`

`describe-db-proxies` + targets → Proxy `ClientConnections` / `DatabaseConnectionsSetupFailed` → cluster `DatabaseConnections` → `max_connections` via cluster parameters → `[AI_ASSIST]` tune pool; see `aws-aiops-cruise` runbook 06.

---

## 6 — Backup / PITR Compliance

**Prompt:** `检查 Aurora 集群备份是否符合生产规范。`

```bash
aws rds describe-db-clusters --query "DBClusters[?Engine=='aurora-mysql' || Engine=='aurora-postgresql'].{ID:DBClusterIdentifier,Backup:BackupRetentionPeriod,Encrypted:StorageEncrypted,DeletionProtection:DeletionProtection}" --output table
```

Checks: BackupRetention ≥7 · Encrypted · DeletionProtection · recent snapshot → `[MANUAL]` non-compliant list.

---

## 7 — FinOps (Reader / ACU)

**Prompt:** `Aurora 成本优化？reader 和 Serverless 是否过大？`

| Check | Signal | Tier |
|---|---|---|
| Idle reader | CPU <10% (14d) | `[AI_ASSIST]` remove/downsize |
| Serverless oversize | MaxCapacity >> p99 capacity | `[AI_ASSIST]` lower MaxCapacity |

---

## 8 — Cross-Skill Latency RCA

**Prompt:** `API 延迟高，怀疑 Aurora，从 ALB 查到数据库。`

`aws-elb-ops` TargetResponseTime → `aws-ec2-ops` app CPU → `aws-aurora-ops` ReplicaLag + PI + Connections → `aws-vpc-ops` SG 3306/5432 if timeout.

---

## Principles

1. Each prompt maps to one AIOps scenario + `decision_tier`
2. Failover / Backtrack / delete cluster → always `[MANUAL]` + confirm tokens per SKILL.md
3. Serverless MaxCapacity up → only default `[AUTO_HEAL]` (with ceiling)
4. PI slow-query detail → `aws-rds-ops` §SQL Slow Query (writer `DbiResourceId`)
