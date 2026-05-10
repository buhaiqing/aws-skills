# boto3 SDK Usage — ElastiCache

## Client Initialization

```python
import boto3

client = boto3.client('elasticache', region_name='us-east-1')
```

## Operation Patterns

### Create Redis Replication Group

```python
response = client.create_replication_group(
    ReplicationGroupId='my-redis-cluster',
    ReplicationGroupDescription='Production Redis cluster',
    Engine='redis',
    EngineVersion='7.0',
    CacheNodeType='cache.m5.large',
    NumCacheClusters=3,
    CacheSubnetGroupName='my-cache-subnet',
    SecurityGroupIds=['sg-aaa'],
    AutomaticFailoverEnabled=True,
    MultiAZEnabled=True,
    AtRestEncryptionEnabled=True,
    TransitEncryptionEnabled=True,
    AuthToken='my-auth-token',
    Tags=[
        {'Key': 'Environment', 'Value': 'production'}
    ]
)

group_arn = response['ReplicationGroup']['ARN']
status = response['ReplicationGroup']['Status']
print(f"Replication Group ARN: {group_arn}")
print(f"Status: {status}")
```

### Create Redis Cluster Mode Enabled (Sharding)

```python
response = client.create_replication_group(
    ReplicationGroupId='my-redis-sharded',
    ReplicationGroupDescription='Redis Cluster mode enabled',
    Engine='redis',
    CacheNodeType='cache.r5.large',
    ReplicasPerNodeGroup=2,
    NumNodeGroups=3,
    CacheSubnetGroupName='my-cache-subnet',
    SecurityGroupIds=['sg-aaa'],
    ClusterMode='enabled'
)
```

### Create Memcached Cluster

```python
response = client.create_cache_cluster(
    CacheClusterId='my-memcached',
    Engine='memcached',
    EngineVersion='1.6.22',
    CacheNodeType='cache.m5.large',
    NumCacheNodes=3,
    CacheSubnetGroupName='my-cache-subnet',
    SecurityGroupIds=['sg-aaa'],
    AZMode='cross-az',
    Tags=[
        {'Key': 'Environment', 'Value': 'production'}
    ]
)

cluster_arn = response['CacheCluster']['ARN']
print(f"Cache Cluster ARN: {cluster_arn}")
```

### Create Single Redis Node

```python
response = client.create_cache_cluster(
    CacheClusterId='my-redis-single',
    Engine='redis',
    EngineVersion='7.0',
    CacheNodeType='cache.t3.medium',
    CacheSubnetGroupName='my-cache-subnet',
    SecurityGroupIds=['sg-aaa']
)
```

### Create Cache Subnet Group

```python
response = client.create_cache_subnet_group(
    CacheSubnetGroupName='my-cache-subnet',
    CacheSubnetGroupDescription='ElastiCache subnet group',
    SubnetIds=['subnet-aaa', 'subnet-bbb', 'subnet-ccc']
)

subnet_group_arn = response['CacheSubnetGroup']['ARN']
print(f"Subnet Group ARN: {subnet_group_arn}")
```

### Describe Replication Groups

```python
response = client.describe_replication_groups(
    ReplicationGroupId='my-redis-cluster'
)

group = response['ReplicationGroups'][0]
print(f"ID: {group['ReplicationGroupId']}")
print(f"Status: {group['Status']}")
print(f"Primary Endpoint: {group['PrimaryEndpoint']['Address']}")
print(f"Reader Endpoint: {group['ReaderEndpoint']['Address']}")
print(f"Member Clusters: {group['MemberClusters']}")

# Pagination
paginator = client.get_paginator('describe_replication_groups')
for page in paginator.paginate():
    for group in page['ReplicationGroups']:
        print(group['ReplicationGroupId'])
```

### Describe Cache Clusters

```python
response = client.describe_cache_clusters(
    CacheClusterId='my-memcached',
    ShowCacheNodeInfo=True
)

cluster = response['CacheClusters'][0]
print(f"ID: {cluster['CacheClusterId']}")
print(f"Status: {cluster['CacheClusterStatus']}")
print(f"Engine: {cluster['Engine']}")

# Get endpoints
for node in cluster['CacheNodes']:
    print(f"Node {node['CacheNodeId']}: {node['Endpoint']['Address']}:{node['Endpoint']['Port']}")
```

### List All Cache Clusters

```python
response = client.describe_cache_clusters()

for cluster in response['CacheClusters']:
    print(f"{cluster['CacheClusterId']}: {cluster['CacheClusterStatus']}")

# Pagination
paginator = client.get_paginator('describe_cache_clusters')
for page in paginator.paginate():
    for cluster in page['CacheClusters']:
        print(cluster['CacheClusterId'])
```

### Add Read Replica (Increase Replica Count)

```python
response = client.increase_replica_count(
    ReplicationGroupId='my-redis-cluster',
    NewReplicaCount=4,
    ApplyImmediately=True
)

print(f"New replica count: {response['ReplicationGroup']['NumCacheClusters']}")
```

### Remove Read Replica

```python
response = client.decrease_replica_count(
    ReplicationGroupId='my-redis-cluster',
    NewReplicaCount=2,
    ReplicaIdsToRemove=['my-redis-cluster-003'],
    ApplyImmediately=True
)
```

### Modify Replication Group (Scale Up)

```python
response = client.modify_replication_group(
    ReplicationGroupId='my-redis-cluster',
    CacheNodeType='cache.r5.large',
    ApplyImmediately=True
)
```

### Modify Replication Group Settings

```python
response = client.modify_replication_group(
    ReplicationGroupId='my-redis-cluster',
    AutomaticFailoverEnabled=True,
    TransitEncryptionEnabled=True,
    AuthToken='new-auth-token',
    ApplyImmediately=True
)
```

### Create Parameter Group

```python
response = client.create_cache_parameter_group(
    CacheParameterGroupName='my-redis-params',
    CacheParameterGroupFamily='redis7',
    Description='Custom Redis parameters'
)

print(f"Parameter Group ARN: {response['CacheParameterGroup']['ARN']}")
```

### Modify Parameter Group Parameters

```python
response = client.modify_cache_parameter_group(
    CacheParameterGroupName='my-redis-params',
    ParameterNameValues=[
        {'ParameterName': 'maxmemory-policy', 'ParameterValue': 'allkeys-lru'},
        {'ParameterName': 'timeout', 'ParameterValue': '300'}
    ]
)
```

### Describe Parameter Group

```python
response = client.describe_cache_parameters(
    CacheParameterGroupName='my-redis-params'
)

for param in response['Parameters']:
    if param['Source'] == 'user':  # User-modified parameters
        print(f"{param['ParameterName']}: {param['ParameterValue']}")
```

### Create Snapshot

```bash
response = client.create_snapshot(
    SnapshotName='my-snapshot-20260510',
    ReplicationGroupId='my-redis-cluster'
)

# Or for cache cluster
response = client.create_snapshot(
    SnapshotName='my-snapshot-20260510',
    CacheClusterId='my-redis-single'
)

snapshot_arn = response['Snapshot']['ARN']
print(f"Snapshot ARN: {snapshot_arn}")
```

### Describe Snapshots

```python
response = client.describe_snapshots(
    SnapshotName='my-snapshot-20260510'
)

snapshot = response['Snapshots'][0]
print(f"Name: {snapshot['SnapshotName']}")
print(f"Status: {snapshot['SnapshotStatus']}")
print(f"Source: {snapshot['SnapshotSource']}")

# List all snapshots
paginator = client.get_paginator('describe_snapshots')
for page in paginator.paginate():
    for snapshot in page['Snapshots']:
        print(snapshot['SnapshotName'])
```

### Restore from Snapshot (Redis)

```python
response = client.create_replication_group(
    ReplicationGroupId='restored-redis',
    ReplicationGroupDescription='Restored from snapshot',
    Engine='redis',
    CacheNodeType='cache.m5.large',
    NumCacheClusters=3,
    SnapshotName='my-snapshot-20260510',
    CacheSubnetGroupName='my-cache-subnet',
    SecurityGroupIds=['sg-aaa']
)
```

### Restore from Snapshot (Memcached)

```python
response = client.create_cache_cluster(
    CacheClusterId='restored-memcached',
    Engine='memcached',
    CacheNodeType='cache.m5.large',
    NumCacheNodes=3,
    SnapshotName='my-snapshot-20260510',
    CacheSubnetGroupName='my-cache-subnet',
    SecurityGroupIds=['sg-aaa']
)
```

### Delete Snapshot

```python
response = client.delete_snapshot(
    SnapshotName='my-snapshot-20260510'
)

print(f"Status: {response['Snapshot']['SnapshotStatus']}")
```

### Delete Cache Cluster (Safety Gate Required)

```python
# Safety Gate: Confirm with user before deletion
response = client.delete_cache_cluster(
    CacheClusterId='my-memcached',
    FinalSnapshotIdentifier='final-snapshot-20260510'
)

print(f"Status: {response['CacheCluster']['CacheClusterStatus']}")
```

### Delete Replication Group (Safety Gate Required)

```python
# Safety Gate: Confirm with user before deletion
response = client.delete_replication_group(
    ReplicationGroupId='my-redis-cluster',
    FinalSnapshotIdentifier='final-snapshot-20260510'
)

print(f"Status: {response['ReplicationGroup']['Status']}")
```

### Delete Subnet Group

```python
response = client.delete_cache_subnet_group(
    CacheSubnetGroupName='my-cache-subnet'
)
```

### List Allowed Node Type Modifications

```python
response = client.list_allowed_node_type_modifications(
    ReplicationGroupId='my-redis-cluster'
)

for mod in response['ScaleUpModifications']:
    print(f"Can scale up to: {mod['NodeType']}")

for mod in response['ScaleDownModifications']:
    print(f"Can scale down to: {mod['NodeType']}")
```

## Error Handling

```python
from botocore.exceptions import ClientError

try:
    response = client.create_replication_group(
        ReplicationGroupId='my-redis',
        Engine='redis',
        CacheNodeType='cache.m5.large',
        NumCacheClusters=3
    )
except ClientError as e:
    code = e.response['Error']['Code']
    
    if code == 'ReplicationGroupAlreadyExists':
        print("Replication group ID already exists")
    elif code == 'CacheSubnetGroupNotFoundFault':
        print("Subnet group not found")
    elif code == 'InvalidParameterValue':
        print("Invalid parameter value")
    elif code == 'InsufficientCacheClusterCapacity':
        print("Not enough capacity for node type")
    elif code == 'ThrottlingException':
        # Retry with backoff
        pass
    else:
        raise
```

## Common Error Codes

| Error Code | HTTP | Action |
|------------|------|--------|
| ReplicationGroupAlreadyExists | 400 | HALT; use different ID |
| CacheClusterAlreadyExists | 400 | HALT; use different ID |
| CacheSubnetGroupNotFoundFault | 404 | HALT; create subnet group first |
| InvalidParameterValue | 400 | Fix parameter; retry once |
| InvalidParameterCombination | 400 | Fix config; retry once |
| InsufficientCacheClusterCapacity | 400 | HALT; different node type |
| CacheClusterNotFound | 404 | HALT; verify cluster ID |
| ReplicationGroupNotFound | 404 | HALT; verify group ID |
| InvalidCacheClusterState | 400 | HALT; wait for available status |
| ThrottlingException | 429 | Backoff; retry 3x |
| ServiceUnavailable | 500 | Retry 3x; HALT if persists |

## Waiters

ElastiCache provides built-in waiters:

```python
# Wait for cache cluster available
waiter = client.get_waiter('cache_cluster_available')
waiter.wait(
    CacheClusterId='my-memcached',
    WaiterConfig={
        'Delay': 15,
        'MaxAttempts': 60
    }
)

# Wait for cache cluster deleted
waiter = client.get_waiter('cache_cluster_deleted')
waiter.wait(CacheClusterId='my-memcached')

# Wait for replication group available
waiter = client.get_waiter('replication_group_available')
waiter.wait(
    ReplicationGroupId='my-redis-cluster',
    WaiterConfig={
        'Delay': 30,
        'MaxAttempts': 40
    }
)

# Wait for replication group deleted
waiter = client.get_waiter('replication_group_deleted')
waiter.wait(ReplicationGroupId='my-redis-cluster')

# Wait for snapshot available
waiter = client.get_waiter('snapshot_available')
waiter.wait(
    SnapshotName='my-snapshot',
    WaiterConfig={
        'Delay': 10,
        'MaxAttempts': 60
    }
)
```

## Custom Polling

```python
import time

def wait_for_replication_group_available(client, group_id, max_wait=900):
    """Wait for replication group to become available."""
    
    for i in range(max_wait // 30):
        response = client.describe_replication_groups(
            ReplicationGroupId=group_id
        )
        status = response['ReplicationGroups'][0]['Status']
        
        if status == 'available':
            print(f"Replication group {group_id} is available")
            return True
        elif status in ['deleted', 'create-failed']:
            raise Exception(f"Replication group failed: {status}")
        
        print(f"Status: {status}, waiting...")
        time.sleep(30)
    
    raise TimeoutError(f"Not available after {max_wait}s")

def wait_for_cache_cluster_available(client, cluster_id, max_wait=600):
    """Wait for cache cluster to become available."""
    
    for i in range(max_wait // 15):
        response = client.describe_cache_clusters(
            CacheClusterId=cluster_id
        )
        status = response['CacheClusters'][0]['CacheClusterStatus']
        
        if status == 'available':
            return True
        elif status in ['deleted', 'restore-failed']:
            raise Exception(f"Cluster failed: {status}")
        
        time.sleep(15)
    
    raise TimeoutError(f"Not available after {max_wait}s")
```

## Pagination Pattern

```python
paginator = client.get_paginator('describe_cache_clusters')
for page in paginator.paginate():
    for cluster in page['CacheClusters']:
        print(cluster['CacheClusterId'])

paginator = client.get_paginator('describe_replication_groups')
for page in paginator.paginate():
    for group in page['ReplicationGroups']:
        print(group['ReplicationGroupId'])
```

## Retry Strategy

```python
from botocore.config import Config

config = Config(retries={'max_attempts': 3, 'mode': 'standard'})
client = boto3.client('elasticache', region_name='us-east-1', config=config)
```