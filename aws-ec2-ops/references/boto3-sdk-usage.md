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

| Error Code | HTTP | Action |
|------------|------|--------|
| InvalidAMIID.NotFound | 400 | Use valid AMI |
| InvalidKeyPair.NotFound | 400 | Create or use existing keypair |
| InvalidSecurityGroupID.NotFound | 400 | Check SG in correct VPC |
| InvalidInstanceID.NotFound | 400 | Verify instance ID |
| InstanceLimitExceeded | 400 | Request quota increase |
| InsufficientInstanceCapacity | 500 | Try different type/AZ |
| ThrottlingException | 429 | Backoff and retry |
| UnauthorizedOperation | 403 | Check IAM permissions |

## Retry Configuration

```python
from botocore.config import Config

config = Config(
    retries={'max_attempts': 3, 'mode': 'adaptive'}
)

---

## AIOps: EC2-LB Target Diagnostics & Auto-Healing

### AH-EC2-01: Reboot Unhealthy Instance [AUTO_HEAL]

```python
import time
import boto3
from datetime import datetime, timedelta

ec2 = boto3.client('ec2')
cw = boto3.client('cloudwatch')

def reboot_and_verify_health(instance_id: str) -> bool:
    """Reboot EC2 and wait for status check recovery.
    Decision: [AUTO_HEAL] — reversible, no data loss.
    """
    ec2.reboot_instances(InstanceIds=[instance_id])
    print(f"Rebooted {instance_id}")
    
    for i in range(24):  # max 120s
        time.sleep(5)
        status = ec2.describe_instance_status(
            InstanceIds=[instance_id]
        )['InstanceStatuses']
        
        if status:
            s = status[0]
            sys_ok = s['SystemStatus']['Status'] == 'ok'
            ins_ok = s['InstanceStatus']['Status'] == 'ok'
            if sys_ok and ins_ok:
                print(f"Instance healthy after { (i+1) * 5 }s")
                return True
        else:
            print("Instance status not yet available...")
    
    print("Status check not recovered after 120s")
    return False
```

### RC-EC2-01: Unhealthy Target Diagnosis (ELB Integration)

```python
def diagnose_unhealthy_target(target_id: str, tg_arn: str):
    """Cross-module diagnosis: why is this EC2 instance unhealthy in LB?"""
    # 1. Check EC2 status
    status = ec2.describe_instance_status(
        InstanceIds=[target_id]
    )['InstanceStatuses']
    if status:
        s = status[0]
        print(f"System: {s['SystemStatus']['Status']}, "
              f"Instance: {s['InstanceStatus']['Status']}")
    
    # 2. Check CPU trend (last 30 min)
    end = datetime.utcnow()
    start = end - timedelta(minutes=30)
    cpu = cw.get_metric_statistics(
        Namespace='AWS/EC2',
        MetricName='CPUUtilization',
        Dimensions=[{'Name': 'InstanceId', 'Value': target_id}],
        StartTime=start, EndTime=end,
        Period=300, Statistics=['Average']
    )
    avg_cpu = sum(dp['Average'] for dp in cpu['Datapoints']) / max(len(cpu['Datapoints']), 1)
    print(f"CPU trend (30min): {avg_cpu:.1f}%")
    
    # 3. Check CloudTrail (cross-module)
    ct = boto3.client('cloudtrail')
    events = ct.lookup_events(
        LookupAttributes=[{'AttributeKey': 'ResourceName', 'AttributeValue': target_id}],
        StartTime=end - timedelta(hours=1), EndTime=end
    )
    for event in events.get('Events', []):
        print(f"Config change: {event['EventName']} at {event['EventTime']}")
    
    # 4. RCA conclusion
    if status and status[0]['SystemStatus']['Status'] != 'ok':
        return {'root_cause': 'AWS hardware issue', 'decision': '[AI_ASSIST]'}
    elif status and status[0]['InstanceStatus']['Status'] != 'ok':
        return {'root_cause': 'OS hang', 'decision': '[AUTO_HEAL] reboot'}
    elif avg_cpu > 90:
        return {'root_cause': 'CPU saturation', 'decision': '[AI_ASSIST] resize'}
    else:
        return {'root_cause': 'Application-level issue', 'decision': '[AI_ASSIST] SSM diagnostic'}
```

### AH-EC2-04: Capacity Pre-Warning (FORECAST)

```python
def forecast_cpu(instance_id: str) -> dict:
    """Predict CPU utilization for next 7 days."""
    cw_data = cw.get_metric_data(
        MetricDataQueries=[
            {'Id': 'm1', 'MetricStat': {
                'Metric': {'Namespace': 'AWS/EC2', 'MetricName': 'CPUUtilization',
                           'Dimensions': [{'Name': 'InstanceId', 'Value': instance_id}]},
                'Period': 3600, 'Stat': 'Average'}},
            {'Id': 'fc', 'Expression': 'FORECAST(m1, \"linear\", 168)',
             'Label': '7-Day Forecast'}
        ],
        StartTime=datetime.utcnow() - timedelta(days=14),
        EndTime=datetime.utcnow()
    )
    
    forecast_values = []
    for result in cw_data['MetricDataResults']:
        if result['Id'] == 'fc':
            forecast_values = result.get('Values', [])
    
    peak = max(forecast_values) if forecast_values else 0
    return {
        'instance_id': instance_id,
        'forecast_peak_cpu': peak,
        'exceeds_80pct': peak > 80,
        'recommendation': 'Resize instance' if peak > 80 else 'No action needed'
    }
```
client = boto3.client('ec2', config=config)
```