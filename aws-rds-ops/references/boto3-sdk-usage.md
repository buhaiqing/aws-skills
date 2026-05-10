# boto3 SDK Usage - RDS

Python boto3 patterns for RDS operations.

## Client Initialization

```python
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

# Standard client
rds = boto3.client('rds', region_name='{{env.AWS_DEFAULT_REGION}}')

# With retry configuration
config = Config(
    retries={
        'max_attempts': 5,
        'mode': 'exponential'
    }
)
rds = boto3.client('rds', region_name='{{env.AWS_DEFAULT_REGION}}', config=config)
```

## DB Instance Operations

### Create DB Instance
```python
def create_db_instance(
    identifier: str,
    instance_class: str,
    engine: str,
    engine_version: str,
    master_username: str,
    master_password: str,
    allocated_storage: int,
    security_group_ids: list,
    subnet_group_name: str = None,
    multi_az: bool = False,
    storage_encrypted: bool = True
):
    """
    Create a new RDS DB instance.
    
    Args:
        identifier: DB instance identifier (unique)
        instance_class: DB instance class (e.g., db.t3.micro)
        engine: Database engine (mysql, postgres, aurora-mysql)
        engine_version: Engine version string
        master_username: Admin username
        master_password: Admin password
        allocated_storage: Storage in GB (min 20 for MySQL)
        security_group_ids: List of VPC security group IDs
        subnet_group_name: DB subnet group name
        multi_az: Enable Multi-AZ deployment
        storage_encrypted: Enable storage encryption
    
    Returns:
        dict: DB instance details
    """
    try:
        params = {
            'DBInstanceIdentifier': identifier,
            'DBInstanceClass': instance_class,
            'Engine': engine,
            'EngineVersion': engine_version,
            'MasterUsername': master_username,
            'MasterUserPassword': master_password,
            'AllocatedStorage': allocated_storage,
            'VpcSecurityGroupIds': security_group_ids,
            'StorageType': 'gp3',
            'StorageEncrypted': storage_encrypted,
            'DeletionProtection': True,
            'EnablePerformanceInsights': True,
            'BackupRetentionPeriod': 7,
        }
        
        if subnet_group_name:
            params['DBSubnetGroupName'] = subnet_group_name
        
        if multi_az:
            params['MultiAZ'] = True
        
        response = rds.create_db_instance(**params)
        return response['DBInstance']
    
    except ClientError as e:
        handle_rds_error(e)
```

### Describe DB Instance
```python
def describe_db_instance(identifier: str) -> dict:
    """
    Get details of a DB instance.
    
    Args:
        identifier: DB instance identifier
    
    Returns:
        dict: DB instance details including status and endpoint
    """
    try:
        response = rds.describe_db_instances(
            DBInstanceIdentifier=identifier
        )
        return response['DBInstances'][0]
    except ClientError as e:
        handle_rds_error(e)

def get_db_instance_status(identifier: str) -> str:
    """Get current status of DB instance."""
    instance = describe_db_instance(identifier)
    return instance['DBInstanceStatus']

def get_db_endpoint(identifier: str) -> tuple:
    """
    Get connection endpoint.
    
    Returns:
        tuple: (host, port) or (None, None) if not available
    """
    instance = describe_db_instance(identifier)
    endpoint = instance.get('Endpoint')
    if endpoint:
        return (endpoint['Address'], endpoint['Port'])
    return (None, None)
```

### Modify DB Instance
```python
def modify_db_instance(
    identifier: str,
    new_instance_class: str = None,
    new_allocated_storage: int = None,
    apply_immediately: bool = False
):
    """
    Modify DB instance configuration.
    
    Args:
        identifier: DB instance identifier
        new_instance_class: New instance class for scaling
        new_allocated_storage: New storage size in GB
        apply_immediately: Apply changes immediately
    
    Returns:
        dict: Modified DB instance details
    """
    try:
        params = {
            'DBInstanceIdentifier': identifier,
            'ApplyImmediately': apply_immediately
        }
        
        if new_instance_class:
            params['DBInstanceClass'] = new_instance_class
        
        if new_allocated_storage:
            params['AllocatedStorage'] = new_allocated_storage
        
        response = rds.modify_db_instance(**params)
        return response['DBInstance']
    
    except ClientError as e:
        handle_rds_error(e)
```

### Delete DB Instance
```python
def delete_db_instance(
    identifier: str,
    final_snapshot_identifier: str = None,
    skip_final_snapshot: bool = False
):
    """
    Delete a DB instance.
    
    SAFETY: Always create final snapshot unless explicitly skipped.
    
    Args:
        identifier: DB instance identifier
        final_snapshot_identifier: Name for final snapshot
        skip_final_snapshot: Skip final snapshot (data loss)
    
    Returns:
        dict: Deletion response
    """
    try:
        params = {
            'DBInstanceIdentifier': identifier,
            'SkipFinalSnapshot': skip_final_snapshot
        }
        
        if final_snapshot_identifier:
            params['FinalDBSnapshotIdentifier'] = final_snapshot_identifier
            params['SkipFinalSnapshot'] = False
        
        response = rds.delete_db_instance(**params)
        return response['DBInstance']
    
    except ClientError as e:
        handle_rds_error(e)
```

## Snapshot Operations

### Create Snapshot
```python
def create_snapshot(instance_identifier: str, snapshot_identifier: str) -> dict:
    """
    Create manual snapshot of DB instance.
    
    Args:
        instance_identifier: Source DB instance identifier
        snapshot_identifier: Unique snapshot identifier
    
    Returns:
        dict: Snapshot details
    """
    try:
        response = rds.create_db_snapshot(
            DBSnapshotIdentifier=snapshot_identifier,
            DBInstanceIdentifier=instance_identifier
        )
        return response['DBSnapshot']
    except ClientError as e:
        handle_rds_error(e)
```

### Describe Snapshots
```python
def describe_snapshot(snapshot_identifier: str) -> dict:
    """Get details of a specific snapshot."""
    try:
        response = rds.describe_db_snapshots(
            DBSnapshotIdentifier=snapshot_identifier
        )
        return response['DBSnapshots'][0]
    except ClientError as e:
        handle_rds_error(e)

def list_instance_snapshots(instance_identifier: str) -> list:
    """List all snapshots for a DB instance."""
    try:
        response = rds.describe_db_snapshots(
            DBInstanceIdentifier=instance_identifier
        )
        return response['DBSnapshots']
    except ClientError as e:
        handle_rds_error(e)
```

### Restore from Snapshot
```python
def restore_from_snapshot(
    snapshot_identifier: str,
    new_instance_identifier: str,
    instance_class: str = None
) -> dict:
    """
    Restore DB instance from snapshot.
    
    Args:
        snapshot_identifier: Source snapshot identifier
        new_instance_identifier: New DB instance identifier
        instance_class: Optional different instance class
    
    Returns:
        dict: Restored DB instance details
    """
    try:
        params = {
            'DBInstanceIdentifier': new_instance_identifier,
            'DBSnapshotIdentifier': snapshot_identifier
        }
        
        if instance_class:
            params['DBInstanceClass'] = instance_class
        
        response = rds.restore_db_instance_from_db_snapshot(**params)
        return response['DBInstance']
    except ClientError as e:
        handle_rds_error(e)
```

### Delete Snapshot
```python
def delete_snapshot(snapshot_identifier: str) -> dict:
    """
    Delete a DB snapshot.
    
    SAFETY: Human confirmation required before deletion.
    
    Args:
        snapshot_identifier: Snapshot to delete
    
    Returns:
        dict: Deletion response
    """
    try:
        response = rds.delete_db_snapshot(
            DBSnapshotIdentifier=snapshot_identifier
        )
        return response['DBSnapshot']
    except ClientError as e:
        handle_rds_error(e)
```

## Read Replica Operations

### Create Read Replica
```python
def create_read_replica(
    source_identifier: str,
    replica_identifier: str,
    replica_class: str = None
) -> dict:
    """
    Create read replica from source DB instance.
    
    Args:
        source_identifier: Source DB instance identifier
        replica_identifier: Replica DB instance identifier
        replica_class: Optional different instance class
    
    Returns:
        dict: Replica DB instance details
    """
    try:
        params = {
            'DBInstanceIdentifier': replica_identifier,
            'SourceDBInstanceIdentifier': source_identifier
        }
        
        if replica_class:
            params['DBInstanceClass'] = replica_class
        
        response = rds.create_db_instance_read_replica(**params)
        return response['DBInstance']
    except ClientError as e:
        handle_rds_error(e)
```

### Promote Read Replica
```python
def promote_read_replica(replica_identifier: str) -> dict:
    """
    Promote read replica to standalone DB instance.
    
    Args:
        replica_identifier: Replica DB instance identifier
    
    Returns:
        dict: Promoted DB instance details
    """
    try:
        response = rds.promote_read_replica(
            DBInstanceIdentifier=replica_identifier
        )
        return response['DBInstance']
    except ClientError as e:
        handle_rds_error(e)
```

## Parameter Group Operations

### Create Parameter Group
```python
def create_parameter_group(
    group_name: str,
    group_family: str,
    description: str
) -> dict:
    """
    Create custom DB parameter group.
    
    Args:
        group_name: Parameter group name
        group_family: Engine family (mysql8.0, postgres15)
        description: Group description
    
    Returns:
        dict: Parameter group details
    """
    try:
        response = rds.create_db_parameter_group(
            DBParameterGroupName=group_name,
            DBParameterGroupFamily=group_family,
            Description=description
        )
        return response['DBParameterGroup']
    except ClientError as e:
        handle_rds_error(e)
```

### Modify Parameter Group
```python
def modify_parameter_group(
    group_name: str,
    parameters: list
) -> dict:
    """
    Modify parameters in a parameter group.
    
    Args:
        group_name: Parameter group name
        parameters: List of parameter dicts with Name, Value, ApplyMethod
    
    Returns:
        dict: Modification result
    
    Example parameters:
        [
            {'ParameterName': 'max_connections', 'ParameterValue': '500', 'ApplyMethod': 'immediate'},
            {'ParameterName': 'innodb_buffer_pool_size', 'ParameterValue': '{size}', 'ApplyMethod': 'pending-reboot'}
        ]
    """
    try:
        response = rds.modify_db_parameter_group(
            DBParameterGroupName=group_name,
            Parameters=parameters
        )
        return response
    except ClientError as e:
        handle_rds_error(e)
```

### Delete Parameter Group
```python
def delete_parameter_group(group_name: str) -> dict:
    """
    Delete parameter group.
    
    PRECONDITION: No DB instances using this group.
    
    Args:
        group_name: Parameter group name
    
    Returns:
        dict: Deletion response
    """
    try:
        response = rds.delete_db_parameter_group(
            DBParameterGroupName=group_name
        )
        return response
    except ClientError as e:
        handle_rds_error(e)
```

## Waiters

### Wait for DB Instance Available
```python
def wait_for_instance_available(identifier: str, timeout: int = 1800):
    """
    Wait for DB instance to become available.
    
    Args:
        identifier: DB instance identifier
        timeout: Maximum wait time in seconds (default 30 min)
    
    Returns:
        bool: True if available, False if timeout
    """
    waiter = rds.get_waiter('db_instance_available')
    try:
        waiter.wait(
            DBInstanceIdentifier=identifier,
            WaiterConfig={
                'Delay': 30,  # Check every 30 seconds
                'MaxAttempts': timeout // 30
            }
        )
        return True
    except Exception:
        return False
```

### Wait for DB Instance Deleted
```python
def wait_for_instance_deleted(identifier: str, timeout: int = 900):
    """
    Wait for DB instance to be deleted.
    
    Args:
        identifier: DB instance identifier
        timeout: Maximum wait time in seconds (default 15 min)
    
    Returns:
        bool: True if deleted, False if timeout
    """
    waiter = rds.get_waiter('db_instance_deleted')
    try:
        waiter.wait(
            DBInstanceIdentifier=identifier,
            WaiterConfig={
                'Delay': 30,
                'MaxAttempts': timeout // 30
            }
        )
        return True
    except Exception:
        return False
```

## Error Handling

```python
def handle_rds_error(error: ClientError):
    """
    Handle RDS errors with recovery guidance.
    
    Args:
        error: ClientError from boto3
    
    Raises:
        Exception with recovery guidance
    """
    error_code = error.response['Error']['Code']
    error_message = error.response['Error']['Message']
    
    recovery_map = {
        'DBInstanceAlreadyExists': 'HALT - Instance exists. Use describe to get details.',
        'InvalidDBInstanceState': 'HALT - Instance in wrong state. Check status.',
        'DBParameterGroupNotFound': 'FIX - Create parameter group first.',
        'DBSnapshotAlreadyExists': 'FIX - Use different snapshot name.',
        'StorageTypeNotSupported': 'RETRY - Use gp2 or gp3 instead.',
        'InsufficientStorageCapacity': 'HALT - Reduce storage size or use different region.',
        'InvalidVPCNetworkState': 'HALT - Fix subnet group or security groups.',
        'DBSecurityGroupNotFound': 'FIX - Create security group in EC2.',
        'AuthorizationNotFound': 'FIX - Add IAM permissions for RDS.',
        'QuotaExceeded': 'HALT - Request quota increase via AWS console.',
    }
    
    recovery = recovery_map.get(error_code, 'HALT - Check AWS documentation.')
    
    raise Exception(f"RDS Error [{error_code}]: {error_message}\nRecovery: {recovery}")
```

## Engine Version Discovery

```python
def get_available_engine_versions(engine: str) -> list:
    """
    Get available versions for a database engine.
    
    Args:
        engine: Database engine (mysql, postgres, aurora-mysql)
    
    Returns:
        list: Available engine versions
    """
    try:
        response = rds.describe_db_engine_versions(Engine=engine)
        versions = [v['EngineVersion'] for v in response['DBEngineVersions']]
        return sorted(versions, reverse=True)
    except ClientError as e:
        handle_rds_error(e)

def get_parameter_group_family(engine: str, version: str) -> str:
    """
    Get parameter group family for engine and version.
    
    Args:
        engine: Database engine
        version: Engine version
    
    Returns:
        str: Parameter group family name
    """
    try:
        response = rds.describe_db_engine_versions(
            Engine=engine,
            EngineVersion=version
        )
        return response['DBEngineVersions'][0]['DBParameterGroupFamily']
    except ClientError as e:
        handle_rds_error(e)
```

## Connection Testing (Optional)

```python
import socket

def test_db_connection(host: str, port: int, timeout: float = 5.0) -> bool:
    """
    Test TCP connection to database endpoint.
    
    Args:
        host: Database endpoint host
        port: Database port
        timeout: Connection timeout
    
    Returns:
        bool: True if reachable, False otherwise
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False
```

## Complete Create Flow Example

```python
def create_db_instance_complete(config: dict) -> dict:
    """
    Complete flow: create, wait, validate.
    
    Args:
        config: Dict with all DB instance parameters
    
    Returns:
        dict: Instance details with endpoint
    """
    # Create
    instance = create_db_instance(
        identifier=config['identifier'],
        instance_class=config['instance_class'],
        engine=config['engine'],
        engine_version=config['engine_version'],
        master_username=config['master_username'],
        master_password=config['master_password'],
        allocated_storage=config['allocated_storage'],
        security_group_ids=config['security_group_ids'],
        subnet_group_name=config.get('subnet_group_name'),
        multi_az=config.get('multi_az', False)
    )
    
    # Wait for available
    wait_for_instance_available(config['identifier'])
    
    # Get final state
    final_instance = describe_db_instance(config['identifier'])
    
    return {
        'identifier': final_instance['DBInstanceIdentifier'],
        'status': final_instance['DBInstanceStatus'],
        'endpoint': final_instance['Endpoint']['Address'],
        'port': final_instance['Endpoint']['Port'],
        'arn': final_instance['DBInstanceArn']
    }
```