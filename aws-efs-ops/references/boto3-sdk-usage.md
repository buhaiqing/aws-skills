# AWS EFS — boto3 SDK Usage

## Client Setup
```python
import boto3
client = boto3.client('efs', region_name='{{user.region}}')
```

## File System CRUD

```python
# Create file system
response = client.create_file_system(
    CreationToken='{{user.file_system_token}}',
    PerformanceMode='generalPurpose',
    ThroughputMode='bursting',
    Encrypted=True
)
fs_id = response['FileSystemId']

# List file systems
response = client.describe_file_systems()
for fs in response['FileSystems']:
    print(fs['FileSystemId'], fs['LifeCycleState'])

# Delete file system (destructive — confirm first)
client.delete_file_system(FileSystemId='{{user.file_system_id}}')
```

## Mount Targets

```python
# Create mount target
response = client.create_mount_target(
    FileSystemId='{{user.file_system_id}}',
    SubnetId='{{user.subnet_id}}',
    SecurityGroups=['{{user.security_group_id}}']
)
mt_id = response['MountTargetId']

# List mount targets
response = client.describe_mount_targets(
    FileSystemId='{{user.file_system_id}}'
)

# Delete mount target (destructive — confirm first)
client.delete_mount_target(MountTargetId='{{user.mount_target_id}}')
```

## Access Points

```python
# Create access point
response = client.create_access_point(
    FileSystemId='{{user.file_system_id}}',
    PosixUser={'Uid': 1000, 'Gid': 1000},
    RootDirectory={
        'Path': '/data',
        'CreationInfo': {
            'OwnerUid': 1000,
            'OwnerGid': 1000,
            'Permissions': '0755'
        }
    }
)
ap_id = response['AccessPointId']

# Delete access point (destructive — confirm first)
client.delete_access_point(AccessPointId='{{user.access_point_id}}')
```

## Lifecycle Policy

```python
client.put_lifecycle_configuration(
    FileSystemId='{{user.file_system_id}}',
    LifecyclePolicies=[
        {'TransitionToIA': 'AFTER_30_DAYS'}
    ]
)
```

## Common Error Handling
```python
from botocore.exceptions import ClientError

try:
    client.describe_file_systems(FileSystemId='{{user.file_system_id}}')
except ClientError as e:
    code = e.response['Error']['Code']
    if code == 'FileSystemNotFoundException':
        print(f"File system not found: {e}")
    elif code == 'BadRequest':
        print(f"Bad request: {e}")
    else:
        raise
```
