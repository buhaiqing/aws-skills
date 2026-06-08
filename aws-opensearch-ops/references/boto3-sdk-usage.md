# boto3 SDK Usage — OpenSearch Service

Python boto3 patterns for OpenSearch Service operations. All functions use `handle_opensearch_error(e)` for error handling.

## Client Initialization
```python
import boto3
from botocore.exceptions import ClientError
client = boto3.client('opensearch', region_name='{{env.AWS_DEFAULT_REGION}}')
```

## Domain Operations

### Create Domain
```python
def create_domain(name, engine_version, instance_type, instance_count=2,
                  volume_size=100, subnet_ids=None, sg_ids=None,
                  master_user=None, master_password=None, kms_key_id=None):
    params = {
        'DomainName': name,
        'EngineVersion': engine_version,
        'ClusterConfig': {
            'InstanceType': instance_type,
            'InstanceCount': instance_count,
            'DedicatedMasterEnabled': False,
            'ZoneAwarenessEnabled': True,
            'ZoneAwarenessConfig': {'AvailabilityZoneCount': 3}
        },
        'EBSOptions': {'EBSEnabled': True, 'VolumeType': 'gp3', 'VolumeSize': volume_size},
        'EncryptionAtRestOptions': {'Enabled': True},
        'NodeToNodeEncryptionOptions': {'Enabled': True},
        'DomainEndpointOptions': {'EnforceHTTPS': True, 'TLSSecurityPolicy': 'Policy-Min-TLS-1-2-2019-07'},
        'AdvancedSecurityOptions': {'Enabled': True, 'InternalUserDatabaseEnabled': True}
    }
    if subnet_ids and sg_ids:
        params['VPCOptions'] = {'SubnetIds': subnet_ids, 'SecurityGroupIds': sg_ids}
    if master_user and master_password:
        params['AdvancedSecurityOptions']['MasterUserOptions'] = {
            'MasterUserName': master_user, 'MasterUserPassword': master_password
        }
    if kms_key_id:
        params['EncryptionAtRestOptions']['KmsKeyId'] = kms_key_id
    try: return client.create_domain(**params)['DomainStatus']
    except ClientError as e: handle_opensearch_error(e)
```

### Describe & Read
```python
def describe_domain(name):
    try: return client.describe_domain(DomainName=name)['DomainStatus']
    except ClientError as e: handle_opensearch_error(e)

def list_domains():
    try: return client.list_domain_names()['DomainNames']
    except ClientError as e: handle_opensearch_error(e)

def get_domain_status(name):
    ds = describe_domain(name)
    return ds.get('Processing', True), ds.get('Endpoint'), ds.get('ARN')
```

### Update Domain Config
```python
def update_domain_config(name, instance_type=None, volume_size=None,
                         access_policies=None, advanced_security=None):
    params = {'DomainName': name}
    if instance_type:
        params['ClusterConfig'] = {'InstanceType': instance_type}
    if volume_size:
        params['EBSOptions'] = {'VolumeSize': volume_size}
    if access_policies:
        params['AccessPolicies'] = access_policies
    if advanced_security:
        params['AdvancedSecurityOptions'] = advanced_security
    try: return client.update_domain_config(**params)['DomainConfig']
    except ClientError as e: handle_opensearch_error(e)
```

### Delete Domain
```python
def delete_domain(name):
    try: return client.delete_domain(DomainName=name)['DomainStatus']
    except ClientError as e: handle_opensearch_error(e)
```

### Upgrade Domain
```python
def get_compatible_versions(name):
    try: return client.get_compatible_versions(DomainName=name)['CompatibleVersions']
    except ClientError as e: handle_opensearch_error(e)

def upgrade_domain(name, target_version, perform_check_only=False):
    try:
        return client.upgrade_domain(
            DomainName=name, TargetVersion=target_version,
            PerformCheckOnly=perform_check_only
        )['UpgradeHistory']
    except ClientError as e: handle_opensearch_error(e)
```

## Snapshot Operations

```python
def create_snapshot(domain_name, snapshot_name, repository_name):
    try:
        return client.create_snapshot(
            DomainName=domain_name, SnapshotName=snapshot_name,
            RepositoryName=repository_name
        )['Snapshot']
    except ClientError as e: handle_opensearch_error(e)

def describe_snapshots(domain_name, repository_name):
    try:
        return client.describe_snapshots(
            DomainName=domain_name, RepositoryName=repository_name
        )['SnapshotList']
    except ClientError as e: handle_opensearch_error(e)

def delete_snapshot(domain_name, snapshot_name, repository_name):
    try:
        return client.delete_snapshot(
            DomainName=domain_name, SnapshotName=snapshot_name,
            RepositoryName=repository_name
        )['Snapshot']
    except ClientError as e: handle_opensearch_error(e)
```

## VPC Endpoint Operations

```python
def create_vpc_endpoint(domain_arn, subnet_ids, sg_ids):
    try:
        return client.create_vpc_endpoint(
            DomainArn=domain_arn,
            VPCOptions={'SubnetIds': subnet_ids, 'SecurityGroupIds': sg_ids}
        )['VpcEndpoint']
    except ClientError as e: handle_opensearch_error(e)

def describe_vpc_endpoints(endpoint_ids):
    try: return client.describe_vpc_endpoints(VpcEndpointIds=endpoint_ids)['VpcEndpoints']
    except ClientError as e: handle_opensearch_error(e)

def delete_vpc_endpoint(endpoint_id):
    try: return client.delete_vpc_endpoint(VpcEndpointId=endpoint_id)['VpcEndpoint']
    except ClientError as e: handle_opensearch_error(e)
```

## Data Ingestion Operations

```python
def create_ingestion(pipeline_name, config_body, subnet_ids=None, sg_ids=None):
    params = {'PipelineName': pipeline_name, 'PipelineConfigurationBody': config_body}
    if subnet_ids and sg_ids:
        params['VPCOptions'] = {'SubnetIds': subnet_ids, 'SecurityGroupIds': sg_ids}
    try: return client.create_ingestion(**params)['Pipeline']
    except ClientError as e: handle_opensearch_error(e)

def describe_ingestion(pipeline_name):
    try: return client.describe_ingestion(PipelineName=pipeline_name)['Pipeline']
    except ClientError as e: handle_opensearch_error(e)

def list_ingestions():
    try: return client.list_ingestions()['IngestionPipelineSummaries']
    except ClientError as e: handle_opensearch_error(e)

def delete_ingestion(pipeline_name):
    try: return client.delete_ingestion(PipelineName=pipeline_name)['Pipeline']
    except ClientError as e: handle_opensearch_error(e)
```

## Tag Operations

```python
def add_tags(arn, tags):
    # tags = [{'Key': 'env', 'Value': 'prod'}]
    try: return client.add_tags(ARN=arn, TagList=tags)
    except ClientError as e: handle_opensearch_error(e)

def remove_tags(arn, keys):
    try: return client.remove_tags(ARN=arn, TagKeys=keys)
    except ClientError as e: handle_opensearch_error(e)

def list_tags(arn):
    try: return client.list_tags(ARN=arn)['TagList']
    except ClientError as e: handle_opensearch_error(e)
```

## Error Handling

```python
def handle_opensearch_error(error):
    code = error.response['Error']['Code']
    msg = error.response['Error']['Message']
    recovery_map = {
        'ResourceAlreadyExistsException': 'HALT - Domain exists',
        'InvalidTypeException': 'FIX - Use supported instance type',
        'ValidationException': 'HALT - Fix parameters',
        'LimitExceededException': 'HALT - Request quota increase',
        'ResourceNotFoundException': 'HALT - Verify domain name / region',
        'BaseException': 'RETRY - Transient error',
        'InternalException': 'RETRY - AWS internal error',
        'SnapshotInProgressException': 'HALT - Wait for snapshot to complete',
        'DomainProcessingException': 'HALT - Domain is processing; retry later',
    }
    recovery = recovery_map.get(code, 'HALT - Check AWS docs.')
    raise Exception(f"OpenSearch Error [{code}]: {msg}\nRecovery: {recovery}")
```

## Polling Helpers

```python
import time

def wait_for_domain_active(name, timeout=1800):
    for _ in range(timeout // 30):
        ds = describe_domain(name)
        if not ds.get('Processing', True):
            return True
        time.sleep(30)
    return False

def wait_for_domain_deleted(name, timeout=900):
    for _ in range(timeout // 30):
        try:
            describe_domain(name)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return True
            raise
        time.sleep(30)
    return False
```
