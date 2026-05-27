# RDS Core Concepts

AWS Relational Database Service architecture, components, and operational concepts.

## Service Overview
**AWS RDS** — Managed relational DB. Key benefits: automated provisioning/patching, managed backups, Multi-AZ HA, read replicas, storage auto-scaling, Performance Insights, encryption.

## Supported Engines (Use API to check latest versions)
```bash
aws rds describe-db-engine-versions --engine mysql --query "DBEngineVersions[*].EngineVersion"
```
| Engine | Default Port | Storage Min | Replication |
|--------|-------------|-------------|-------------|
| MySQL 5.7/8.0 | 3306 | 20 GB | Read replicas, Multi-AZ |
| PostgreSQL 12-16 | 5432 | 20 GB | Read replicas, Multi-AZ |
| Aurora MySQL 8.0 | 3306 | — | Cluster (writer + 15 readers) |
| Aurora PostgreSQL 15 | 5432 | — | Cluster (writer + 15 readers) |
| MariaDB 10.4-10.6 | 3306 | 20 GB | Read replicas |
| Oracle 19c/21c | 1521 | 20 GB | BYOL or License Included |
| SQL Server 2016-2022 | 1433 | 20 GB | License Included |

## DB Instance Components

**Identifier**: 1-63 alphanumeric, first char must be letter, immutable.

**Instance Class Prefixes**: db.t (burstable), db.r (memory), db.m (general), db.x (extreme memory)
- Graviton2: db.t4g, db.r6g (ARM, cost-effective)
- Standard: db.t3, db.r5, db.m5

**Storage Types**: gp2(3 IOPS/GB baseline), gp3(3000 baseline, up to 16000), io1/io2(provisioned up to 50000)
- **Auto-scaling**: triggered when FreeStorage < 10% or < 5 GB

## High Availability

**Multi-AZ**: Primary + standby in different AZ, sync replication, auto failover (~2x cost)
**Multi-AZ DB Cluster**: 1 writer + 2 readers in different AZs, faster failover (MySQL/PostgreSQL only)
**Aurora**: Storage distributed across 3 AZs (6 copies), writer + up to 15 readers

## Read Replicas
- **Cross-AZ**: Async, reduce primary read load, can be promoted
- **Cross-Region**: Async, DR + global reads, can be promoted
- **Limits**: MySQL/PG ≤5 per source, Aurora ≤15 readers

## Backup & Recovery
- **Automated**: Daily full backup + 5-min transaction logs, retention 1-35 days (default 7)
- **Manual snapshots**: Retained indefinitely, user-initiated, cross-region copy supported
- **PITR**: Point-in-time recovery within retention period

## Aurora
- **Serverless v2**: 0.5-128 ACU, instant scale, pay-per-use
- **Global Database**: <1s lag cross-region, up to 5 secondary regions, 16 readers each

## Parameter Groups
- **Default**: Engine family templates (immutable)
- **Custom**: Derived from default, tune performance, static params need reboot
- **Types**: `immediate` (dynamic, e.g. max_connections) / `pending-reboot` (static, e.g. innodb_buffer_pool_size)

## Security Highlights
- VPC security groups control network access (port + source IP)
- IAM auth for passwordless login (MySQL/PG/Aurora)
- Storage encryption via KMS (cannot disable after creation)
- SSL/TLS in transit via rds-ca-* certs
- Deletion protection prevents accidental delete

## Key Metrics (CloudWatch AWS/RDS)
`CPUUtilization`, `FreeStorageSpace`, `DatabaseConnections`, `ReadIOPS`/`WriteIOPS`, `FreeableMemory`, `SwapUsage`, `ReplicaLag`

## Quotas
| Resource | Default Limit | Check Command |
|----------|--------------|--------------|
| DB Instances | 40/region | `aws service-quotas get-service-quota --service-code rds --quota-code L-...` |
| DB Snapshots | 100/region | |
| Total Storage | 100 TB/region | |
| Read Replicas/source | 5 | |
| Parameter Groups | 50 | |

**Quota Increase**: Via AWS Service Quotas console.

## Instance States
`available`(normal) | `creating` | `modifying` | `deleting` | `stopped` | `backing-up` | `restoring` | `upgrading` | `maintenance` | `failed`

## Best Practices

**Production**: Multi-AZ + encryption + deletion protection + backup ≥7d + private subnet + security group min access + Performance Insights + Enhanced Monitoring + tuned parameter group.

## Pricing (FinOps Reference)
- **Instance**: Per-hour by class. Graviton2 lower cost. Multi-AZ = 2x instance cost.
- **Storage**: Per GB/month. gp3: base + provisioned IOPS. io1/io2: base + provisioned IOPS.
- **Backup**: Automated backup free up to instance size. Manual snapshots billed indefinitely.
- **Data Transfer**: Inter-AZ $0.01/GB (Multi-AZ replication). Cross-region at standard rates. Within AZ free.
- **Extras**: Performance Insights 7d free, $0.02/vCPU-hour beyond. Enhanced Monitoring free.

**Dev/Test**: Single AZ + smaller class + shorter retention + stop/start for savings.

**Security**: No public access (prod) + IAM auth + Secrets Manager for passwords + regular rotation.