# boto3 SDK Usage — Auto Scaling

## Overview

boto3 `autoscaling` client is the fallback path when AWS CLI fails after 3 retries.

## Bootstrap Pattern

```python
import boto3
import os

client = boto3.client(
    'autoscaling',
    region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
)

# With explicit profile (SSO / AssumeRole)
# session = boto3.Session(profile_name=os.environ.get('AWS_PROFILE'))
# client = session.client('autoscaling', region_name='us-east-1')

# Verify credentials
identity = client.get_caller_identity() if hasattr(client, 'get_caller_identity') else None
```

## Common Patterns

### Create Auto Scaling Group
```python
response = client.create_auto_scaling_group(
    AutoScalingGroupName='my-asg',
    LaunchTemplate={
        'LaunchTemplateName': 'my-lt',
        'Version': '$Default'
    },
    MinSize=1,
    MaxSize=5,
    DesiredCapacity=2,
    VPCZoneIdentifier='subnet-abc12345,subnet-def67890',
    HealthCheckType='ELB',
    HealthCheckGracePeriod=300,
    DefaultCooldown=300,
    Tags=[
        {
            'Key': 'Name',
            'Value': 'my-asg-instance',
            'PropagateAtLaunch': True
        },
        {
            'Key': 'Environment',
            'Value': 'production',
            'PropagateAtLaunch': True
        }
    ]
)
# ASG creation returns HTTP 200 with no body
```

### Describe Auto Scaling Groups
```python
paginator = client.get_paginator('describe_auto_scaling_groups')
pages = paginator.paginate(AutoScalingGroupNames=['my-asg'])
for page in pages:
    for asg in page['AutoScalingGroups']:
        print(asg['AutoScalingGroupName'],
              asg['MinSize'], asg['MaxSize'], asg['DesiredCapacity'])
        for inst in asg.get('Instances', []):
            print(f"  {inst['InstanceId']} {inst['LifecycleState']} {inst['HealthStatus']}")
```

### Update Auto Scaling Group
```python
response = client.update_auto_scaling_group(
    AutoScalingGroupName='my-asg',
    MinSize=2,
    MaxSize=10,
    DesiredCapacity=3
)
```

### Delete Auto Scaling Group
```python
# Scale to 0 first
client.update_auto_scaling_group(
    AutoScalingGroupName='my-asg',
    MinSize=0, MaxSize=0, DesiredCapacity=0
)

# Wait for instances to terminate
waiter = client.get_waiter('group_not_exists')
waiter.wait(AutoScalingGroupNames=['my-asg'])

# Or force delete (destructive, requires confirmation)
client.delete_auto_scaling_group(
    AutoScalingGroupName='my-asg',
    ForceDelete=True
)
```

### Put Scaling Policy (Target Tracking)
```python
response = client.put_scaling_policy(
    AutoScalingGroupName='my-asg',
    PolicyName='cpu-target-50',
    PolicyType='TargetTrackingScaling',
    TargetTrackingConfiguration={
        'TargetValue': 50.0,
        'PredefinedMetricSpecification': {
            'PredefinedMetricType': 'ASGAverageCPUUtilization'
        }
    }
)
# Returns PolicyARN and Alarms
policy_arn = response['PolicyARN']
```

### Put Scaling Policy (Step Scaling)
```python
response = client.put_scaling_policy(
    AutoScalingGroupName='my-asg',
    PolicyName='scale-out-step',
    PolicyType='StepScaling',
    AdjustmentType='ChangeInCapacity',
    StepAdjustments=[
        {'MetricIntervalLowerBound': 0.0, 'ScalingAdjustment': 1},
        {'MetricIntervalLowerBound': 20.0, 'ScalingAdjustment': 2},
        {'MetricIntervalLowerBound': 40.0, 'ScalingAdjustment': 4},
    ],
    Cooldown=300
)
```

### Put Scheduled Action
```python
response = client.put_scheduled_update_group_action(
    AutoScalingGroupName='my-asg',
    ScheduledActionName='scale-up-morning',
    Recurrence='0 9 * * 1-5',
    MinSize=2,
    MaxSize=10,
    DesiredCapacity=4
)
```

### Instance Refresh
```python
response = client.start_instance_refresh(
    AutoScalingGroupName='my-asg',
    Preferences={
        'MinHealthyPercentage': 90,
        'InstanceWarmup': 300
    }
)
refresh_id = response['InstanceRefreshId']

# Poll until complete
import time
while True:
    resp = client.describe_instance_refreshes(
        AutoScalingGroupName='my-asg',
        InstanceRefreshIds=[refresh_id]
    )
    status = resp['InstanceRefreshes'][0]['Status']
    if status in ['Successful', 'Failed', 'Cancelled']:
        break
    time.sleep(10)
```

### Attach / Detach Instances
```python
# Attach
client.attach_instances(
    AutoScalingGroupName='my-asg',
    InstanceIds=['i-1234567890abcdef0']
)

# Detach
client.detach_instances(
    AutoScalingGroupName='my-asg',
    InstanceIds=['i-1234567890abcdef0'],
    ShouldDecrementDesiredCapacity=True
)
```

### Suspend / Resume Processes
```python
# Suspend
client.suspend_processes(
    AutoScalingGroupName='my-asg',
    ScalingProcesses=['HealthCheck', 'ReplaceUnhealthy']
)

# Resume
client.resume_processes(
    AutoScalingGroupName='my-asg',
    ScalingProcesses=['HealthCheck', 'ReplaceUnhealthy']
)
```

### Lifecycle Hook
```python
client.put_lifecycle_hook(
    LifecycleHookName='my-hook',
    AutoScalingGroupName='my-asg',
    LifecycleTransition='autoscaling:EC2_INSTANCE_LAUNCHING',
    HeartbeatTimeout=300,
    DefaultResult='CONTINUE',
    NotificationTargetARN='arn:aws:sns:us-east-1:123456789012:my-topic',
    RoleARN='arn:aws:iam::123456789012:role/aws-service-role/autoscaling.amazonaws.com/AWSServiceRoleForAutoScaling'
)
```

### Launch Configuration (Legacy)
```python
response = client.create_launch_configuration(
    LaunchConfigurationName='my-lc',
    ImageId='ami-0abcdef1234567890',
    InstanceType='t3.micro',
    SecurityGroups=['sg-12345678'],
    KeyName='my-keypair',
    AssociatePublicIpAddress=True,
    InstanceMonitoring={'Enabled': True}
)
```

### Create or Update Tags
```python
client.create_or_update_tags(
    Tags=[{
        'ResourceId': 'my-asg',
        'ResourceType': 'auto-scaling-group',
        'Key': 'Environment',
        'Value': 'production',
        'PropagateAtLaunch': True
    }]
)
```

### Warm Pool Configuration
```python
client.put_warm_pool(
    AutoScalingGroupName='my-asg',
    MinSize=0,
    MaxGroupPreparedCapacity=2,
    PoolState='Stopped'
)
```

## Waiters

| Waiter | Description | Default Poll |
|--------|-------------|-------------|
| `group_exists` | Wait until ASG exists | 10s interval, 600s timeout |
| `group_not_exists` | Wait until ASG is deleted | 10s interval, 600s timeout |
| `group_in_service` | Wait until all instances InService | 15s interval, 600s timeout |

```python
waiter = client.get_waiter('group_in_service')
waiter.wait(AutoScalingGroupNames=['my-asg'])
```

## Error Handling Pattern

```python
from botocore.exceptions import ClientError, BotoCoreError

try:
    response = client.create_auto_scaling_group(**params)
except ClientError as e:
    error_code = e.response['Error']['Code']
    error_msg = e.response['Error']['Message']

    if error_code == 'AlreadyExists':
        raise RuntimeError(f"ASG already exists: {error_msg}")
    elif error_code == 'ValidationError':
        raise RuntimeError(f"Invalid parameters: {error_msg}")
    elif error_code == 'ScalingActivityInProgress':
        raise RuntimeError(f"Activity in progress: {error_msg}")
    elif error_code == 'ResourceContention':
        # Throttling-like; retry with backoff
        pass
    elif error_code == 'LimitExceeded':
        raise RuntimeError(f"Quota exceeded: {error_msg}")
    else:
        raise
except BotoCoreError as e:
    raise

# Common error codes
error_map = {
    'AlreadyExists': 'ASG with this name already exists',
    'ValidationError': 'Check parameter values',
    'ScalingActivityInProgress': 'Wait for current activity to finish',
    'ResourceContention': 'Service contention; retry with backoff',
    'LimitExceeded': 'Quota exceeded; request increase',
    'InvalidParameter': 'Check provided parameters',
    'ResourceNotFoundException': 'Resource does not exist',
    'InternalServiceFailure': 'AWS internal error; retry',
}
```

## Retry Strategy

```python
import time
from botocore.config import Config

config = Config(
    retries={
        'max_attempts': 3,
        'mode': 'adaptive'
    }
)
client = boto3.client('autoscaling', config=config)
```