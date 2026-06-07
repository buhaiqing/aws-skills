# AWS CLI Usage — Auto Scaling

## Common JSON Paths (Centralized)

```
# ASG:           .AutoScalingGroups[0].{AutoScalingGroupName,MinSize,MaxSize,DesiredCapacity,Instances[*].{InstanceId,LifecycleState,HealthStatus}}
# Activities:    .Activities[].{ActivityId,Description,Cause,StartTime,EndTime,StatusCode,StatusMessage}
# Policies:      .ScalingPolicies[].{PolicyName,PolicyType,ScalingAdjustment,AdjustmentType,Cooldown}
# Schedule:      .ScheduledUpdateGroupActions[].{ScheduledActionName,Recurrence,MinSize,MaxSize,DesiredCapacity,StartTime}
# Hooks:         .LifecycleHooks[].{LifecycleHookName,LifecycleTransition,HeartbeatTimeout,DefaultResult}
# InstanceRefresh: .InstanceRefresh.{InstanceRefreshId,Status,PercentageComplete,EndTime}
# LaunchConfigs: .LaunchConfigurations[0].{LaunchConfigurationName,ImageId,InstanceType,KeyName,SecurityGroups,UserData,CreatedTime}
# LBs:           .LoadBalancers[].LoadBalancerName
# TGs:           .TargetGroups[].LoadBalancerTargetGroupARN
# Processes:     .Processes[].ProcessName
# Tags:          .Tags[].{Key,Value,ResourceId,PropagateAtLaunch}
# WarmPool:      .WarmPoolConfiguration.{MinSize,MaxGroupPreparedCapacity,PoolState}
```

## Command Map

| Goal | CLI Command |
|------|-------------|
| Create ASG | `aws autoscaling create-auto-scaling-group` |
| Describe ASG | `aws autoscaling describe-auto-scaling-groups` |
| Update ASG | `aws autoscaling update-auto-scaling-group` |
| Delete ASG | `aws autoscaling delete-auto-scaling-group` |
| List ASGs | `aws autoscaling describe-auto-scaling-groups` |
| Create Scaling Policy | `aws autoscaling put-scaling-policy` |
| Describe Scaling Policies | `aws autoscaling describe-policies` |
| Delete Scaling Policy | `aws autoscaling delete-policy` |
| Create Scheduled Action | `aws autoscaling put-scheduled-update-group-action` |
| Describe Scheduled Actions | `aws autoscaling describe-scheduled-actions` |
| Delete Scheduled Action | `aws autoscaling delete-scheduled-action` |
| Create Lifecycle Hook | `aws autoscaling put-lifecycle-hook` |
| Describe Lifecycle Hooks | `aws autoscaling describe-lifecycle-hooks` |
| Delete Lifecycle Hook | `aws autoscaling delete-lifecycle-hook` |
| Create Launch Config | `aws autoscaling create-launch-configuration` |
| Describe Launch Configs | `aws autoscaling describe-launch-configurations` |
| Delete Launch Config | `aws autoscaling delete-launch-configuration` |
| Attach Instances | `aws autoscaling attach-instances` |
| Detach Instances | `aws autoscaling detach-instances` |
| Attach LB | `aws autoscaling attach-load-balancers` |
| Detach LB | `aws autoscaling detach-load-balancers` |
| Attach TG | `aws autoscaling attach-load-balancer-target-groups` |
| Detach TG | `aws autoscaling detach-load-balancer-target-groups` |
| Start Instance Refresh | `aws autoscaling start-instance-refresh` |
| Describe Instance Refresh | `aws autoscaling describe-instance-refreshes` |
| Cancel Instance Refresh | `aws autoscaling cancel-instance-refresh` |
| Suspend Processes | `aws autoscaling suspend-processes` |
| Resume Processes | `aws autoscaling resume-processes` |
| Set Desired Capacity | `aws autoscaling set-desired-capacity` |
| Describe Activities | `aws autoscaling describe-scaling-activities` |
| Describe Tags | `aws autoscaling describe-tags` |
| Create or Update Tags | `aws autoscaling create-or-update-tags` |
| Delete Tags | `aws autoscaling delete-tags` |
| Describe Warm Pool | `aws autoscaling describe-warm-pool` |
| Put Warm Pool | `aws autoscaling put-warm-pool` |
| Delete Warm Pool | `aws autoscaling delete-warm-pool` |

## Key CLI Conventions

### Output Format
Always use `--output json` for agent parsing.

### Region
Pass `--region` or rely on `AWS_DEFAULT_REGION`.

### Pagination
CLI auto-paginates. For explicit control:
```bash
aws autoscaling describe-auto-scaling-groups --next-token TOKEN --max-items N
```

## Common Patterns

### Create Auto Scaling Group (Full Example)
```bash
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name "my-asg" \
  --launch-template "LaunchTemplateName=my-lt,Version=\$Default" \
  --min-size 1 \
  --max-size 5 \
  --desired-capacity 2 \
  --vpc-zone-identifier "subnet-abc12345,subnet-def67890" \
  --health-check-type ELB \
  --health-check-grace-period 300 \
  --default-cooldown 300 \
  --tags "[{\"Key\":\"Name\",\"Value\":\"my-asg-instance\",\"PropagateAtLaunch\":true},{\"Key\":\"Environment\",\"Value\":\"production\",\"PropagateAtLaunch\":true}]" \
  --region us-east-1 \
  --output json
```

### Describe Auto Scaling Group
```bash
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names "my-asg" \
  --region us-east-1 \
  --output json \
  | jq '.AutoScalingGroups[0] | {AutoScalingGroupName, MinSize, MaxSize, DesiredCapacity, InstancesCount: [.Instances[] | length]}'
```

### List All ASGs with Instance Count
```bash
aws autoscaling describe-auto-scaling-groups \
  --region us-east-1 \
  --output json \
  | jq '.AutoScalingGroups[] | {Name: .AutoScalingGroupName, Min: .MinSize, Max: .MaxSize, Desired: .DesiredCapacity, Instances: [.Instances[] | {Id: .InstanceId, State: .LifecycleState, Health: .HealthStatus}]}'
```

### Scale Out (Increase Desired Capacity)
```bash
aws autoscaling set-desired-capacity \
  --auto-scaling-group-name "my-asg" \
  --desired-capacity 4 \
  --honor-cooldown \
  --region us-east-1 \
  --output json
```

### Create Target Tracking Policy (CPU Utilization)
```bash
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name "my-asg" \
  --policy-name "cpu-target-50" \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{"TargetValue": 50.0, "PredefinedMetricSpecification": {"PredefinedMetricType": "ASGAverageCPUUtilization"}}' \
  --region us-east-1 \
  --output json
```

### Create Lifecycle Hook
```bash
aws autoscaling put-lifecycle-hook \
  --lifecycle-hook-name "my-hook" \
  --auto-scaling-group-name "my-asg" \
  --lifecycle-transition "autoscaling:EC2_INSTANCE_LAUNCHING" \
  --heartbeat-timeout 300 \
  --default-result "CONTINUE" \
  --region us-east-1 \
  --output json
```

### Delete Auto Scaling Group (force delete)
```bash
aws autoscaling delete-auto-scaling-group \
  --auto-scaling-group-name "my-asg" \
  --force-delete \
  --region us-east-1 \
  --output json
```

### Suspend Health Check Process
```bash
aws autoscaling suspend-processes \
  --auto-scaling-group-name "my-asg" \
  --scaling-processes "HealthCheck" "ReplaceUnhealthy" \
  --region us-east-1 \
  --output json
```

### Query by Tag
```bash
aws autoscaling describe-auto-scaling-groups \
  --region us-east-1 \
  --output json \
  | jq '.AutoScalingGroups[] | select(.Tags[] | select(.Key=="Environment" and .Value=="production")) | .AutoScalingGroupName'
```

## Retry Strategy

| Error Code | Retry? | Max Retries |
|------------|--------|-------------|
| 400 (InvalidParameter) | No | 0 |
| 403 (AccessDenied) | No | 0 |
| 404 (NotFound) | No | 0 |
| 429 (Throttling) | Yes | 3 with exponential backoff |
| 500 (InternalError) | Yes | 3 with exponential backoff |
| 503 (ServiceUnavailable) | Yes | 3 |
| ScalingActivityInProgress | Yes | Wait + retry