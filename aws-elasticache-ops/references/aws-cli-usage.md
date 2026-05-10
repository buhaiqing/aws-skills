# AWS CLI Usage — ElastiCache

## Command Map

| Goal | CLI Command | JSON Output Path |
|------|-------------|------------------|
| Create cache cluster | `aws elasticache create-cache-cluster` | `.CacheCluster.ARN` |
| Describe cache clusters | `aws elasticache describe-cache-clusters` | `.CacheClusters[]` |
| Delete cache cluster | `aws elasticache delete-cache-cluster` | Empty (success) |
| Create replication group | `aws elasticache create-replication-group` | `.ReplicationGroup.ARN` |
| Describe replication groups | `aws elasticache describe-replication-groups` | `.ReplicationGroups[]` |
| Delete replication group | `aws elasticache delete-replication-group` | Empty (success) |
| Create snapshot | `aws elasticache create-snapshot` | `.Snapshot.ARN` |
| Describe snapshots | `aws elasticache describe-snapshots` | `.Snapshots[]` |
| Delete snapshot | `aws elasticache delete-snapshot` | Empty (success) |
| Create subnet group | `aws elasticache create-cache-subnet-group` | `.CacheSubnetGroup.ARN` |
| Describe subnet groups | `aws elasticache describe-cache-subnet-groups` | `.CacheSubnetGroups[]` |
| Delete subnet group | `aws elasticache delete-cache-subnet-group` | Empty (success) |
| Modify replication group | `aws elasticache modify-replication-group` | `.ReplicationGroup.ARN` |
| Increase replica count | `aws elasticache increase-replica-count` | `.ReplicationGroup.ARN` |
| Decrease replica count | `aws elasticache decrease-replica-count` | `.ReplicationGroup.ARN` |
| List allowed node types | `aws elasticache list-allowed-node-type-modifications` | `.ScaleUpModifications[]` |

## Key CLI Conventions

### Regional Service
ElastiCache is **regional** — region parameter required.

### Output Format
Always use `--output json` for agent parsing.

### Cluster Status Values
- `creating` — Cluster being created
- `available` — Cluster ready for use
- `modifying` — Cluster being modified
- `deleting` — Cluster being deleted
- `snapshotting` — Snapshot in progress
- `restore-failed` — Restore from snapshot failed
- `incompatible-network` — Network configuration issue

## Common Patterns

### Create Redis Replication Group (Primary + Read Replicas)

```bash
aws elasticache create-replication-group \
  --replication-group-id my-redis-cluster \
  --replication-group-description "Production Redis cluster" \
  --engine redis \
  --engine-version 7.0 \
  --cache-node-type cache.m5.large \
  --num-cache-clusters 3 \
  --cache-subnet-group-name my-cache-subnet \
  --security-group-ids sg-aaa \
  --automatic-failover-enabled \
  --multi-az-enabled \
  --at-rest-encryption-enabled \
  --transit-encryption-enabled \
  --auth-token my-auth-token \
  --output json
```

### Create Redis Cluster Mode Enabled (Sharding)

```bash
aws elasticache create-replication-group \
  --replication-group-id my-redis-sharded \
  --replication-group-description "Redis Cluster mode enabled" \
  --engine redis \
  --cache-node-type cache.r5.large \
  --replicas-per-node-group 2 \
  --num-node-groups 3 \
  --cache-subnet-group-name my-cache-subnet \
  --security-group-ids sg-aaa \
  --cluster-mode enabled \
  --output json
```

### Create Memcached Cluster

```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id my-memcached \
  --engine memcached \
  --engine-version 1.6 \
  --cache-node-type cache.m5.large \
  --num-cache-nodes 3 \
  --cache-subnet-group-name my-cache-subnet \
  --security-group-ids sg-aaa \
  --az-mode cross-az \
  --output json
```

### Create Single Redis Node (No Replication)

```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id my-redis-single \
  --engine redis \
  --engine-version 7.0 \
  --cache-node-type cache.t3.medium \
  --cache-subnet-group-name my-cache-subnet \
  --security-group-ids sg-aaa \
  --output json
```

### Create Cache Subnet Group

```bash
aws elasticache create-cache-subnet-group \
  --cache-subnet-group-name my-cache-subnet \
  --cache-subnet-group-description "ElastiCache subnet group" \
  --subnet-ids subnet-aaa subnet-bbb subnet-ccc \
  --output json
```

### Describe Replication Groups

```bash
aws elasticache describe-replication-groups \
  --replication-group-id my-redis-cluster \
  --output json

# Get primary endpoint
aws elasticache describe-replication-groups \
  --replication-group-id my-redis-cluster \
  --output json --query 'ReplicationGroups[0].PrimaryEndpoint.Address'
```

### Describe Cache Clusters

```bash
aws elasticache describe-cache-clusters \
  --cache-cluster-id my-memcached \
  --show-cache-node-info \
  --output json

# Get cluster endpoint
aws elasticache describe-cache-clusters \
  --cache-cluster-id my-memcached \
  --output json --query 'CacheClusters[0].CacheNodes[0].Endpoint.Address'
```

### List All Cache Clusters

```bash
aws elasticache describe-cache-clusters --output json

# Pagination
aws elasticache describe-cache-clusters \
  --max-items 20 \
  --output json
```

### Add Read Replica to Redis

```bash
aws elasticache increase-replica-count \
  --replication-group-id my-redis-cluster \
  --new-replica-count 4 \
  --apply-immediately \
  --output json
```

### Remove Read Replica

```bash
aws elasticache decrease-replica-count \
  --replication-group-id my-redis-cluster \
  --new-replica-count 2 \
  --replica-ids-to-remove my-redis-cluster-003 \
  --apply-immediately \
  --output json
```

### Modify Replication Group (Scale Up)

```bash
aws elasticache modify-replication-group \
  --replication-group-id my-redis-cluster \
  --cache-node-type cache.r5.large \
  --apply-immediately \
  --output json
```

### Modify Cache Cluster Parameters

```bash
aws elasticache modify-cache-cluster \
  --cache-cluster-id my-redis-single \
  --cache-parameter-group-name my-param-group \
  --apply-immediately \
  --output json
```

### Create Parameter Group

```bash
aws elasticache create-cache-parameter-group \
  --cache-parameter-group-name my-redis-params \
  --cache-parameter-group-family redis7 \
  --description "Custom Redis parameters" \
  --output json
```

### Modify Parameter Group Parameters

```bash
aws elasticache modify-cache-parameter-group \
  --cache-parameter-group-name my-redis-params \
  --parameter-name-values ParameterName=maxmemory-policy,ParameterValue=allkeys-lru \
  --output json
```

### Create Snapshot

```bash
aws elasticache create-snapshot \
  --snapshot-name my-snapshot-20260510 \
  --replication-group-id my-redis-cluster \
  --output json

# Or for single cache cluster
aws elasticache create-snapshot \
  --snapshot-name my-snapshot-20260510 \
  --cache-cluster-id my-redis-single \
  --output json
```

### Describe Snapshots

```bash
aws elasticache describe-snapshots \
  --snapshot-name my-snapshot-20260510 \
  --output json
```

### Restore from Snapshot (Redis)

```bash
aws elasticache create-replication-group \
  --replication-group-id restored-redis \
  --replication-group-description "Restored from snapshot" \
  --engine redis \
  --cache-node-type cache.m5.large \
  --num-cache-clusters 3 \
  --snapshot-name my-snapshot-20260510 \
  --cache-subnet-group-name my-cache-subnet \
  --security-group-ids sg-aaa \
  --output json
```

### Restore from Snapshot (Memcached)

```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id restored-memcached \
  --engine memcached \
  --cache-node-type cache.m5.large \
  --num-cache-nodes 3 \
  --snapshot-name my-snapshot-20260510 \
  --cache-subnet-group-name my-cache-subnet \
  --security-group-ids sg-aaa \
  --output json
```

### Delete Snapshot

```bash
aws elasticache delete-snapshot \
  --snapshot-name my-snapshot-20260510 \
  --output json
```

### Delete Cache Cluster (Safety Gate Required)

```bash
# Safety Gate: Confirm with user before deletion
aws elasticache delete-cache-cluster \
  --cache-cluster-id my-memcached \
  --final-snapshot-identifier final-snapshot-20260510 \
  --output json
```

### Delete Replication Group (Safety Gate Required)

```bash
# Safety Gate: Confirm with user before deletion
aws elasticache delete-replication-group \
  --replication-group-id my-redis-cluster \
  --final-snapshot-identifier final-snapshot-20260510 \
  --output json
```

### Delete Subnet Group

```bash
# Must have no clusters using the subnet group
aws elasticache delete-cache-subnet-group \
  --cache-subnet-group-name my-cache-subnet \
  --output json
```

### List Allowed Node Type Modifications

```bash
aws elasticache list-allowed-node-type-modifications \
  --replication-group-id my-redis-cluster \
  --output json

# Or for cache cluster
aws elasticache list-allowed-node-type-modifications \
  --cache-cluster-id my-memcached \
  --output json
```

## ARN Format

| Resource | ARN Pattern |
|----------|-------------|
| Cache Cluster | `arn:aws:elasticache:region:account:cluster:name` |
| Replication Group | `arn:aws:elasticache:region:account:cluster:name` |
| Snapshot | `arn:aws:elasticache:region:account:snapshot:name` |
| Subnet Group | `arn:aws:elasticache:region:account:subnetgroup:name` |
| Parameter Group | `arn:aws:elasticache:region:account:parametergroup:name` |

## Engine Versions

### Redis Versions
| Version | Status |
|---------|--------|
| 7.2 | Latest |
| 7.0 | Supported |
| 6.2 | Supported |
| 6.0 | Supported |
| 5.0.6 | Legacy |

### Memcached Versions
| Version | Status |
|---------|--------|
| 1.6.22 | Latest |
| 1.6.17 | Supported |
| 1.5.10 | Legacy |

## Status Values

| Resource | Status Values |
|----------|---------------|
| Cache Cluster | creating, available, modifying, deleting, snapshotting |
| Replication Group | creating, available, modifying, deleted, snapshotting |
| Snapshot | creating, available, copying, deleted |

## Endpoint Access

```bash
# Redis Primary endpoint
aws elasticache describe-replication-groups \
  --replication-group-id my-redis \
  --query 'ReplicationGroups[0].PrimaryEndpoint'

# Redis Reader endpoint (for read replicas)
aws elasticache describe-replication-groups \
  --replication-group-id my-redis \
  --query 'ReplicationGroups[0].ReaderEndpoint'

# Memcached cluster endpoint
aws elasticache describe-cache-clusters \
  --cache-cluster-id my-memcached \
  --show-cache-node-info \
  --query 'CacheClusters[0].CacheNodes[0].Endpoint'
```

## Credential Handling

CLI reads credentials in priority order:
1. Environment: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
2. Config file: `~/.aws/credentials`
3. IAM role (EC2/Lambda)

Verify:
```bash
aws sts get-caller-identity --output json
```