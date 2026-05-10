# boto3 SDK Usage — IAM

## Client Initialization

```python
import boto3
import os

# IAM is global service
client = boto3.client('iam')
```

## Operation Patterns

### Create User

```python
response = client.create_user(
    UserName='john',
    Path='/developers/'
)
print(f"Created: {response['User']['Arn']}")
```

### Get User

```python
response = client.get_user(UserName='john')
user = response['User']
print(f"ARN: {user['Arn']}")
print(f"Path: {user['Path']}")
print(f"Created: {user['CreateDate']}")
```

### List Users

```python
response = client.list_users()
for user in response['Users']:
    print(f"{user['UserName']} - {user['Arn']}")

# Pagination
paginator = client.get_paginator('list_users')
for page in paginator.paginate():
    for user in page['Users']:
        print(user['UserName'])
```

### Delete User

```python
# Must clean up attached entities first
# 1. Detach policies
attached_policies = client.list_attached_user_policies(UserName='john')
for policy in attached_policies['AttachedPolicies']:
    client.detach_user_policy(UserName='john', PolicyArn=policy['PolicyArn'])

# 2. Delete access keys
access_keys = client.list_access_keys(UserName='john')
for key in access_keys['AccessKeyMetadata']:
    client.delete_access_key(UserName='john', AccessKeyId=key['AccessKeyId'])

# 3. Remove from groups
groups = client.list_groups_for_user(UserName='john')
for group in groups['Groups']:
    client.remove_user_from_group(UserName='john', GroupName=group['GroupName'])

# 4. Delete user
client.delete_user(UserName='john')
```

### Create Role

```python
trust_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"Service": "ec2.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }
    ]
}

response = client.create_role(
    RoleName='EC2-SSM-Role',
    AssumeRolePolicyDocument=json.dumps(trust_policy)
)
print(f"Role ARN: {response['Role']['Arn']}")
```

### Attach Policy to Role

```python
response = client.attach_role_policy(
    RoleName='EC2-SSM-Role',
    PolicyArn='arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore'
)
print("Policy attached")
```

### Create Custom Policy

```python
policy_document = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": ["s3:GetObject", "s3:ListBucket"],
            "Resource": ["arn:aws:s3:::my-bucket", "arn:aws:s3:::my-bucket/*"]
        }
    ]
}

response = client.create_policy(
    PolicyName='S3-Read-Only',
    PolicyDocument=json.dumps(policy_document)
)
print(f"Policy ARN: {response['Policy']['Arn']}")
```

### Create Access Key (Sensitive)

```python
response = client.create_access_key(UserName='john')
access_key = response['AccessKey']

# IMPORTANT: SecretAccessKey only available once
print(f"AccessKeyId: {access_key['AccessKeyId']}")
print(f"SecretAccessKey: {access_key['SecretAccessKey']}")  # Save immediately
print(f"Status: {access_key['Status']}")
```

### Create Group

```python
response = client.create_group(GroupName='developers')
print(f"Group ARN: {response['Group']['Arn']}")

# Add user to group
client.add_user_to_group(GroupName='developers', UserName='john')

# Attach policy to group
client.attach_group_policy(
    GroupName='developers',
    PolicyArn='arn:aws:iam::aws:policy/ReadOnlyAccess'
)
```

### Get Policy Document

```python
response = client.get_policy_version(
    PolicyArn='arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess',
    VersionId='v1'
)
policy_doc = json.loads(response['PolicyVersion']['Document'])
```

### Put Inline Policy

```python
inline_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {"Effect": "Allow", "Action": "s3:GetObject", "Resource": "arn:aws:s3:::bucket/*"}
    ]
}

client.put_user_policy(
    UserName='john',
    PolicyName='S3GetObject',
    PolicyDocument=json.dumps(inline_policy)
)
```

## Error Handling

```python
from botocore.exceptions import ClientError

try:
    response = client.create_user(UserName='john')
except ClientError as e:
    code = e.response['Error']['Code']
    
    if code == 'EntityAlreadyExists':
        print("User already exists")
    elif code == 'InvalidInput':
        print("Invalid user name or path")
    elif code == 'LimitExceeded':
        print("IAM entity limit reached")
    elif code == 'Throttling':
        # IAM is eventually consistent; retry with backoff
        pass
    else:
        raise
```

## Common Error Codes

| Error Code | HTTP | Action |
|------------|------|--------|
| EntityAlreadyExists | 409 | HALT; entity already exists |
| NoSuchEntity | 404 | HALT; user/role/policy not found |
| InvalidInput | 400 | Fix name/path; retry once |
| LimitExceeded | 400 | HALT; request quota increase |
| MalformedPolicyDocument | 400 | Fix policy JSON; retry once |
| ThrottlingException | 429 | Backoff; retry 3x |
| ServiceFailure | 500 | Retry 3x; then HALT |

## Retry Strategy (IAM Eventual Consistency)

IAM is **eventually consistent** — changes may take seconds to propagate:

```python
import time
from botocore.config import Config

config = Config(retries={'max_attempts': 3, 'mode': 'standard'})
client = boto3.client('iam', config=config)

# Verify after create
def verify_user_exists(client, user_name, max_wait=30):
    for _ in range(max_wait // 2):
        try:
            client.get_user(UserName=user_name)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntity':
                time.sleep(2)
            else:
                raise
    raise TimeoutError(f"User {user_name} not visible after {max_wait}s")
```