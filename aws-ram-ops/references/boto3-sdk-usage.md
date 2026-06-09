# boto3 SDK Usage — AWS Resource Access Manager (RAM)

## Bootstrap

```python
import boto3
import os

client = boto3.client(
    'ram',
    region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
)

# With SSO profile
# session = boto3.Session(profile_name=os.environ.get('AWS_PROFILE'))
# client = session.client('ram', region_name='us-east-1')
```

## Common Patterns

### Create Resource Share
```python
response = client.create_resource_share(
    name='shared-subnet-prod',
    resourceArns=['arn:aws:ec2:us-east-1:123456789012:subnet/subnet-abc123'],
    principals=['222222222222'],
    allowExternalPrincipals=True
)
share_arn = response['resourceShare']['resourceShareArn']

# Verify
shares = client.get_resource_shares(resourceShareArns=[share_arn])
print(shares['resourceShares'][0]['status'])
```

### Accept Invitation
```python
client.accept_resource_share_invitation(
    resourceShareInvitationArn='arn:aws:ram:us-east-1:111111111111:resource-share-invitation/abc-123'
)

# Verify
invitations = client.get_resource_share_invitations(
    resourceShareInvitationArns=['arn:aws:ram:us-east-1:111111111111:resource-share-invitation/abc-123']
)
print(invitations['resourceShareInvitations'][0]['status'])
```

### List Shared Resources
```python
# All resources in account
paginator = client.get_paginator('list_resources')
for page in paginator.paginate():
    for resource in page['resources']:
        print(resource['arn'], resource['type'], resource['status'])

# Resources in a specific share
resources = client.list_resources(
    resourceArns=['arn:aws:ec2:us-east-1:123456789012:subnet/subnet-abc123']
)
```

### Associate and Disassociate
```python
# Associate principal
client.associate_resource_share(
    resourceShareArn=share_arn,
    principals=['333333333333'],
    resourceArns=['arn:aws:ec2:us-east-1:123456789012:subnet/subnet-abc123']
)

# Disassociate
client.disassociate_resource_share(
    resourceShareArn=share_arn,
    principals=['333333333333'],
    resourceArns=['arn:aws:ec2:us-east-1:123456789012:subnet/subnet-abc123']
)
```

### Permission Management
```python
# List permissions
perms = client.list_permissions()
for p in perms['permissions']:
    print(p['permissionArn'], p['permissionName'])

# Associate permission to share
client.associate_resource_share_permission(
    resourceShareArn=share_arn,
    permissionArn='arn:aws:ram::aws:permission/AmazonEC2VPCSubnetReadWriteAccess'
)

# Delete permission
client.delete_permission(permissionArn='arn:aws:ram:us-east-1:123456789012:permission/custom')
```

### Enable Organization Sharing
```python
client.enable_sharing_with_aws_organization()
```

### Error Handling Pattern
```python
from botocore.exceptions import ClientError

try:
    client.delete_resource_share(resourceShareArn=share_arn)
except ClientError as e:
    code = e.response['Error']['Code']
    if code == 'ResourceNotFoundException':
        print("Resource share not found")
    elif code == 'OperationNotPermittedException':
        print("Check AWS Organizations settings")
    elif code == 'ServerException':
        # Backoff and retry
        pass
    else:
        print(f"Error: {code}")
```
