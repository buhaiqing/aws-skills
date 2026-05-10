# Troubleshooting — ElastiCache

## Common Error Codes

| Error Code | HTTP | Meaning | Agent Action |
|------------|------|---------|--------------|
| ReplicationGroupAlreadyExists | 400 | Group ID exists | HALT; use different ID |
| CacheClusterAlreadyExists | 400 | Cluster ID exists | HALT; use different ID |
| CacheSubnetGroupNotFoundFault | 404 | Subnet group not found | HALT; create subnet group first |
| InvalidParameterValue | 400 | Parameter value invalid | Fix parameter; retry once |
| InvalidParameterCombination | 400 | Parameters conflict | Fix config; retry once |
| InsufficientCacheClusterCapacity | 400 | Not enough capacity | HALT; different node type |
| CacheClusterNotFoundFault | 404 | Cluster not found | HALT; verify cluster ID |
| ReplicationGroupNotFoundFault | 404 | Replication group not found | HALT; verify group ID |
| InvalidCacheClusterState | 400 | Cluster not in valid state | HALT; wait for available |
| InvalidReplicationGroupState | 400 | Group not in valid state | HALT; wait for available |
| SnapshotNotFoundFault | 404 | Snapshot not found | HALT; verify snapshot name |
| SnapshotAlreadyExistsFault | 400 | Snapshot name exists | HALT; use different name |
| AuthorizationNotFoundFault | 404 | Security group not found | HALT; verify SG |
| DependencyViolation | 400 | Cannot delete (dependencies) | Remove dependencies first |
| ThrottlingException | 429 | Too many requests | Backoff; retry 3x |
| ServiceUnavailable | 500 | ElastiCache service issue | Retry 3x; HALT if persists |

## Diagnostic Order

1. **Verify credentials**: `aws sts get-caller-identity`
2. **Verify subnet group**: `aws elasticache describe-cache-subnet-groups`
3. **Verify security groups**: `aws ec2 describe-security-groups`
4. **Verify cluster exists**: `aws elasticache describe-cache-clusters --cache-cluster-id {{id}}`
5. **Verify replication group**: `aws elasticache describe-replication-groups --replication-group-id {{id}}`
6. **Check cluster status**: Look for creating/modifying/deleting states
7. **Check node health**: Describe with `--show-cache-node-info`

## Common Issues

### ReplicationGroupAlreadyExists / CacheClusterAlreadyExists

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Create fails | ID already used | Use unique ID (IDs are permanent per region) |
| ID reused after delete | ElastiCache retains deleted ID briefly | Wait or use different ID |

### CacheSubnetGroupNotFoundFault

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Create fails | Subnet group doesn't exist | Create subnet group first |
| Invalid subnet | Subnet not in correct VPC | Use subnets from same VPC |

### InsufficientCacheClusterCapacity

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Create fails | Node type unavailable in AZ | Try different node type |
| Scale-up fails | Capacity limits | Try different AZ or node type |

### InvalidCacheClusterState / InvalidReplicationGroupState

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Modify fails | Cluster creating | Wait for 'available' status |
| Delete fails | Snapshot in progress | Wait for snapshot to complete |
| Scale fails | Scaling already in progress | Wait for current operation |

### CacheClusterNotFoundFault / ReplicationGroupNotFoundFault

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Describe fails | Wrong ID or region | Verify ID and region |
| Cluster deleted | Already deleted | Recreate if needed |
| Wrong engine type | Redis vs Memcached commands | Use correct command type |

### DependencyViolation

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Cannot delete subnet group | Clusters using it | Delete all clusters first |
| Cannot delete parameter group | Clusters using it | Modify clusters to use different group |

### Snapshot Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| SnapshotAlreadyExists | Name already used | Use unique snapshot name |
| SnapshotNotFound | Wrong name | Verify snapshot exists |
| Restore fails | Snapshot corrupted | Try different snapshot |
| Snapshot too slow | Large dataset | Wait longer (check status) |

### Connection Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Connection refused | Security group blocks | Allow port 6379/11211 in SG |
| Connection timeout | Wrong endpoint | Verify endpoint address |
| Auth failed | Wrong auth token | Verify auth token matches |
| TLS errors | Certificate mismatch | Check TLS configuration |

### Performance Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| High latency | Memory pressure | Scale up node type |
| Evictions | Memory full | Increase memory or TTL |
| Swap usage | Memory exceeded | Scale up immediately |
| High CPU | Redis single-thread | Scale up or use cluster mode |

### Redis-Specific Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Replication lag | Network/write-heavy | Scale replicas or reduce writes |
| Primary failover | Primary failure | Automatic; check new primary endpoint |
| Cluster slot imbalance | Uneven data distribution | Rebalance slots |
| AOF rewrite slow | Large dataset | Monitor, may need larger node |

### Memcached-Specific Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Uneven distribution | Slab allocation | Configure slab sizes |
| Connection limits | Too many connections | Scale nodes |
| No persistence | Memcached design | Use Redis if persistence needed |

## Permissions Required

| Action | Minimum IAM Permissions |
|--------|-------------------------|
| Create cluster | `elasticache:CreateCacheCluster` |
| Describe clusters | `elasticache:DescribeCacheClusters` |
| Delete cluster | `elasticache:DeleteCacheCluster` |
| Create replication group | `elasticache:CreateReplicationGroup` |
| Describe replication groups | `elasticache:DescribeReplicationGroups` |
| Delete replication group | `elasticache:DeleteReplicationGroup` |
| Create snapshot | `elasticache:CreateSnapshot` |
| Describe snapshots | `elasticache:DescribeSnapshots` |
| Create subnet group | `elasticache:CreateCacheSubnetGroup` |
| Describe subnet groups | `elasticache:DescribeCacheSubnetGroups` |
| Modify replication group | `elasticache:ModifyReplicationGroup` |
| Describe EC2 subnets | `ec2:DescribeSubnets` |
| Describe EC2 security groups | `ec2:DescribeSecurityGroups` |

## Cleanup Sequence (Delete Replication Group)

```
1. Create final snapshot: create-snapshot
2. Wait for snapshot complete (poll)
3. Delete replication group: delete-replication-group
4. Wait for deletion complete (poll)
5. Delete subnet group (if no other clusters): delete-cache-subnet-group
```

## Cleanup Sequence (Delete Cache Cluster)

```
1. Create final snapshot: create-snapshot (optional)
2. Delete cache cluster: delete-cache-cluster
3. Wait for deletion complete (poll)
```

## Health Check Commands

```bash
# Replication group status
aws elasticache describe-replication-groups \
  --replication-group-id {{group_id}} \
  --output json | jq '.ReplicationGroups[0].Status'

# Cache cluster status
aws elasticache describe-cache-clusters \
  --cache-cluster-id {{cluster_id}} \
  --output json | jq '.CacheClusters[0].CacheClusterStatus'

# Node information
aws elasticache describe-cache-clusters \
  --cache-cluster-id {{cluster_id}} \
  --show-cache-node-info \
  --output json | jq '.CacheClusters[0].CacheNodes'

# Snapshot status
aws elasticache describe-snapshots \
  --snapshot-name {{snapshot_name}} \
  --output json | jq '.Snapshots[0].SnapshotStatus'
```

## Endpoint Connection Testing

```bash
# Redis connection test
redis-cli -h {{endpoint}} -p 6379 ping

# Redis with auth
redis-cli -h {{endpoint}} -p 6379 -a {{auth_token}} ping

# Redis with TLS
redis-cli -h {{endpoint}} -p 6379 --tls ping

# Memcached connection test
telnet {{endpoint}} 11211
stats
quit

# Or with nc
echo "stats" | nc {{endpoint}} 11211
```

## Recovery Actions

| Error | Max Retries | Action |
|-------|-------------|--------|
| 5xx ServiceUnavailable | 3 | Backoff 30s, 60s, 120s; HALT after 3 |
| 429 ThrottlingException | 3 | Exponential backoff |
| 400 InvalidParameterValue | 1 | Fix; retry once |
| 400 ReplicationGroupAlreadyExists | 0 | HALT; use different ID |
| 400 InsufficientCacheClusterCapacity | 0 | HALT; try different node type |
| 404 CacheClusterNotFoundFault | 0 | HALT; verify ID |
| 404 CacheSubnetGroupNotFoundFault | 0 | HALT; create subnet group |

## CloudWatch Metrics for Troubleshooting

| Metric | Redis | Memcached | Purpose |
|--------|-------|-----------|---------|
| CacheHitRate | ✅ | ✅ | Effectiveness |
| Evictions | ✅ | ✅ | Memory pressure |
| BytesUsedForCache | ✅ | ✅ | Memory usage |
| SwapUsage | ✅ | ✅ | Memory overflow |
| CPUUtilization | ✅ | ✅ | CPU load |
| CurrentConnections | ✅ | ✅ | Connection count |
| ReplicationLag | ✅ | — | Replica health |
| GetCmds/SetCmds | ✅ | ✅ | Command rate |
| NetworkBytesIn/Out | ✅ | ✅ | Bandwidth |

## Common Parameter Tuning

```bash
# View current parameters
aws elasticache describe-cache-parameters \
  --cache-parameter-group-name {{param_group}} \
  --output json

# Modify Redis parameters
aws elasticache modify-cache-parameter-group \
  --cache-parameter-group-name my-redis-params \
  --parameter-name-values \
    ParameterName=maxmemory-policy,ParameterValue=allkeys-lru \
    ParameterName=timeout,ParameterValue=300 \
  --output json

# Apply to cluster
aws elasticache modify-cache-cluster \
  --cache-cluster-id my-redis \
  --cache-parameter-group-name my-redis-params \
  --apply-immediately \
  --output json
```