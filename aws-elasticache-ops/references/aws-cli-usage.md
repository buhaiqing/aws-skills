# AWS CLI Usage — ElastiCache

## Common JSON Paths (Centralized)

```
# Create Repl Group:    .ReplicationGroup.{ARN,Status,PrimaryEndpoint}
# Describe Repl Group:  .ReplicationGroups[].{Status,MemberClusters,PrimaryEndpoint,ReaderEndpoint}
# Create Cache Cluster: .CacheCluster.{ARN,Status,CacheNodes}
# Describe Cache:       .CacheClusters[].{CacheClusterStatus,CacheNodes,CacheNodeType}
# Create Snapshot:      .Snapshot.{ARN,Status}
# Create Subnet Group:  .CacheSubnetGroup.{ARN}
# Modify:               .ReplicationGroup.Status
# Increase/Decrease:    .ReplicationGroup.Status
```

## Command Map

| Goal | CLI Command |
|------|-------------|
| Create Redis Replication Group | `aws elasticache create-replication-group` |
| Describe Replication Groups | `aws elasticache describe-replication-groups` |
| Delete Replication Group | `aws elasticache delete-replication-group` |
| Create Cache Cluster | `aws elasticache create-cache-cluster` |
| Describe Cache Clusters | `aws elasticache describe-cache-clusters` |
| Delete Cache Cluster | `aws elasticache delete-cache-cluster` |
| Create Snapshot | `aws elasticache create-snapshot` |
| Describe Snapshots | `aws elasticache describe-snapshots` |
| Create Subnet Group | `aws elasticache create-cache-subnet-group` |
| Modify Replication Group | `aws elasticache modify-replication-group` |
| Increase/Decrease Replica | `aws elasticache increase/decrease-replica-count` |
| List Allowed Node Types | `aws elasticache list-allowed-node-type-modifications` |

## Common Patterns

### Create Redis Replication Group (Primary + Read Replicas)
```bash
aws elasticache create-replication-group \
  --replication-group-id my-redis-cluster \
  --replication-group-description "Production Redis cluster" \
  --engine redis --engine-version 7.0 \
  --cache-node-type cache.m5.large \
  --num-cache-clusters 3 \
  --cache-subnet-group-name my-cache-subnet \
  --security-group-ids sg-aaa \
  --automatic-failover-enabled --multi-az-enabled \
  --at-rest-encryption-enabled --transit-encryption-enabled
```

### Create Redis Cluster Mode Enabled (Sharding)
```bash
aws elasticache create-replication-group \
  --replication-group-id my-redis-sharded \
  --replication-group-description "Redis Cluster mode" \
  --engine redis --cache-node-type cache.r5.large \
  --replicas-per-node-group 2 --num-node-groups 3 \
  --cache-subnet-group-name my-cache-subnet \
  --security-group-ids sg-aaa --cluster-mode enabled
```

### Create Memcached Cluster
```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id my-memcached --engine memcached --engine-version 1.6 \
  --cache-node-type cache.m5.large --num-cache-nodes 3 \
  --cache-subnet-group-name my-cache-subnet \
  --security-group-ids sg-aaa --az-mode cross-az
```

### Create Single Redis Node
```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id my-redis-single --engine redis --engine-version 7.0 \
  --cache-node-type cache.t3.medium \
  --cache-subnet-group-name my-cache-subnet --security-group-ids sg-aaa
```

### Subnet Group
```bash
aws elasticache create-cache-subnet-group \
  --cache-subnet-group-name my-cache-subnet \
  --cache-subnet-group-description "ElastiCache subnet group" \
  --subnet-ids subnet-aaa subnet-bbb subnet-ccc
```

### Describe / Query Endpoints
```bash
aws elasticache describe-replication-groups --replication-group-id my-redis-cluster
aws elasticache describe-cache-clusters --cache-cluster-id my-memcached --show-cache-node-info
# Get primary endpoint
aws elasticache describe-replication-groups --replication-group-id my-redis --query 'ReplicationGroups[0].PrimaryEndpoint'
# Get reader endpoint
aws elasticache describe-replication-groups --replication-group-id my-redis --query 'ReplicationGroups[0].ReaderEndpoint'
```

### Replica Count / Modify / Scale
```bash
aws elasticache increase-replica-count --replication-group-id my-redis-cluster --new-replica-count 4 --apply-immediately
aws elasticache decrease-replica-count --replication-group-id my-redis-cluster --new-replica-count 2 --apply-immediately
aws elasticache modify-replication-group --replication-group-id my-redis-cluster --cache-node-type cache.r5.large --apply-immediately
aws elasticache modify-cache-cluster --cache-cluster-id my-redis-single --cache-parameter-group-name my-param-group --apply-immediately
aws elasticache list-allowed-node-type-modifications --replication-group-id my-redis-cluster
```

### Parameter Group
```bash
aws elasticache create-cache-parameter-group \
  --cache-parameter-group-name my-redis-params \
  --cache-parameter-group-family redis7 \
  --description "Custom Redis parameters"
aws elasticache modify-cache-parameter-group \
  --cache-parameter-group-name my-redis-params \
  --parameter-name-values ParameterName=maxmemory-policy,ParameterValue=allkeys-lru
```

### Snapshot / Restore
```bash
aws elasticache create-snapshot --snapshot-name my-snapshot --replication-group-id my-redis-cluster
aws elasticache describe-snapshots --snapshot-name my-snapshot
aws elasticache delete-snapshot --snapshot-name my-snapshot
# Restore from snapshot (Redis)
aws elasticache create-replication-group --replication-group-id restored-redis \
  --engine redis --cache-node-type cache.m5.large --num-cache-clusters 3 \
  --snapshot-name my-snapshot --cache-subnet-group-name my-cache-subnet --security-group-ids sg-aaa
```

### Delete (Safety Gate Required)
```bash
aws elasticache delete-replication-group --replication-group-id my-redis-cluster --final-snapshot-identifier final-backup
aws elasticache delete-cache-cluster --cache-cluster-id my-memcached --final-snapshot-identifier final-backup
aws elasticache delete-cache-subnet-group --cache-subnet-group-name my-cache-subnet
```