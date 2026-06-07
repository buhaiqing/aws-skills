# boto3 SDK Usage - RDS

Python boto3 patterns for RDS operations. All functions use `handle_rds_error(e)` for error handling (see Error Handling section).

## Client Initialization
```python
import boto3
from botocore.exceptions import ClientError
rds = boto3.client('rds', region_name='{{env.AWS_DEFAULT_REGION}}')
```

## DB Instance Operations

### Create DB Instance
```python
def create_db_instance(identifier, instance_class, engine, engine_version, master_username,
                       master_password, allocated_storage, security_group_ids,
                       subnet_group_name=None, multi_az=False, storage_encrypted=True):
    params = {
        'DBInstanceIdentifier': identifier, 'DBInstanceClass': instance_class,
        'Engine': engine, 'EngineVersion': engine_version, 'MasterUsername': master_username,
        'MasterUserPassword': master_password, 'AllocatedStorage': allocated_storage,
        'VpcSecurityGroupIds': security_group_ids, 'StorageType': 'gp3',
        'StorageEncrypted': storage_encrypted, 'DeletionProtection': True,
        'EnablePerformanceInsights': True, 'BackupRetentionPeriod': 7,
    }
    if subnet_group_name: params['DBSubnetGroupName'] = subnet_group_name
    if multi_az: params['MultiAZ'] = True
    try: return rds.create_db_instance(**params)['DBInstance']
    except ClientError as e: handle_rds_error(e)
```

### Describe & Read
```python
def describe_db_instance(identifier):
    try: return rds.describe_db_instances(DBInstanceIdentifier=identifier)['DBInstances'][0]
    except ClientError as e: handle_rds_error(e)

def get_db_instance_status(identifier): return describe_db_instance(identifier)['DBInstanceStatus']

def get_db_endpoint(identifier):
    inst = describe_db_instance(identifier)
    ep = inst.get('Endpoint')
    return (ep['Address'], ep['Port']) if ep else (None, None)
```

### Modify DB Instance
```python
def modify_db_instance(identifier, new_instance_class=None, new_allocated_storage=None, apply_immediately=False):
    params = {'DBInstanceIdentifier': identifier, 'ApplyImmediately': apply_immediately}
    if new_instance_class: params['DBInstanceClass'] = new_instance_class
    if new_allocated_storage: params['AllocatedStorage'] = new_allocated_storage
    try: return rds.modify_db_instance(**params)['DBInstance']
    except ClientError as e: handle_rds_error(e)
```

### Delete DB Instance
```python
def delete_db_instance(identifier, final_snapshot_identifier=None, skip_final_snapshot=False):
    params = {'DBInstanceIdentifier': identifier, 'SkipFinalSnapshot': skip_final_snapshot}
    if final_snapshot_identifier:
        params['FinalDBSnapshotIdentifier'] = final_snapshot_identifier
        params['SkipFinalSnapshot'] = False
    try: return rds.delete_db_instance(**params)['DBInstance']
    except ClientError as e: handle_rds_error(e)
```

## Snapshot Operations
```python
def create_snapshot(instance_id, snapshot_id):
    try: return rds.create_db_snapshot(DBSnapshotIdentifier=snapshot_id, DBInstanceIdentifier=instance_id)['DBSnapshot']
    except ClientError as e: handle_rds_error(e)

def describe_snapshot(snapshot_id):
    try: return rds.describe_db_snapshots(DBSnapshotIdentifier=snapshot_id)['DBSnapshots'][0]
    except ClientError as e: handle_rds_error(e)

def list_instance_snapshots(instance_id):
    try: return rds.describe_db_snapshots(DBInstanceIdentifier=instance_id)['DBSnapshots']
    except ClientError as e: handle_rds_error(e)

def restore_from_snapshot(snapshot_id, new_instance_id, instance_class=None):
    params = {'DBInstanceIdentifier': new_instance_id, 'DBSnapshotIdentifier': snapshot_id}
    if instance_class: params['DBInstanceClass'] = instance_class
    try: return rds.restore_db_instance_from_db_snapshot(**params)['DBInstance']
    except ClientError as e: handle_rds_error(e)

def delete_snapshot(snapshot_id):
    try: return rds.delete_db_snapshot(DBSnapshotIdentifier=snapshot_id)['DBSnapshot']
    except ClientError as e: handle_rds_error(e)
```

## Read Replica Operations
```python
def create_read_replica(source_id, replica_id, replica_class=None):
    params = {'DBInstanceIdentifier': replica_id, 'SourceDBInstanceIdentifier': source_id}
    if replica_class: params['DBInstanceClass'] = replica_class
    try: return rds.create_db_instance_read_replica(**params)['DBInstance']
    except ClientError as e: handle_rds_error(e)

def promote_read_replica(replica_id):
    try: return rds.promote_read_replica(DBInstanceIdentifier=replica_id)['DBInstance']
    except ClientError as e: handle_rds_error(e)
```

## Parameter Group Operations
```python
def create_parameter_group(group_name, group_family, description):
    try: return rds.create_db_parameter_group(DBParameterGroupName=group_name,
            DBParameterGroupFamily=group_family, Description=description)['DBParameterGroup']
    except ClientError as e: handle_rds_error(e)

def modify_parameter_group(group_name, parameters):
    try: return rds.modify_db_parameter_group(DBParameterGroupName=group_name, Parameters=parameters)
    except ClientError as e: handle_rds_error(e)
# parameters = [{'ParameterName': 'max_connections', 'ParameterValue': '500', 'ApplyMethod': 'immediate'}]

def delete_parameter_group(group_name):
    try: return rds.delete_db_parameter_group(DBParameterGroupName=group_name)
    except ClientError as e: handle_rds_error(e)
```

## Waiters
```python
def wait_for_instance_available(identifier, timeout=1800):
    waiter = rds.get_waiter('db_instance_available')
    try:
        waiter.wait(DBInstanceIdentifier=identifier, WaiterConfig={'Delay': 30, 'MaxAttempts': timeout // 30})
        return True
    except Exception: return False

def wait_for_instance_deleted(identifier, timeout=900):
    waiter = rds.get_waiter('db_instance_deleted')
    try:
        waiter.wait(DBInstanceIdentifier=identifier, WaiterConfig={'Delay': 30, 'MaxAttempts': timeout // 30})
        return True
    except Exception: return False
```

## Error Handling
```python
def handle_rds_error(error):
    code = error.response['Error']['Code']
    msg = error.response['Error']['Message']
    recovery_map = {
        'DBInstanceAlreadyExists': 'HALT - Instance exists',
        'InvalidDBInstanceState': 'HALT - Wrong state',
        'DBParameterGroupNotFound': 'FIX - Create first',
        'DBSnapshotAlreadyExists': 'FIX - Different name',
        'StorageTypeNotSupported': 'RETRY - Use gp2/gp3',
        'InsufficientStorageCapacity': 'HALT - Reduce size/change region',
        'QuotaExceeded': 'HALT - Request quota increase',
    }
    recovery = recovery_map.get(code, 'HALT - Check AWS docs.')
    raise Exception(f"RDS Error [{code}]: {msg}\nRecovery: {recovery}")
```

## Performance Insights (Slow Query Analysis)

```python
import boto3
from datetime import datetime, timedelta

rds = boto3.client('rds')
pi = boto3.client('pi')
logs = boto3.client('logs')

def get_dbi_resource_id(identifier):
    """Get the DbiResourceId needed for PI API calls"""
    resp = rds.describe_db_instances(DBInstanceIdentifier=identifier)
    return resp['DBInstances'][0]['DbiResourceId']

def enable_performance_insights(identifier, retention=7):
    rds.modify_db_instance(
        DBInstanceIdentifier=identifier,
        EnablePerformanceInsights=True,
        PerformanceInsightsRetentionPeriod=retention,
        ApplyImmediately=True
    )

def enable_slow_query_log(identifier, engine='mysql'):
    log_type = 'slowquery' if engine.startswith('mysql') or engine.startswith('aurora-mysql') else 'postgresql'
    rds.modify_db_instance(
        DBInstanceIdentifier=identifier,
        CloudwatchLogsExportConfiguration={
            'EnableLogTypes': [log_type]
        },
        ApplyImmediately=True
    )

def get_top_sql_by_load(dbi_resource_id, hours=1, limit=10, region='us-east-1'):
    end = datetime.utcnow()
    start = end - timedelta(hours=hours)
    return pi.get_resource_metrics(
        ServiceType='RDS',
        Identifier=dbi_resource_id,
        StartTime=int(start.timestamp()),
        EndTime=int(end.timestamp()),
        PeriodInSeconds=60,
        MetricQueries=[{
            'Metric': 'db.sproc_execution_time',
            'GroupBy': {'Group': 'db.sql_tokenized', 'Limit': limit}
        }],
        PeriodAligned=True
    )

def get_wait_event_breakdown(dbi_resource_id, hours=1, limit=10, region='us-east-1'):
    end = datetime.utcnow()
    start = end - timedelta(hours=hours)
    return pi.get_resource_metrics(
        ServiceType='RDS',
        Identifier=dbi_resource_id,
        StartTime=int(start.timestamp()),
        EndTime=int(end.timestamp()),
        PeriodInSeconds=60,
        MetricQueries=[{
            'Metric': 'db.sproc_execution_time',
            'GroupBy': {'Group': 'db.wait_event', 'Limit': limit}
        }]
    )

def get_slow_query_logs_cw(identifier, hours=1, engine='mysql', region='us-east-1'):
    log_type = 'slowquery' if engine.startswith('mysql') or engine.startswith('aurora-mysql') else 'postgresql'
    log_group = f"/aws/rds/instance/{identifier}/{log_type}"
    end = datetime.utcnow()
    start = end - timedelta(hours=hours)

    query_string = ('fields @timestamp, @message | filter @message like /(?i)(Query_time|# User@Host)/ '
        '| parse @message /Query_time: (?<query_time>\\S+).*Lock_time: (?<lock_time>\\S+).*'
        'Rows_sent: (?<rows_sent>\\d+).*Rows_examined: (?<rows_examined>\\d+)/ '
        '| sort query_time desc | limit 50')

    response = logs.start_query(
        logGroupNames=[log_group],
        startTime=int(start.timestamp()),
        endTime=int(end.timestamp()),
        queryString=query_string,
        limit=50
    )
    query_id = response['queryId']

    import time
    for _ in range(10):
        result = logs.get_query_results(queryId=query_id)
        if result['status'] == 'Complete':
            return result['results']
        time.sleep(2)
    return None

def get_pi_dimension_breakdown(dbi_resource_id, metric='db.sproc_execution_time',
                                group='db.user', limit=10):
    """Get metric breakdown by dimension (user, host, database, etc.)"""
    end = datetime.utcnow()
    start = end - timedelta(hours=1)
    return pi.get_resource_metrics(
        ServiceType='RDS',
        Identifier=dbi_resource_id,
        StartTime=int(start.timestamp()),
        EndTime=int(end.timestamp()),
        PeriodInSeconds=60,
        MetricQueries=[{
            'Metric': metric,
            'GroupBy': {'Group': group, 'Limit': limit}
        }]
    )
```

## Engine Version Discovery
```python
def get_available_engine_versions(engine):
    try:
        versions = [v['EngineVersion'] for v in rds.describe_db_engine_versions(Engine=engine)['DBEngineVersions']]
        return sorted(versions, reverse=True)
    except ClientError as e: handle_rds_error(e)

def get_parameter_group_family(engine, version):
    try:
        return rds.describe_db_engine_versions(Engine=engine, EngineVersion=version)['DBEngineVersions'][0]['DBParameterGroupFamily']
    except ClientError as e: handle_rds_error(e)
```