# AWS CLI Usage — ElastiCache

Common JSON paths are centralized in `SKILL.md`. Always use `--output json`.

## Command Map

| Goal | CLI Command |
|------|-------------|
| Create Redis Replication Group | `aws elasticache create-replication-group` |
| Describe Replication Groups | `aws elasticache describe-replication-groups` |
| Modify Replication Group | `aws elasticache modify-replication-group` |
| Increase/Decrease Replica | `aws elasticache increase-replica-count` / `decrease-replica-count` |
| Delete Replication Group | `aws elasticache delete-replication-group` |
| Create Cache Cluster | `aws elasticache create-cache-cluster` |
| Describe Cache Clusters | `aws elasticache describe-cache-clusters` |
| Delete Cache Cluster | `aws elasticache delete-cache-cluster` |
| Snapshot | `aws elasticache create-snapshot` / `describe-snapshots` / `delete-snapshot` |
| Subnet Group | `aws elasticache create-cache-subnet-group` / `describe-cache-subnet-groups` / `delete-cache-subnet-group` |
| Parameter Group | `aws elasticache create-cache-parameter-group` / `describe-cache-parameters` / `modify-cache-parameter-group` |
| List Allowed Node Types | `aws elasticache list-allowed-node-type-modifications` |

## Core Patterns

```bash
# Create Redis Replication Group (HA)
aws elasticache create-replication-group \
  --replication-group-id my-cluster \
  --replication-group-description "Prod cluster" \
  --engine redis --cache-node-type cache.m5.large \
  --num-cache-clusters 3 --automatic-failover-enabled \
  --cache-subnet-group-name my-sg --security-group-ids sg-xxx

# Create Redis Cluster Mode (sharded)
aws elasticache create-replication-group \
  --replication-group-id my-shard --engine redis \
  --cache-node-type cache.r5.large \
  --replicas-per-node-group 2 --num-node-groups 3 --cluster-mode enabled \
  --cache-subnet-group-name my-sg --security-group-ids sg-xxx

# Create Memcached Cluster
aws elasticache create-cache-cluster \
  --cache-cluster-id my-memcached --engine memcached \
  --cache-node-type cache.m5.large --num-cache-nodes 3 \
  --cache-subnet-group-name my-sg --security-group-ids sg-xxx

# Get endpoints
aws elasticache describe-replication-groups \
  --replication-group-id my-cluster --query 'ReplicationGroups[0].{Primary:PrimaryEndpoint,Reader:ReaderEndpoint}'

aws elasticache describe-cache-clusters \
  --cache-cluster-id my-memcached --show-cache-node-info \
  --query 'CacheClusters[0].CacheNodes[].{ID:CacheNodeId,Endpoint:Endpoint}'

# Scale
aws elasticache modify-replication-group \
  --replication-group-id my-cluster --cache-node-type cache.r5.large --apply-immediately
aws elasticache increase-replica-count \
  --replication-group-id my-cluster --new-replica-count 4 --apply-immediately
aws elasticache list-allowed-node-type-modifications --replication-group-id my-cluster

# Parameter Group
aws elasticache create-cache-parameter-group \
  --cache-parameter-group-name my-params --cache-parameter-group-family redis7 \
  --description "Custom params"
aws elasticache modify-cache-parameter-group \
  --cache-parameter-group-name my-params \
  --parameter-name-values ParameterName=maxmemory-policy,ParameterValue=allkeys-lru

# Snapshot / Restore
aws elasticache create-snapshot --snapshot-name my-snap --replication-group-id my-cluster
aws elasticache create-replication-group --replication-group-id restored-cluster \
  --engine redis --cache-node-type cache.m5.large \
  --num-cache-clusters 3 --snapshot-name my-snap \
  --cache-subnet-group-name my-sg --security-group-ids sg-xxx

# Delete (Safety Gate Required: confirm with user first)
aws elasticache delete-replication-group \
  --replication-group-id my-cluster --final-snapshot-identifier final-backup
aws elasticache delete-cache-cluster \
  --cache-cluster-id my-memcached --final-snapshot-identifier final-backup
```