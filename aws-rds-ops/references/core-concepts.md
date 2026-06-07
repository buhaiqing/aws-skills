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

## Performance Insights & Slow Query Analysis

### Performance Insights (PI)
- **Purpose**: Database performance monitoring with 7-dimension analysis
- **Data**: DB load, wait events, top SQL, users, hosts, databases
- **Retention**: 7 days free → 2 years paid
- **Dimensions**: `db.sql_tokenized` (top SQL), `db.wait_event` (wait events), `db.user` (user), `db.host` (host), `db.database` (DB)
- **Key Metrics**: `db.sproc_execution_time` (SQL exec), `db.cpu` (CPU), `db.io` (IO), `db.dbload` (total load), `db.dbload_non_cpu` (non-CPU load)
- **Access**: `aws pi` CLI or PI API via boto3

### Common Wait Events & Their Meaning

| Wait Event | Meaning | Common Fix |
|---|---|---|
| `CPU` | Query consuming CPU cycles | Add index, optimize query, scale instance |
| `IO:XactSync` | Transaction commit waiting for storage | Tune sync_binlog, use Multi-AZ with SSD |
| `IO:DataFileRead` | Reading data from disk (buffer miss) | Increase buffer pool, check index |
| `IO:LogWrite` | Writing WAL/redo log | Use gp3 with provisioned IOPS |
| `tcp:connection` | Client connection handling | Increase max_connections, use connection pool |
| `Lock:RowLockWait` | Row lock contention | Optimize transaction scope, use NOWAIT |
| `Lock:TableLock` | Table-level lock | Use InnoDB, check DDL locking |
| `wait/synch/mutex` | Internal contention | Tune innodb_thread_concurrency |

### Key Parameters for Query Performance (MySQL)

| Parameter | Default | Recommendation | Effect |
|---|---|---|---|
| `slow_query_log` | OFF | 1 | Enable slow query logging |
| `long_query_time` | 10 | 2-5 | Log queries slower than N seconds |
| `log_queries_not_using_indexes` | OFF | 1 | Flag full table scans |
| `innodb_buffer_pool_size` | 25% of RAM | 70-80% of RAM | Reduce disk reads |
| `innodb_log_file_size` | 128MB | 1-4GB | Reduce log contention |
| `max_connections` | ~80-200 | (RAM/thread_mem) | Avoid connection throttling |
| `tmp_table_size` / `max_heap_table_size` | 16MB | 64-256MB | Reduce disk temp tables |
| `sort_buffer_size` | 256KB | 1-4MB | Speed up sort operations |
| `join_buffer_size` | 256KB | 1-4MB | Speed up JOIN (no index) |

### Key Parameters for Query Performance (PostgreSQL)

| Parameter | Default | Recommendation | Effect |
|---|---|---|---|
| `log_min_duration_statement` | -1 (off) | 5000ms | Log slow queries |
| `shared_buffers` | 128MB | 25% of RAM | Cache data in memory |
| `work_mem` | 4MB | 16-64MB | Per-operation sort memory |
| `maintenance_work_mem` | 64MB | 1GB | Speed up VACUUM, CREATE INDEX |
| `effective_cache_size` | 4GB | 75% of RAM | Planner memory estimation |
| `random_page_cost` | 4 | 1.1 (SSD) | Query planner SSD tuning |
| `effective_io_concurrency` | 1 | 200 (SSD) | Parallel IO on SSD |
| `max_parallel_workers_per_gather` | 2 | 4-8 | Parallel query execution |

### Slow Query Diagnosis Flow

```
1. Is PI enabled? → If not, enable (`modify-db-instance --enable-performance-insights`)
2. Is slow log published to CW? → If not, enable (`modify-db-instance --cloudwatch-logs-export-configuration`)
3. Get DbiResourceId → `describe-db-instances[0].DbiResourceId`
4. Query PI for top SQL by load → `pi get-resource-metrics` with `db.sql_tokenized` group
5. Query PI for wait events → Same API with `db.wait_event` group
6. Query CloudWatch slow query log → `logs start-query` on slowquery log group
7. Cross-reference: top SQL from PI ↔ slow queries from CloudWatch
8. Pattern match (see troubleshooting.md) → recommend index / parameter / scale
9. Apply recommendation → validate improvement via PI
```

### Performance Insights API Dimensions

| Dimension Group | Description | Use Case |
|---|---|---|
| `db.sql_tokenized` | Top SQL by DB load (normalized) | Find slow queries |
| `db.wait_event` | Wait events by % of total DB load | Find bottleneck type |
| `db.user` | DB users by load | Find heavy user |
| `db.host` | Client hosts by load | Find heavy client |
| `db.database` | Databases by load | Find heavy database |
| `db.application` | Application by load | Find heavy app (PG only) |
| `db.session_type` | Session type breakdown | (Aurora only) |