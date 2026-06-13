# Aurora Troubleshooting

## Error Reference

| Error | Resolution |
|-------|-----------|
| DBClusterAlreadyExists | HALT — use different identifier or modify existing |
| DBClusterNotFoundFault | Verify cluster id and region |
| InvalidDBClusterStateFault | Wait for `available`; check `describe-db-clusters` Status |
| InvalidDBInstanceState | Instance creating/modifying — wait before failover/delete |
| InsufficientDBClusterCapacity | Try different instance class or AZ |
| DBClusterSnapshotAlreadyExistsFault | Use unique snapshot name with timestamp |
| GlobalClusterAlreadyExistsFault | Use different global cluster identifier |
| InvalidDBClusterStateFault (backtrack) | Enable backtrack window first; time must be within window |

## Failover Issues

| Symptom | Cause | Solution |
|---------|-------|----------|
| Failover slow | No healthy reader | Add reader instance before planned failover |
| App errors post-failover | Cached writer endpoint | Use cluster endpoint (auto-follows writer) |
| Replica lag spike | Heavy write load | Scale writer class; add readers |

```bash
aws rds describe-db-clusters --db-cluster-identifier {{id}} \
  --query "DBClusters[0].{Status:Status,Members:DBClusterMembers}" --output json
aws cloudwatch get-metric-statistics --namespace AWS/RDS \
  --metric-name AuroraReplicaLag --dimensions Name=DBClusterIdentifier,Value={{id}} \
  --start-time $(date -u -d '-1 hour' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) --period 60 --statistics Maximum --output json
```

## Connection Issues

| Symptom | Cause | Solution |
|---------|-------|----------|
| Timeout | SG blocks client IP | Allow port 3306/5432 from app subnet/SG |
| Read on writer | Using cluster endpoint for reads | Use reader endpoint or custom endpoint |
| Too many connections | Pool misconfigured | Tune `max_connections`; use RDS Proxy |

## Serverless v2

| Symptom | Cause | Solution |
|---------|-------|----------|
| Capacity capped | MaxCapacity too low | Raise `MaxCapacity` on instance/cluster |
| Cold start latency | MinCapacity=0.5 with idle workload | Set MinCapacity to steady-state need |

## Throttling (429)

Exponential backoff: 0.5s → 1s → 2s → 4s (max 3 retries), then HALT.

## Global Database

| Symptom | Cause | Solution |
|---------|-------|----------|
| High lag | Network or write burst | Monitor `AuroraGlobalDBReplicationLag`; scale primary |
| Cannot delete global cluster | Secondaries still attached | `remove-from-global-cluster` on each secondary first |

## Permission Errors

| Error | Resolution |
|-------|-----------|
| AccessDenied on `rds:*` | IAM policy needs cluster-scoped actions |
| KMSAccessDenied | Grant `kms:Decrypt`, `kms:GenerateDataKey` on cluster KMS key |
