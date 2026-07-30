# boto3 SDK Usage — EC2

## Client Initialization

```python
import boto3
import os

client = boto3.client(
    'ec2',
    region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
)
```

## Operation Patterns

### Run Instance

```python
response = client.run_instances(
    ImageId='ami-0abcdef1234567890',
    InstanceType='t3.micro',
    KeyName='my-keypair',
    SecurityGroupIds=['sg-12345678'],
    SubnetId='subnet-12345678',
    TagSpecifications=[
        {
            'ResourceType': 'instance',
            'Tags': [{'Key': 'Name', 'Value': 'my-instance'}]
        }
    ],
    MinCount=1,
    MaxCount=1
)

instance_id = response['Instances'][0]['InstanceId']
print(f"Launched: {instance_id}")
```

### Describe Instance

```python
response = client.describe_instances(
    InstanceIds=['i-1234567890abcdef0']
)

instance = response['Reservations'][0]['Instances'][0]
print(f"State: {instance['State']['Name']}")
print(f"Type: {instance['InstanceType']}")
print(f"Private IP: {instance.get('PrivateIpAddress')}")
print(f"Public IP: {instance.get('PublicIpAddress')}")
```

### List Instances (Paginator)

```python
paginator = client.get_paginator('describe_instances')
for page in paginator.paginate():
    for reservation in page['Reservations']:
        for instance in reservation['Instances']:
            print(f"{instance['InstanceId']}: {instance['State']['Name']}")
```

### Filter by State

```python
response = client.describe_instances(
    Filters=[
        {'Name': 'instance-state-name', 'Values': ['running']}
    ]
)
```

### Stop Instance

```python
response = client.stop_instances(
    InstanceIds=['i-1234567890abcdef0']
)
print(f"Stopping: {response['StoppingInstances'][0]['InstanceId']}")
```

### Start Instance

```python
response = client.start_instances(
    InstanceIds=['i-1234567890abcdef0']
)
print(f"Starting: {response['StartingInstances'][0]['InstanceId']}")
```

### Terminate Instance

```python
response = client.terminate_instances(
    InstanceIds=['i-1234567890abcdef0']
)
print(f"Terminated: {response['TerminatingInstances'][0]['InstanceId']}")
```

## Error Handling

```python
from botocore.exceptions import ClientError

try:
    response = client.run_instances(**params)
except ClientError as e:
    code = e.response['Error']['Code']
    
    if code == 'InvalidAMIID.NotFound':
        print("AMI not found. Use valid AMI ID.")
    elif code == 'InvalidKeyPair.NotFound':
        print("KeyPair not found.")
    elif code == 'InstanceLimitExceeded':
        print("Quota exceeded. Request increase.")
    elif code == 'InsufficientInstanceCapacity':
        print("No capacity. Try different instance type or AZ.")
    elif code == 'Throttling':
        # Retry with backoff
        pass
    else:
        raise
```

## Polling Pattern

```python
import time

def wait_for_state(client, instance_id, target_state, max_wait=120, interval=5):
    for _ in range(max_wait // interval):
        response = client.describe_instances(InstanceIds=[instance_id])
        state = response['Reservations'][0]['Instances'][0]['State']['Name']
        
        if state == target_state:
            return True
        if state in ['terminated', 'shutting-down']:
            raise RuntimeError(f"Unexpected state: {state}")
        
        time.sleep(interval)
    
    raise TimeoutError(f"Timeout waiting for {target_state}")

# Usage
wait_for_state(client, 'i-1234567890abcdef0', 'running')
```

## Common Error Codes

See [troubleshooting.md — Common Error Codes](troubleshooting.md#common-error-codes).

## Retry Configuration

```python
import boto3
from botocore.config import Config

config = Config(
    retries={'max_attempts': 3, 'mode': 'adaptive'}
)
client = boto3.client('ec2', config=config)
```

## AIOps diagnostics

Canonical AIOps flows (LB unhealthy RCA, FORECAST, SSM) live in [troubleshooting.md](troubleshooting.md#aiops-ec2-lb-cross-module-diagnostic-flow). Do not duplicate SDK here.