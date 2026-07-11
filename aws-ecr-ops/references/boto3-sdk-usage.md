# AWS ECR — boto3 SDK Usage

## Client Setup
```python
import boto3
client = boto3.client('ecr', region_name='{{user.region}}')
```

## Repository CRUD

```python
# Create repository with scanning enabled
response = client.create_repository(
    repositoryName='{{user.repository_name}}',
    imageScanningConfiguration={'scanOnPush': True}
)
repo_uri = response['repository']['repositoryUri']

# List repositories
repos = client.describe_repositories()
for r in repos['repositories']:
    print(r['repositoryName'], r['repositoryUri'])

# Delete repository (destructive — confirm first)
response = client.delete_repository(
    repositoryName='{{user.repository_name}}'
)

# Force delete non-empty
response = client.delete_repository(
    repositoryName='{{user.repository_name}}',
    force=True
)
```

## Image Management

```python
# List images
images = client.list_images(
    repositoryName='{{user.repository_name}}'
)
for img in images['imageIds']:
    print(img.get('imageTag', '(untagged)'), img['imageDigest'])

# Batch delete images (destructive — confirm first)
response = client.batch_delete_image(
    repositoryName='{{user.repository_name}}',
    imageIds=[
        {'imageTag': 'v1.0.0'},
        {'imageTag': 'v0.9.0'}
    ]
)
```

## Lifecycle Policy

```python
# Put lifecycle policy
with open('policy.json') as f:
    policy_text = f.read()
response = client.put_lifecycle_policy(
    repositoryName='{{user.repository_name}}',
    lifecyclePolicyText=policy_text
)

# Get lifecycle policy
response = client.get_lifecycle_policy(
    repositoryName='{{user.repository_name}}'
)
```

## Repository Policy

```python
# Set repository policy
with open('policy.json') as f:
    policy_text = f.read()
response = client.set_repository_policy(
    repositoryName='{{user.repository_name}}',
    policyText=policy_text
)

# Get repository policy
response = client.get_repository_policy(
    repositoryName='{{user.repository_name}}'
)
```

## Image Scanning

```python
# Start scan
client.start_image_scan(
    repositoryName='{{user.repository_name}}',
    imageId={'imageTag': 'latest'}
)

# Get findings
findings = client.describe_image_scan_findings(
    repositoryName='{{user.repository_name}}',
    imageId={'imageTag': 'latest'}
)
```

## Common Error Handling
```python
from botocore.exceptions import ClientError

try:
    client.describe_repositories(repositoryNames=['{{user.repository_name}}'])
except ClientError as e:
    code = e.response['Error']['Code']
    if code == 'RepositoryNotFoundException':
        print(f"Repository not found: {e}")
    elif code == 'InvalidParameterException':
        print(f"Invalid parameter: {e}")
    else:
        raise
```
