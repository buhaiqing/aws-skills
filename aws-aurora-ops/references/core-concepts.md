# Aurora Core Concepts

Amazon Aurora is a MySQL/PostgreSQL-compatible managed database built on a distributed storage layer. Operations use the **RDS API** (`aws rds`, boto3 `rds` client).

## Architecture

| Component | Description |
|-----------|-------------|
| **DB cluster** | Logical unit: shared storage volume, cluster endpoint, reader endpoint |
| **Writer instance** | Single primary; handles writes (`IsClusterWriter=true`) |
| **Reader instances** | Up to 15; async replication; served via reader endpoint |
| **Storage** | Auto-scales 10 GB–128 TB; 6 copies across 3 AZs |
| **Endpoints** | Cluster (writer), Reader (load-balanced readers), Custom (static reader set) |

## Engines (query latest via API)

```bash
aws rds describe-db-engine-versions --engine aurora-mysql --query "DBEngineVersions[-1].EngineVersion"
aws rds describe-db-engine-versions --engine aurora-postgresql --query "DBEngineVersions[-1].EngineVersion"
```

| Engine | Default Port | Notes |
|--------|-------------|-------|
| aurora-mysql | 3306 | Backtrack, Global Database |
| aurora-postgresql | 5432 | Fast clone, Babelfish (optional) |

## High Availability

- **AZ failure**: Aurora promotes reader or recreates instance (~30 s typical failover)
- **Manual failover**: `failover-db-cluster` — brief write interruption
- **Promotion tier**: Lower number = higher failover priority (0–15)

## Aurora Serverless v2

- Instance class `db.serverless` with `MinCapacity` / `MaxCapacity` in ACUs (0.5–128)
- Scales per instance; cluster can mix provisioned + serverless instances
- Use `modify-db-cluster --serverless-v2-scaling-configuration` for cluster defaults

## Global Database

- Primary region + up to 5 secondary regions
- Storage-based replication (<1 s typical lag)
- `create-global-cluster` → attach regional clusters → secondary read-only until promoted

## Backup & Recovery

- Continuous backup to S3; PITR within retention (1–35 days)
- **Cluster snapshots** (`create-db-cluster-snapshot`) — preferred for Aurora
- **Backtrack** (Aurora MySQL only): rewind cluster to timestamp within backtrack window

## Cluster Parameter Groups

- Family: `aurora-mysql8.0`, `aurora-postgresql15`, etc.
- Cluster-level params apply to all instances; some require reboot
- Instance parameter groups optional for instance-specific overrides

## Key Metrics (CloudWatch `AWS/RDS`)

`AuroraReplicaLag`, `CPUUtilization`, `DatabaseConnections`, `FreeLocalStorage`, `BufferCacheHitRatio`, `CommitLatency`, `Deadlocks`, `ServerlessDatabaseCapacity` (Serverless v2)

## AIOps Metrics Map

| Metric / Signal | Rule ID | Runbook | Typical tier |
|-----------------|---------|---------|--------------|
| `AuroraReplicaLag` > threshold | AURORA-LAG-01 / FD-15 | RB-023 | AI_ASSIST |
| `ServerlessDatabaseCapacity` ≥ 90% Max | AURORA-SLV2-01 / PD-08 | RB-024 | AUTO_HEAL |
| Writer / cluster unhealthy | FD-16 / RDS-PROXY-AURORA-01 | RB-025 | MANUAL |
| `AuroraGlobalDBReplicationLag` high | AURORA-GDB-01 / PD-09 | RB-026 | MANUAL |
| Proxy + cluster connections | RDS-PROXY-AURORA-02 / PD-04 | RB-027 | AI_ASSIST |
| PI `db.load.avg` elevated (writer) | RDS-PI-01 | — | AI_ASSIST |
| `BufferCacheHitRatio` < 99% | AURORA-CACHE-01 | — | AI_ASSIST |

Composite rules in `aws-aiops-cruise/references/inference-rules.md`: `RDS-PROXY-AURORA-*`, `RDS-PROXY-CONN-01`.

Incident contract: `aws-aiops-cruise/references/incident-schema.md` v1.1.0 (`resource_type: Aurora`).

## Quotas

| Resource | Typical default | Check |
|----------|----------------|-------|
| DB clusters | 40/region | Service Quotas console |
| Readers/cluster | 15 | Hard limit |
| Cluster snapshots | 100/region | Delete unused |

## Cluster States

`available` | `creating` | `modifying` | `deleting` | `stopped` | `starting` | `backing-up` | `backtracking` | `failed`

## Best Practices

**Production**: ≥2 instances (writer + reader), deletion protection, encrypted storage, backup ≥7d, private subnets, tuned cluster parameter group, monitor `AuroraReplicaLag`, Performance Insights enabled.

**Security**: No public access; IAM DB auth or Secrets Manager for credentials; KMS encryption at rest; TLS in transit.
