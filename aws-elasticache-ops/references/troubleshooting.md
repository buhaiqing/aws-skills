# Troubleshooting — ElastiCache

## Common Error Codes

| Error | Action |
|-------|--------|
| ReplicationGroupAlreadyExists / CacheClusterAlreadyExists | HALT; use different ID (IDs are permanent per region) |
| CacheSubnetGroupNotFoundFault | HALT; create subnet group first |
| InvalidParameterValue / InvalidParameterCombination | Fix parameter; retry once |
| InsufficientCacheClusterCapacity | HALT; try different node type, AZ, or region |
| CacheClusterNotFoundFault / ReplicationGroupNotFoundFault | HALT; verify cluster ID and region |
| InvalidCacheClusterState / InvalidReplicationGroupState | HALT; wait for available status |
| DependencyViolation | HALT; remove all clusters using this resource first |
| Throttling (429) / ServiceUnavailable (5xx) | Backoff exponential; retry 3x; HALT if persists |

## Diagnostic Order

1. `aws sts get-caller-identity`
2. `aws elasticache describe-cache-subnet-groups --cache-subnet-group-name {{name}}`
3. `aws ec2 describe-security-groups --group-ids {{sg_ids}}`
4. `aws elasticache describe-replication-groups --replication-group-id {{id}}` or `describe-cache-clusters --cache-cluster-id {{id}}`
5. Check status: `creating`/`modifying`/`deleting` → wait; `available` → ok
6. For node issues: `describe-cache-clusters --cache-cluster-id {{id}} --show-cache-node-info`

## Common Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Create fails: "not enough capacity" | Node type unavailable in AZ | Try different node type, AZ, or region |
| Modify fails: "invalid state" | Cluster is creating/deleting/snapshotting | Wait for 'available' status |
| Connection timeout | Wrong endpoint or SG blocks | Verify endpoint; allow port 6379/11211 in SG |
| Auth failed | Wrong AUTH token or TLS mismatch | Verify token; check TLS configuration |
| High evictions / SwapUsage | Memory full | Scale up node type; increase TTL |
| Replication lag | Network or write-heavy workload on primary | Scale replicas; reduce write load |
| Cannot delete subnet group | Clusters still use it | Delete all dependent clusters first |
| Restore fails from snapshot | Snapshot corrupted or wrong region | Verify snapshot name and region |
| Redis: Primary failover | Primary node failure | Automatic; check new primary endpoint via `describe-replication-groups` |
| Memcached: No persistence | Memcached design limitation | Use Redis if persistence needed |

## Permissions

Use `aws iam simulate-custom-policy` to validate minimum actions: `elasticache:Create*`, `elasticache:Describe*`, `elasticache:Delete*`, `elasticache:Modify*`, `ec2:DescribeSubnets`, `ec2:DescribeSecurityGroups`.

## Recovery Actions

| Error | Max Retries | Action |
|-------|-------------|--------|
| 5xx ServiceUnavailable | 3 | Backoff 30s → 60s → 120s; HALT |
| 429 ThrottlingException | 3 | Exponential backoff |
| 400 InvalidParameterValue | 1 | Fix; retry once |
| 4xx Not Found / AlreadyExists | 0 | HALT; verify identifiers |
| 400 InsufficientCapacity | 0 | HALT; try different type/region |
| 400 InvalidState | 0 | HALT; wait for available |