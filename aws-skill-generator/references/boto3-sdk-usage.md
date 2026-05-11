# boto3 SDK Usage Reference

## Overview

boto3 is the official AWS SDK for Python. Use as **fallback** when AWS CLI fails after 3 retries.

## Client vs Resource

| Mode | Description | Use Case |
|------|-------------|----------|
| **Client** | Low-level API mapping | All operations; fine-grained control |
| **Resource** | High-level object-oriented | Simple CRUD; automatic pagination |

**Recommendation**: Use **Client** for operational skills (explicit API mapping).

## Bootstrap Pattern

```python
import boto3
import os

# boto3 auto-discovers credentials from the standard AWS chain:
#   1. Explicit env vars (AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY + AWS_SESSION_TOKEN)
#   2. AWS_PROFILE env var → ~/.aws/config (supports SSO / AssumeRole)
#   3. ~/.aws/credentials
#   4. ~/.aws/config
#   5. IAM Role (EC2/Lambda/ECS instance metadata)

# Client initialization
client = boto3.client(
    '[service]',
    region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
)

# With explicit profile (for SSO / cross-account roles)
# session = boto3.Session(profile_name=os.environ.get('AWS_PROFILE'))
# client = session.client('[service]', region_name='us-east-1')

# With explicit temporary credentials (for STS AssumeRole)
# client = boto3.client(
#     '[service]',
#     aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
#     aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
#     aws_session_token=os.environ.get('AWS_SESSION_TOKEN'),  # Required for temporary creds
#     region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
# )

# Verify credentials
identity = client.get_caller_identity() if hasattr(client, 'get_caller_identity') else None
# For services without STS-like operations, use a simple describe/list call
```

## Operation Patterns

### Create Operation

```python
response = client.create_[resource](
    # Required parameters per AWS API docs
    Name='{{user.resource_name}}',
    
    # Optional parameters
    Tags=[
        {'Key': 'Environment', 'Value': 'production'},
    ]
)

# Extract resource ID (verify path per service)
resource_id = response['[ResourceIdKey]']  # e.g., 'InstanceId', 'BucketName'
```

### Describe/Get Operation

```python
response = client.describe_[resource](
    [ResourceIdParam]='{{user.resource_id}}'
)

# Common response structure
# response['[ResourcesKey]'][0]['...']
```

### List Operation (Pagination)

```python
# boto3 handles pagination automatically with Paginator
paginator = client.get_paginator('list_[resources]')
pages = paginator.paginate()

for page in pages:
    for resource in page['[ResourcesKey]']:
        print(resource['Id'])

# Manual pagination (rare)
response = client.list_[resources](
    MaxResults=100,
    NextToken='token_from_previous_call'
)
```

### Delete Operation

```python
response = client.delete_[resource](
    [ResourceIdParam]='{{user.resource_id}}'
)

# Typically returns minimal response or empty dict
# Check for errors via exception handling
```

## Error Handling Pattern

```python
from botocore.exceptions import ClientError, BotoCoreError

try:
    response = client.create_[resource](**params)
except ClientError as e:
    error_code = e.response['Error']['Code']
    error_msg = e.response['Error']['Message']
    
    if error_code == 'InvalidParameter':
        # Fix and retry once
        pass
    elif error_code == 'QuotaExceeded':
        # HALT
        raise RuntimeError(f"Quota exceeded: {error_msg}")
    elif error_code == 'Throttling':
        # Retry with backoff
        pass
    else:
        raise
except BotoCoreError as e:
    # Connection/timeout issues
    # Retry up to 3 times
    raise
```

## Common Error Codes

| Error Code | HTTP | Action |
|------------|------|--------|
| InvalidParameter | 400 | Fix args; retry once |
| AccessDenied | 403 | HALT; check permissions |
| NotFound | 404 | HALT; resource doesn't exist |
| QuotaExceeded | 402/400 | HALT; request increase |
| Throttling | 429 | Backoff; retry 3x |
| InternalError | 500 | Retry 3x; then HALT |
| ServiceUnavailable | 503 | Retry 3x; then HALT |

## Retry Strategy Implementation

```python
import time
from botocore.config import Config

# Configure retry in client
config = Config(
    retries={
        'max_attempts': 3,
        'mode': 'adaptive'
    }
)
client = boto3.client('[service]', config=config)

# Manual retry (for specific cases)
def retry_operation(func, max_retries=3, backoff_base=2):
    for attempt in range(max_retries):
        try:
            return func()
        except ClientError as e:
            if e.response['Error']['Code'] in ['InvalidParameter', 'AccessDenied']:
                raise  # Non-retryable
            if attempt < max_retries - 1:
                time.sleep(backoff_base ** attempt)
            else:
                raise
```

## Polling Pattern (Async Operations)

```python
import time

def wait_for_state(client, resource_id, target_state, max_wait=300, interval=5):
    """
    Poll until resource reaches target_state or timeout.
    """
    for _ in range(max_wait // interval):
        response = client.describe_[resource](
            [ResourceIdParam]=resource_id
        )
        current_state = response['[StateKey]']  # e.g., 'State', 'Status'
        
        if current_state == target_state:
            return True
        if current_state in ['failed', 'error', 'deleted']:
            raise RuntimeError(f"Resource reached error state: {current_state}")
        
        time.sleep(interval)
    
    raise TimeoutError(f"Timeout waiting for {target_state}")

# Usage
wait_for_state(client, 'i-12345', 'running', max_wait=120)
```

## Service-Specific Notes (Template)

Replace these placeholders for each service:

| Placeholder | Description | Example |
|-------------|-------------|---------|
| `[service]` | boto3 service name | `ec2`, `s3`, `rds` |
| `[resource]` | Resource type suffix | `instance`, `bucket` |
| `[ResourceIdKey]` | Response ID field | `InstanceId`, `BucketName` |
| `[ResourceIdParam]` | Request ID param | `InstanceId`, `BucketName` |
| `[ResourcesKey]` | List response array key | `Reservations`, `Buckets` |
| `[StateKey]` | Status field name | `State`, `Status` |

## boto3 vs CLI Comparison

| Aspect | boto3 SDK | AWS CLI |
|--------|-----------|---------|
| Setup | Python env required | Python env required |
| Output | Python dict | JSON/text/table |
| Pagination | Automatic (Paginator) | Automatic |
| Retry | Config + manual | Config in ~/.aws/config |
| Best for | Integration tests, complex logic | Quick ops, shell scripts |