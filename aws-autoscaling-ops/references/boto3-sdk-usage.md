# boto3 SDK Usage — Auto Scaling

> **TE-2**: No docstrings. Inline comments only. Minimal examples.
> **TE-6**: Only SDK-specific patterns here. Full op flows in `aws-cli-usage.md`.

## Bootstrap

```python
import boto3, os
client = boto3.client('autoscaling', region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'))
```

## Core Patterns

### Describe ASGs (paginator)
```python
paginator = client.get_paginator('describe_auto_scaling_groups')
for page in paginator.paginate(AutoScalingGroupNames=['{{user.asg_name}}']):
    for asg in page['AutoScalingGroups']:
        print(asg['AutoScalingGroupName'], asg['MinSize'], asg['MaxSize'])
```

### Create ASG
```python
client.create_auto_scaling_group(
    AutoScalingGroupName='{{user.asg_name}}',
    LaunchTemplate={'LaunchTemplateName': '{{user.lt_name}}', 'Version': '{{user.lt_version}}'},
    MinSize={{user.min_size}}, MaxSize={{user.max_size}}, DesiredCapacity={{user.desired_capacity}},
    VPCZoneIdentifier='{{user.subnet_ids}}'
)
```

### Delete ASG (scale-to-0 first)
```python
client.update_auto_scaling_group(AutoScalingGroupName='{{user.asg_name}}', MinSize=0, MaxSize=0, DesiredCapacity=0)
client.get_waiter('group_not_exists').wait(AutoScalingGroupNames=['{{user.asg_name}}'])
# Or: client.delete_auto_scaling_group(AutoScalingGroupName='{{user.asg_name}}', ForceDelete=True)
```

### Scaling Policy
```python
# Target tracking
client.put_scaling_policy(
    AutoScalingGroupName='{{user.asg_name}}', PolicyName='{{user.policy_name}}',
    PolicyType='TargetTrackingScaling',
    TargetTrackingConfiguration={'TargetValue': 50.0, 'PredefinedMetricSpecification': {'PredefinedMetricType': 'ASGAverageCPUUtilization'}}
)
# Step scaling
client.put_scaling_policy(
    AutoScalingGroupName='{{user.asg_name}}', PolicyName='{{user.policy_name}}',
    PolicyType='StepScaling', AdjustmentType='ChangeInCapacity',
    StepAdjustments=[{'MetricIntervalLowerBound': 0.0, 'ScalingAdjustment': 1}],
    Cooldown=300
)
```

### Instance Refresh
```python
refresh_id = client.start_instance_refresh(
    AutoScalingGroupName='{{user.asg_name}}',
    Preferences={'MinHealthyPercentage': 90, 'InstanceWarmup': 300}
)['InstanceRefreshId']
import time
while True:
    st = client.describe_instance_refreshes(AutoScalingGroupName='{{user.asg_name}}', InstanceRefreshIds=[refresh_id])['InstanceRefreshes'][0]['Status']
    if st in ('Successful', 'Failed', 'Cancelled'): break
    time.sleep(10)
```

### Attach / Detach Instances
```python
client.attach_instances(AutoScalingGroupName='{{user.asg_name}}', InstanceIds=['{{user.instance_id}}'])
client.detach_instances(AutoScalingGroupName='{{user.asg_name}}', InstanceIds=['{{user.instance_id}}'], ShouldDecrementDesiredCapacity=True)
```

### Lifecycle Hook
```python
client.put_lifecycle_hook(
    LifecycleHookName='{{user.lifecycle_hook_name}}', AutoScalingGroupName='{{user.asg_name}}',
    LifecycleTransition='autoscaling:EC2_INSTANCE_LAUNCHING',
    HeartbeatTimeout=300, DefaultResult='CONTINUE'
)
```

### Warm Pool
```python
client.put_warm_pool(AutoScalingGroupName='{{user.asg_name}}', MinSize=0, MaxGroupPreparedCapacity=2, PoolState='Stopped')
```

## Error Map (compact)

```python
from botocore.exceptions import ClientError
error_map = {
    'AlreadyExists': 'HALT — name taken',
    'ValidationError': 'Fix params',
    'ScalingActivityInProgress': 'Wait + retry',
    'ResourceContention': 'Retry with backoff',
    'LimitExceeded': 'HALT — quota',
    'ResourceNotFoundException': 'Resource missing',
    'InternalServiceFailure': 'Retry 3x then HALT',
}
```

## Waiters

| Waiter | Use after |
|--------|-----------|
| `group_in_service` | Instance refresh, attach |
| `group_not_exists` | Delete ASG |