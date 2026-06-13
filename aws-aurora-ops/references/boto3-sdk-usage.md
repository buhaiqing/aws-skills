# boto3 SDK Usage — Aurora (RDS client)

Primary path is AWS CLI; use boto3 after 3 consecutive CLI failures. All functions call `handle_rds_error(e)` on `ClientError` (see Error Handling).

## Client Initialization

```python
import boto3
from botocore.exceptions import ClientError

rds = boto3.client('rds', region_name='{{env.AWS_DEFAULT_REGION}}')
```

## Error Handling (declare once)

```python
def handle_rds_error(e):
    code = e.response['Error']['Code']
    if code in ('Throttling', 'ThrottlingException'):
        raise  # caller retries with backoff
    if code.endswith('NotFound'):
        raise ValueError(f'Resource not found: {code}') from e
    raise
```

## Cluster Operations

```python
def create_db_cluster(cluster_id, engine, master_user, password_arn, subnet_group, sg_ids):
    try:
        return rds.create_db_cluster(
            DBClusterIdentifier=cluster_id,
            Engine=engine,
            MasterUsername=master_user,
            MasterUserPassword=password_arn,
            DBSubnetGroupName=subnet_group,
            VpcSecurityGroupIds=sg_ids,
            BackupRetentionPeriod=7,
            StorageEncrypted=True,
            DeletionProtection=True,
        )['DBCluster']
    except ClientError as e:
        handle_rds_error(e)

def describe_db_cluster(cluster_id):
    try:
        return rds.describe_db_clusters(DBClusterIdentifier=cluster_id)['DBClusters'][0]
    except ClientError as e:
        handle_rds_error(e)

def create_cluster_instance(instance_id, cluster_id, instance_class, engine, promotion_tier=2):
    try:
        return rds.create_db_instance(
            DBInstanceIdentifier=instance_id,
            DBClusterIdentifier=cluster_id,
            DBInstanceClass=instance_class,
            Engine=engine,
            PromotionTier=promotion_tier,
        )['DBInstance']
    except ClientError as e:
        handle_rds_error(e)

def failover_db_cluster(cluster_id, target_instance_id=None):
    params = {'DBClusterIdentifier': cluster_id}
    if target_instance_id:
        params['TargetDBInstanceIdentifier'] = target_instance_id
    try:
        return rds.failover_db_cluster(**params)['DBCluster']
    except ClientError as e:
        handle_rds_error(e)

def delete_db_cluster(cluster_id, final_snapshot_id=None, skip_final_snapshot=False):
    params = {
        'DBClusterIdentifier': cluster_id,
        'SkipFinalSnapshot': skip_final_snapshot,
    }
    if final_snapshot_id:
        params['FinalDBSnapshotIdentifier'] = final_snapshot_id
        params['SkipFinalSnapshot'] = False
    try:
        return rds.delete_db_cluster(**params)['DBCluster']
    except ClientError as e:
        handle_rds_error(e)
```

## Serverless v2

```python
def create_serverless_v2_instance(instance_id, cluster_id, engine, min_cap=0.5, max_cap=16):
    try:
        return rds.create_db_instance(
            DBInstanceIdentifier=instance_id,
            DBClusterIdentifier=cluster_id,
            DBInstanceClass='db.serverless',
            Engine=engine,
            ServerlessV2ScalingConfiguration={'MinCapacity': min_cap, 'MaxCapacity': max_cap},
        )['DBInstance']
    except ClientError as e:
        handle_rds_error(e)
```

## Cluster Snapshots

```python
def create_cluster_snapshot(cluster_id, snapshot_id):
    try:
        return rds.create_db_cluster_snapshot(
            DBClusterSnapshotIdentifier=snapshot_id,
            DBClusterIdentifier=cluster_id,
        )['DBClusterSnapshot']
    except ClientError as e:
        handle_rds_error(e)

def restore_cluster_from_snapshot(new_cluster_id, snapshot_id, engine):
    try:
        return rds.restore_db_cluster_from_snapshot(
            DBClusterIdentifier=new_cluster_id,
            SnapshotIdentifier=snapshot_id,
            Engine=engine,
        )['DBCluster']
    except ClientError as e:
        handle_rds_error(e)

def delete_cluster_snapshot(snapshot_id):
    try:
        return rds.delete_db_cluster_snapshot(DBClusterSnapshotIdentifier=snapshot_id)['DBClusterSnapshot']
    except ClientError as e:
        handle_rds_error(e)
```

## Global Database

```python
def create_global_cluster(global_id, engine):
    try:
        return rds.create_global_cluster(GlobalClusterIdentifier=global_id, Engine=engine)['GlobalCluster']
    except ClientError as e:
        handle_rds_error(e)

def remove_from_global_cluster(global_id, cluster_arn):
    try:
        return rds.remove_from_global_cluster(
            GlobalClusterIdentifier=global_id,
            DbClusterIdentifier=cluster_arn,
        )['DBCluster']
    except ClientError as e:
        handle_rds_error(e)
```

## Polling

```python
import time

def wait_cluster_available(cluster_id, max_wait=1800, interval=30):
    for _ in range(max_wait // interval):
        status = describe_db_cluster(cluster_id)['Status']
        if status == 'available':
            return True
        if status in ('failed', 'inaccessible-encryption-credentials'):
            return False
        time.sleep(interval)
    return False
```
