# boto3 SDK Usage — EKS

## Client Initialization

```python
import boto3

client = boto3.client('eks', region_name='us-east-1')
```

## Operation Patterns

### Create Cluster

```python
response = client.create_cluster(
    name='my-cluster',
    version='1.30',
    roleArn='arn:aws:iam::123456789012:role/eksClusterRole',
    resourcesVpcConfig={
        'subnetIds': ['subnet-aaa', 'subnet-bbb'],
        'securityGroupIds': ['sg-xxx']
    },
    kubernetesNetworkConfig={
        'serviceIpv4Cidr': '10.100.0.0/16'
    },
    logging={
        'clusterLogging': [
            {
                'types': ['api', 'audit', 'authenticator'],
                'enabled': True
            }
        ]
    },
    encryptionConfig=[
        {
            'resources': ['secrets'],
            'provider': {
                'keyArn': 'arn:aws:kms:us-east-1:123456789012:key/key-id'
            }
        }
    ],
    tags={
        'Environment': 'production'
    }
)

cluster_arn = response['cluster']['arn']
cluster_status = response['cluster']['status']
print(f"Cluster ARN: {cluster_arn}")
print(f"Status: {cluster_status}")
```

### Create Cluster with All Options

```python
response = client.create_cluster(
    name='my-cluster',
    version='1.30',
    roleArn='arn:aws:iam::123456789012:role/eksClusterRole',
    resourcesVpcConfig={
        'subnetIds': ['subnet-aaa', 'subnet-bbb', 'subnet-ccc'],
        'securityGroupIds': ['sg-xxx'],
        'endpointPublicAccess': True,
        'endpointPrivateAccess': True,
        'publicAccessCidrs': ['0.0.0.0/0']  # Restrict in production
    },
    kubernetesNetworkConfig={
        'serviceIpv4Cidr': '10.100.0.0/16',
        'ipFamily': 'ipv4'
    },
    logging={
        'clusterLogging': [
            {
                'types': ['api', 'audit', 'authenticator', 'controllerManager', 'scheduler'],
                'enabled': True
            }
        ]
    },
    authenticationMode='API_AND_CONFIG_MAP',
    accessConfig={
        'authenticationMode': 'API_AND_CONFIG_MAP',
        'bootstrapClusterCreatorAdminPermissions': True
    }
)
```

### Describe Cluster

```python
response = client.describe_cluster(name='my-cluster')

cluster = response['cluster']
print(f"Name: {cluster['name']}")
print(f"Status: {cluster['status']}")
print(f"Version: {cluster['version']}")
print(f"Endpoint: {cluster['endpoint']}")
print(f"ARN: {cluster['arn']}")

# Get certificate authority for kubectl
ca_data = cluster['certificateAuthority']['data']
print(f"CA Certificate: {ca_data}")

# Get VPC config
vpc_config = cluster['resourcesVpcConfig']
print(f"Subnets: {vpc_config['subnetIds']}")
print(f"Security Groups: {vpc_config['securityGroupIds']}")
```

### List Clusters

```python
response = client.list_clusters()

for cluster_name in response['clusters']:
    print(cluster_name)

# Pagination
paginator = client.get_paginator('list_clusters')
for page in paginator.paginate():
    for cluster_name in page['clusters']:
        print(cluster_name)
```

### Update Cluster Version

```python
response = client.update_cluster_version(
    name='my-cluster',
    version='1.31'
)

update_id = response['update']['id']
print(f"Update ID: {update_id}")

# Check update status
update_response = client.describe_update(
    name='my-cluster',
    updateId=update_id
)
print(f"Update Status: {update_response['update']['status']}")
```

### Update Cluster Configuration

```python
response = client.update_cluster_config(
    name='my-cluster',
    logging={
        'clusterLogging': [
            {
                'types': ['api', 'audit'],
                'enabled': True
            }
        ]
    }
)

update_id = response['update']['id']
```

### Create Managed Node Group

```python
response = client.create_nodegroup(
    clusterName='my-cluster',
    nodegroupName='my-nodegroup',
    scalingConfig={
        'minSize': 2,
        'maxSize': 10,
        'desiredSize': 3
    },
    instanceTypes=['t3.medium'],
    amiType='AL2_x86_64',
    nodeRole='arn:aws:iam::123456789012:role/eksNodeRole',
    subnets=['subnet-aaa', 'subnet-bbb'],
    labels={
        'env': 'production',
        'app': 'web'
    },
    tags={
        'Environment': 'production'
    },
    diskSize=50,  # GB
    capacityType='ON_DEMAND'  # or 'SPOT'
)

nodegroup_arn = response['nodegroup']['nodegroupArn']
print(f"Node Group ARN: {nodegroup_arn}")
```

### Create Node Group with Launch Template

```python
response = client.create_nodegroup(
    clusterName='my-cluster',
    nodegroupName='custom-nodegroup',
    launchTemplate={
        'id': 'lt-xxx',
        'version': '1'
    },
    nodeRole='arn:aws:iam::123456789012:role/eksNodeRole',
    subnets=['subnet-aaa', 'subnet-bbb'],
    scalingConfig={
        'minSize': 1,
        'maxSize': 5,
        'desiredSize': 2
    }
)
```

### Describe Node Group

```python
response = client.describe_nodegroup(
    clusterName='my-cluster',
    nodegroupName='my-nodegroup'
)

nodegroup = response['nodegroup']
print(f"Name: {nodegroup['nodegroupName']}")
print(f"Status: {nodegroup['status']}")
print(f"Scaling Config: {nodegroup['scalingConfig']}")
print(f"Instance Types: {nodegroup['instanceTypes']}")
print(f"Nodes: {nodegroup['nodeResource']}")

# Health issues
health = nodegroup.get('health', {})
if health.get('issues'):
    for issue in health['issues']:
        print(f"Health Issue: {issue['code']} - {issue['message']}")
```

### List Node Groups

```python
response = client.list_nodegroups(clusterName='my-cluster')

for nodegroup_name in response['nodegroups']:
    print(nodegroup_name)
```

### Update Node Group Config

```python
response = client.update_nodegroup_config(
    clusterName='my-cluster',
    nodegroupName='my-nodegroup',
    scalingConfig={
        'minSize': 2,
        'maxSize': 15,
        'desiredSize': 5
    },
    labels={
        'env': 'production',
        'team': 'backend'
    },
    taints=[
        {
            'key': 'dedicated',
            'value': 'gpu',
            'effect': 'NO_SCHEDULE'
        }
    ]
)
```

### Update Node Group Version

```python
response = client.update_nodegroup_version(
    clusterName='my-cluster',
    nodegroupName='my-nodegroup',
    version='1.30',
    launchTemplate={
        'id': 'lt-xxx',
        'version': '2'
    }
)
```

### Delete Node Group

```python
# Safety Gate: Confirm with user before deletion
response = client.delete_nodegroup(
    clusterName='my-cluster',
    nodegroupName='my-nodegroup'
)

print(f"Node group deletion initiated: {response['nodegroup']['status']}")
```

### Create Fargate Profile

```python
response = client.create_fargate_profile(
    clusterName='my-cluster',
    fargateProfileName='my-profile',
    podExecutionRoleArn='arn:aws:iam::123456789012:role/eksFargateRole',
    selectors=[
        {
            'namespace': 'default',
            'labels': {
                'app': 'my-app'
            }
        },
        {
            'namespace': 'kube-system',
            'labels': {
                'k8s-app': 'coredns'
            }
        }
    ],
    subnets=['subnet-aaa', 'subnet-bbb'],
    tags={
        'Environment': 'production'
    }
)

profile_arn = response['fargateProfile']['fargateProfileArn']
print(f"Fargate Profile ARN: {profile_arn}")
```

### Describe Fargate Profile

```python
response = client.describe_fargate_profile(
    clusterName='my-cluster',
    fargateProfileName='my-profile'
)

profile = response['fargateProfile']
print(f"Name: {profile['fargateProfileName']}")
print(f"Status: {profile['status']}")
print(f"Selectors: {profile['selectors']}")
```

### List Fargate Profiles

```python
response = client.list_fargate_profiles(clusterName='my-cluster')

for profile_name in response['fargateProfileNames']:
    print(profile_name)
```

### Delete Fargate Profile

```python
response = client.delete_fargate_profile(
    clusterName='my-cluster',
    fargateProfileName='my-profile'
)

print(f"Status: {response['fargateProfile']['status']}")
```

### Create Addon

```python
response = client.create-addon(
    clusterName='my-cluster',
    addonName='vpc-cni',
    addonVersion='v1.12.0-eksbuild.1',
    serviceAccountRoleArn='arn:aws:iam::123456789012:role/eksVPCCniRole',
    resolveConflicts='OVERWRITE',
    tags={
        'Addon': 'vpc-cni'
    }
)

addon_arn = response['addon']['addonArn']
print(f"Addon ARN: {addon_arn}")
```

### List Addons

```python
response = client.list_addons(clusterName='my-cluster')

for addon_name in response['addons']:
    print(addon_name)
```

### Describe Addon

```python
response = client.describe_addon(
    clusterName='my-cluster',
    addonName='vpc-cni'
)

addon = response['addon']
print(f"Name: {addon['addonName']}")
print(f"Version: {addon['addonVersion']}")
print(f"Status: {addon['status']}")
```

### Update Addon

```python
response = client.update-addon(
    clusterName='my-cluster',
    addonName='vpc-cni',
    addonVersion='v1.13.0-eksbuild.1',
    resolveConflicts='OVERWRITE'
)
```

### Delete Addon

```python
response = client.delete_addon(
    clusterName='my-cluster',
    addonName='vpc-cni'
)
```

### Delete Cluster (Complete Cleanup)

```python
# Safety Gate: Confirm with user before deletion

def delete_eks_cluster(client, cluster_name):
    """Complete EKS cluster deletion with cleanup."""
    
    # 1. Delete all Fargate profiles
    profiles = client.list_fargate_profiles(clusterName=cluster_name)
    for profile_name in profiles['fargateProfileNames']:
        print(f"Deleting Fargate profile: {profile_name}")
        client.delete_fargate_profile(
            clusterName=cluster_name,
            fargateProfileName=profile_name
        )
    
    # 2. Delete all node groups
    nodegroups = client.list_nodegroups(clusterName=cluster_name)
    for ng_name in nodegroups['nodegroups']:
        print(f"Deleting node group: {ng_name}")
        client.delete_nodegroup(
            clusterName=cluster_name,
            nodegroupName=ng_name
        )
    
    # 3. Delete all addons
    addons = client.list_addons(clusterName=cluster_name)
    for addon_name in addons['addons']:
        print(f"Deleting addon: {addon_name}")
        client.delete_addon(
            clusterName=cluster_name,
            addonName=addon_name
        )
    
    # 4. Wait for all deletions (poll)
    # ... wait logic ...
    
    # 5. Delete cluster
    print(f"Deleting cluster: {cluster_name}")
    response = client.delete_cluster(name=cluster_name)
    return response
```

### Describe Update

```python
response = client.describe_update(
    name='my-cluster',
    updateId='update-id'
)

update = response['update']
print(f"ID: {update['id']}")
print(f"Status: {update['status']}")
print(f"Type: {update['type']}")
print(f"Errors: {update.get('errors', [])}")
```

### List Updates

```python
response = client.list_updates(name='my-cluster')

for update in response['updates']:
    print(f"{update['id']}: {update['type']} - {update['status']}")
```

## Error Handling

```python
from botocore.exceptions import ClientError

try:
    response = client.create_cluster(
        name='my-cluster',
        version='1.30',
        roleArn='arn:aws:iam::123456789012:role/eksClusterRole',
        resourcesVpcConfig={
            'subnetIds': ['subnet-xxx']
        }
    )
except ClientError as e:
    code = e.response['Error']['Code']
    
    if code == 'ResourceInUseException':
        print("Cluster name already exists")
    elif code == 'ResourceLimitExceededException':
        print("EKS cluster quota exceeded")
    elif code == 'InvalidParameterException':
        print("Invalid parameter value")
    elif code == 'ThrottlingException':
        # Retry with backoff
        pass
    else:
        raise
```

## Common Error Codes

| Error Code | HTTP | Action |
|------------|------|--------|
| ResourceInUseException | 400 | HALT; cluster/name exists |
| ResourceLimitExceededException | 400 | HALT; quota exceeded |
| InvalidParameterException | 400 | Fix parameter; retry once |
| ResourceNotFoundException | 404 | HALT; resource not found |
| AccessDeniedException | 403 | HALT; check IAM permissions |
| ClientException | 400 | Fix config; retry once |
| ServiceUnavailableException | 500 | Retry 3x; HALT if persists |
| ThrottlingException | 429 | Backoff; retry 3x |

## Waiters

EKS provides built-in waiters:

```python
# Wait for cluster to be active
waiter = client.get_waiter('cluster_active')
waiter.wait(
    name='my-cluster',
    WaiterConfig={
        'Delay': 30,
        'MaxAttempts': 40
    }
)

# Wait for cluster to be deleted
waiter = client.get_waiter('cluster_deleted')
waiter.wait(name='my-cluster')

# Wait for nodegroup to be active
waiter = client.get_waiter('nodegroup_active')
waiter.wait(
    clusterName='my-cluster',
    nodegroupName='my-nodegroup'
)

# Wait for nodegroup to be deleted
waiter = client.get_waiter('nodegroup_deleted')
waiter.wait(
    clusterName='my-cluster',
    nodegroupName='my-nodegroup'
)
```

## Custom Polling

```python
import time

def wait_for_cluster_active(client, cluster_name, max_wait=900):
    """Wait for cluster to become ACTIVE."""
    
    for i in range(max_wait // 30):
        response = client.describe_cluster(name=cluster_name)
        status = response['cluster']['status']
        
        if status == 'ACTIVE':
            print(f"Cluster {cluster_name} is ACTIVE")
            return True
        elif status == 'FAILED':
            raise Exception(f"Cluster creation failed")
        
        print(f"Cluster status: {status}, waiting...")
        time.sleep(30)
    
    raise TimeoutError(f"Cluster not active after {max_wait}s")

def wait_for_update_complete(client, cluster_name, update_id, max_wait=600):
    """Wait for update to complete."""
    
    for i in range(max_wait // 10):
        response = client.describe_update(
            name=cluster_name,
            updateId=update_id
        )
        status = response['update']['status']
        
        if status == 'Successful':
            return True
        elif status in ['Failed', 'Cancelled']:
            raise Exception(f"Update failed: {status}")
        
        time.sleep(10)
    
    raise TimeoutError(f"Update not complete after {max_wait}s")
```

## Pagination Pattern

```python
paginator = client.get_paginator('list_clusters')
for page in paginator.paginate():
    for cluster_name in page['clusters']:
        print(cluster_name)
```

## Retry Strategy

```python
from botocore.config import Config

config = Config(retries={'max_attempts': 3, 'mode': 'standard'})
client = boto3.client('eks', region_name='us-east-1', config=config)
```