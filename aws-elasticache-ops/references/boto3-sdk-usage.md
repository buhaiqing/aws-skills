# boto3 SDK Usage — ElastiCache

## Client Initialization

```python
import boto3
client = boto3.client('elasticache', region_name='us-east-1')
```

## Create

```python
# Redis Replication Group
resp = client.create_replication_group(
    ReplicationGroupId='my-cluster', ReplicationGroupDescription='Prod cluster',
    Engine='redis', EngineVersion='7.0', CacheNodeType='cache.m5.large',
    NumCacheClusters=3, CacheSubnetGroupName='my-sg', SecurityGroupIds=['sg-xxx'],
    AutomaticFailoverEnabled=True, MultiAZEnabled=True,
    AtRestEncryptionEnabled=True, TransitEncryptionEnabled=True, AuthToken='{{auth}}',
    Tags=[{'Key': 'Env', 'Value': 'prod'}])

# Redis Cluster Mode (sharded)
resp = client.create_replication_group(
    ReplicationGroupId='my-shard', Engine='redis', CacheNodeType='cache.r5.large',
    ReplicasPerNodeGroup=2, NumNodeGroups=3, CacheSubnetGroupName='my-sg',
    SecurityGroupIds=['sg-xxx'], ClusterMode='enabled')

# Memcached Cluster
resp = client.create_cache_cluster(
    CacheClusterId='my-memcached', Engine='memcached', CacheNodeType='cache.m5.large',
    NumCacheNodes=3, CacheSubnetGroupName='my-sg', SecurityGroupIds=['sg-xxx'], AZMode='cross-az')

# Single Redis Node (via cache cluster)
resp = client.create_cache_cluster(
    CacheClusterId='my-redis-single', Engine='redis', EngineVersion='7.0',
    CacheNodeType='cache.t3.medium', CacheSubnetGroupName='my-sg', SecurityGroupIds=['sg-xxx'])

# Subnet Group
resp = client.create_cache_subnet_group(
    CacheSubnetGroupName='my-sg', CacheSubnetGroupDescription='Cache subnets',
    SubnetIds=['subnet-a', 'subnet-b'])

# Parameter Group
resp = client.create_cache_parameter_group(
    CacheParameterGroupName='my-params', CacheParameterGroupFamily='redis7',
    Description='Custom Redis params')
```

## Describe / Query

```python
# Single group
resp = client.describe_replication_groups(ReplicationGroupId='my-cluster')
g = resp['ReplicationGroups'][0]
print(g['Status'], g['PrimaryEndpoint']['Address'], g['ReaderEndpoint']['Address'])

# Single cluster with node info
resp = client.describe_cache_clusters(CacheClusterId='my-memcached', ShowCacheNodeInfo=True)
for n in resp['CacheClusters'][0]['CacheNodes']:
    print(n['CacheNodeId'], n['Endpoint']['Address'])

# Paginate all (1 example; same pattern for replication groups)
paginator = client.get_paginator('describe_cache_clusters')
for page in paginator.paginate():
    for c in page['CacheClusters']:
        print(c['CacheClusterId'], c['CacheClusterStatus'])
```

## Modify / Scale

```python
# Scale up node type
client.modify_replication_group(
    ReplicationGroupId='my-cluster', CacheNodeType='cache.r5.large', ApplyImmediately=True)

# Increase replicas
client.increase_replica_count(
    ReplicationGroupId='my-cluster', NewReplicaCount=4, ApplyImmediately=True)

# Decrease replicas (specific nodes to remove)
client.decrease_replica_count(
    ReplicationGroupId='my-cluster', NewReplicaCount=2,
    ReplicaIdsToRemove=['my-cluster-003'], ApplyImmediately=True)

# List allowed scale targets
resp = client.list_allowed_node_type_modifications(ReplicationGroupId='my-cluster')
for nt in resp['ScaleUpModifications']: print(nt['NodeType'])
```

## Snapshot / Restore

```python
# Create
resp = client.create_snapshot(SnapshotName='my-snap-202605', ReplicationGroupId='my-cluster')

# Describe
resp = client.describe_snapshots(SnapshotName='my-snap-202605')
print(resp['Snapshots'][0]['SnapshotStatus'])

# Delete
client.delete_snapshot(SnapshotName='my-snap-202605')

# Restore Redis RG from snapshot
client.create_replication_group(
    ReplicationGroupId='restored-redis', Description='Restored', Engine='redis',
    CacheNodeType='cache.m5.large', NumCacheClusters=3, SnapshotName='my-snap-202605',
    CacheSubnetGroupName='my-sg', SecurityGroupIds=['sg-xxx'])
```

## Delete (Safety Gate Required)

```python
# Replication Group
resp = client.delete_replication_group(
    ReplicationGroupId='my-cluster', FinalSnapshotIdentifier='final-snapshot-202605')
print(resp['ReplicationGroup']['Status'])

# Cache Cluster
resp = client.delete_cache_cluster(
    CacheClusterId='my-memcached', FinalSnapshotIdentifier='final-snapshot-202605')
print(resp['CacheCluster']['CacheClusterStatus'])

# Subnet Group (no clusters using it)
client.delete_cache_subnet_group(CacheSubnetGroupName='my-sg')
```

## Waiters (built-in)

```python
client.get_waiter('replication_group_available').wait(
    ReplicationGroupId='my-cluster', WaiterConfig={'Delay': 30, 'MaxAttempts': 40})
```

Other waiters: `cache_cluster_available`, `replication_group_deleted`, `snapshot_available`.
See [boto3 docs](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/elasticache.html) for full list.

