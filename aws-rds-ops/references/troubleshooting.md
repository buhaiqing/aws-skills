# RDS Troubleshooting

Common RDS error codes, recovery procedures, and operational troubleshooting.

## Error Reference (by category)

### Instance Errors
| Error | Resolution |
|-------|-----------|
| DBInstanceAlreadyExists | HALT — use different identifier or modify existing |
| InvalidDBInstanceState | HALT — wait for `available` state (current: creating/modifying/deleting/stopped/upgrading) |
| DBInstanceNotFound | Verify identifier spelling, check region, or instance was deleted |
| InvalidDBInstanceClass | List valid classes: `describe-orderable-db-instance-options --engine {{engine}}` |

### Storage Errors
| Error | Resolution |
|-------|-----------|
| InsufficientStorageCapacity | Reduce size, try different AZ, use gp3 instead of io1/io2 |
| StorageTypeNotSupported | Use gp2/gp3 (supported by most engines) |
| StorageQuotaExceeded | Request quota increase, delete unused snapshots |

### Snapshot Errors
| Error | Resolution |
|-------|-----------|
| DBSnapshotAlreadyExists | Use unique name (timestamp-based: `mydb-snapshot-20260510-1200`) |
| DBSnapshotNotFound | Verify name, check region (snapshots are regional) |
| InvalidDBSnapshotState | Wait for `available` state before restore |

### Parameter Group Errors
| Error | Resolution |
|-------|-----------|
| DBParameterGroupNotFound | Create group first, or use default group |
| DBParameterGroupAlreadyExists | Use different name or modify existing |
| InvalidDBParameterGroupState | Instances using this group — modify them first |
```bash
# Check instances using a parameter group
aws rds describe-db-instances --query "DBInstances[?DBParameterGroups[?DBParameterGroupName=='{{name}}']]"
```

### Network/VPC Errors
| Error | Resolution |
|-------|-----------|
| InvalidVPCNetworkState | Verify subnet group has subnets in ≥2 AZs, check IP availability |
| DBSubnetGroupNotFound | Create subnet group or use default |
| DBSecurityGroupNotFound | Create EC2 security group first (`aws ec2 create-security-group`) |

### Permission Errors
| Error | Resolution |
|-------|-----------|
| AuthorizationNotFound | Add IAM permissions for RDS: `rds:CreateDBInstance`, `rds:DescribeDBInstances`, `rds:DeleteDBInstance` |
| KMSAccessDenied | Add KMS permissions: `kms:Encrypt`, `kms:Decrypt`, `kms:GenerateDataKey` |

### Quota Errors
| Limit | Default | Resolution |
|-------|---------|-----------|
| DB Instances | 40/region | Request quota increase via Service Quotas console |
| DB Snapshots | 100/region | Delete unused snapshots |
| Read Replicas/source | 5 | Reduce replicas |

## Throttling (429)
Exponential backoff strategy:
```python
import time, math
def exponential_backoff(attempt, base=0.5, max_delay=60):
    time.sleep(min(base * math.pow(2, attempt), max_delay))
```

## Connection Troubleshooting
| Symptom | Cause | Solution |
|---------|-------|----------|
| Timeout | Security group blocks IP | Add inbound rule for port/source IP |
| Timeout | Instance stopped | Start instance |
| Timeout | Wrong endpoint | Use `describe` to get correct endpoint |
| Refused | Wrong port | Use correct port (3306/5432) |
| Auth failed | Wrong credentials | Verify username/password |
| Auth failed | IAM auth/SSL issue | Configure IAM/SSL properly |

**Diagnostic steps**:
```bash
aws rds describe-db-instances --db-instance-identifier {{id}} --query "DBInstances[0].Endpoint"
nc -zv {{endpoint}} {{port}}  # TCP test from app host
aws ec2 describe-security-groups --group-ids {{sg_id}} --query "SecurityGroups[0].IpPermissions"
```

## Read Replica Issues
**ReplicaLag high**: Scale source/replica, monitor via CloudWatch `ReplicaLag` metric.
**Can't promote**: Source not available / replica initializing — wait and retry.

## Aurora Cluster Issues
**Cluster unavailable**: Check `describe-db-clusters` → `.DBClusterMembers`, no writer = failover needed.
**Instance addition failed**: Cluster not available / class unsupported / AZ capacity — wait, check options, try different AZ.
```bash
aws rds failover-db-cluster --db-cluster-identifier {{cluster}} --target-db-instance-identifier {{target}}
```

## Performance Issues
| Symptom | Diagnosis | Resolution |
|---------|-----------|-----------|
| High CPU | Performance Insights → Top SQL | Scale class, tune params, optimize queries, add indexes |
| High memory (SwapUsage>0) | Connections / buffer pool | Increase buffer pool, reduce max_connections, scale class |
| IOPS saturation (ReadLatency↑) | gp2/gp3 hitting limits | Increase storage (more baseline), switch to io1/io2, scale class |
| Slow queries | Slow query log / Performance Insights | Add indexes, tune params |

### SQL Slow Query Diagnosis Table

| Pattern | PI Wait Event | CW Log Signal | Root Cause | Recommendation |
|---------|---------------|---------------|------------|----------------|
| Full table scan | CPU high | `rows_examined >> rows_sent` | Missing index | `CREATE INDEX idx_<table>_<col> ON <table>(<col>)` |
| Lock contention | `Lock:RowLockWait` | High `Lock_time` | Long transaction scope | Reduce transaction size; use `NOWAIT`; index FK columns |
| Disk read storm | `IO:DataFileRead` | High IOPS, no index | Buffer pool insufficient | Increase `innodb_buffer_pool_size`; add covering index |
| Temp table on disk | CPU + IO | `Created_tmp_disk_tables` > 0 | Sort exceeds `tmp_table_size` | Increase `tmp_table_size` / `max_heap_table_size` |
| Bad join plan | CPU/IO | Inefficient JOIN | Wrong join order or missing FK index | Add composite index; use STRAIGHT_JOIN; update stats |
| Sync commit latency | `IO:XactSync` | High commit time | Sync log every transaction | `sync_binlog=0` (risk); batch commits; use SSD |
| Connection flood | `tcp:connection` | `max_connections` reached | Connection pool leak | Increase `max_connections`; fix app pool; use ProxySQL |
| Deadlock | `Lock:RowLockWait` | `Deadlock found` | Concurrent conflicting transactions | Retry logic; index order; reduce transaction time |
| Replica lag | N/A (on replica) | `Seconds_Behind_Master` > 0 | Write-heavy on source; slow replica | Scale replica; parallel replication; optimize source writes |
| Query timeout | CPU/IO mix | Queries > `long_query_time` | Insufficient instance size or IOPS | Scale class; add IOPS; optimize top SQL |

### Quick Reference: Key Diagnostic Commands

```bash
# 1. Check if PI enabled
aws rds describe-db-instances --db-instance-identifier {{id}} --query 'DBInstances[0].{PI:PerformanceInsightsEnabled,Retention:PerformanceInsightsRetentionPeriod,DbiResourceId}'

# 2. Check slow log publish
aws rds describe-db-instances --db-instance-identifier {{id}} --query 'DBInstances[0].EnabledCloudwatchLogsExports'

# 3. Get DbiResourceId (for PI API)
aws rds describe-db-instances --db-instance-identifier {{id}} --query 'DBInstances[0].DbiResourceId' --output text

# 4. PI: Top SQL by DB load (last 1h)
aws pi get-resource-metrics --service-type RDS --identifier <DbiResourceId> \
  --start-time $(date -u -d '-1 hour' +%s) --end-time $(date -u +%s) \
  --period-in-seconds 60 \
  --metric-queries '[{"Metric":"db.sproc_execution_time","GroupBy":{"Group":"db.sql_tokenized","Limit":10}}]'

# 5. PI: Wait event breakdown
aws pi get-resource-metrics --service-type RDS --identifier <DbiResourceId> \
  --start-time $(date -u -d '-1 hour' +%s) --end-time $(date -u +%s) \
  --period-in-seconds 60 \
  --metric-queries '[{"Metric":"db.sproc_execution_time","GroupBy":{"Group":"db.wait_event","Limit":10}}]'

# 6. CW: Top slow queries from slow log
aws logs start-query --log-group-name "/aws/rds/instance/{{id}}/slowquery" \
  --start-time $(date -u -d '-1 hour' +%s) --end-time $(date -u +%s) \
  --query-string 'fields @timestamp, @message | parse @message /Query_time: (?<qt>\\S+).*Rows_examined: (?<re>\\d+)/ | sort qt desc | limit 20'

# 7. MySQL: Current active queries
# Connect via mysql client:
# SELECT * FROM information_schema.PROCESSLIST WHERE COMMAND != 'Sleep' ORDER BY TIME DESC;

# 8. PG: Current active queries
# Connect via psql:
# SELECT pid, now() - pg_stat_activity.query_start AS duration, query, state
# FROM pg_stat_activity WHERE state != 'idle' ORDER BY duration DESC;
```

### MySQL Performance Schema Queries (connect to DB)
```sql
-- Top queries by total execution time
SELECT digest_text, count_star, sum_timer_wait / 1000000000000 AS total_sec,
       avg_timer_wait / 1000000000 AS avg_ms, sum_rows_examined, sum_rows_sent
FROM performance_schema.events_statements_summary_by_digest
ORDER BY sum_timer_wait DESC LIMIT 10;

-- Full table scans
SELECT * FROM sys.schema_unused_indexes;
SELECT * FROM sys.statements_with_full_table_scans;

-- Index suggestions
SELECT * FROM sys.schema_index_statistics WHERE rows_selected > 0 ORDER BY rows_selected DESC;
```

### PostgreSQL Query Diagnostics (connect to DB)
```sql
-- Slow queries by total time
SELECT query, calls, total_exec_time / 1000 AS total_sec,
       mean_exec_time AS avg_ms, rows, shared_blks_hit, shared_blks_read
FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 10;

-- Sequential scans (missing indexes)
SELECT schemaname, relname, seq_scan, seq_tup_read, idx_scan
FROM pg_stat_user_tables WHERE seq_scan > 1000 ORDER BY seq_scan DESC;

-- Index usage
SELECT schemaname, relname, indexrelname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes ORDER BY idx_scan ASC LIMIT 20;
```

## Backup/Snapshot Issues
**Snapshot hanging in `creating`**: Large DB takes time (hours). Check instance IOPS during snapshot. Multi-AZ = faster snapshots.
**Restore slow**: Large snapshot / small instance class. Use larger class for faster restore.

## Delete Operation Issues
**Blocked by read replicas**:
```bash
aws rds describe-db-instances --query "DBInstances[?ReadReplicaSourceDBInstanceIdentifier=='{{source}}']"
# Delete/promote replicas first, then delete source
```
**Blocked by deletion protection**:
```bash
aws rds modify-db-instance --db-instance-identifier {{id}} --no-deletion-protection --apply-immediately
aws rds wait db-instance-available --db-instance-identifier {{id}}
aws rds delete-db-instance --db-instance-identifier {{id}} --final-db-snapshot-identifier {{snap}}
```
**Aurora cluster**: Delete all instances in cluster first, then delete cluster.

## Parameter Group Issues
**Static param not applied**: Reboot instance — `aws rds reboot-db-instance --db-instance-identifier {{id}}`
**Invalid param value**: Check constraints with `describe-engine-default-parameters`

## Monitoring Alerts
| Alert | Threshold | Action |
|-------|-----------|--------|
| FreeStorageSpace low | < 10% | Enable auto-scaling or manually increase |
| DatabaseConnections high | > 90% max_connections | Increase max_connections, check connection leaks |
| SwapUsage > 0 | Any | Memory pressure — increase buffer pool, scale class |

## Recovery Procedures
**Instance**: Identify error → check state → apply fix (retry once) → HALT if persistent, backoff for throttling (max 3).
**Connection**: Check state → verify endpoint → test TCP → check SG → verify creds → apply fix.
**Snapshot**: Wait `available` → restore → validate → update app endpoints → monitor.