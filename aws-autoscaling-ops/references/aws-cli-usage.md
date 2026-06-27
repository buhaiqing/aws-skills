# AWS CLI Usage — Auto Scaling

> **TE-4**: JSON paths centralized in SKILL.md `## Common JSON Paths`. This file is the canonical source for CLI commands.

## Common JSON Paths

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

Always use `--output json` for agent parsing. Pass `--region` or rely on `AWS_DEFAULT_REGION`. For explicit pagination:
```bash
aws autoscaling describe-auto-scaling-groups --next-token TOKEN --max-items N
```

## Common Patterns

### Create ASG
```bash
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name "{{user.asg_name}}" \
  --launch-template "LaunchTemplateName={{user.lt_name}},Version={{user.lt_version}}" \
  --min-size {{user.min_size}} --max-size {{user.max_size}} --desired-capacity {{user.desired_capacity}} \
  --vpc-zone-identifier "{{user.subnet_ids}}" --region "{{user.region}}" --output json
```

### Delete ASG (scale-to-0 first)
```bash
# Scale to 0
aws autoscaling update-auto-scaling-group --auto-scaling-group-name "{{user.asg_name}}" \
  --min-size 0 --max-size 0 --desired-capacity 0 --region "{{user.region}}" --output json
# Wait for instances to terminate, then delete
aws autoscaling delete-auto-scaling-group --auto-scaling-group-name "{{user.asg_name}}" \
  --region "{{user.region}}" --output json
# Or force-delete (all instances immediately)
aws autoscaling delete-auto-scaling-group --auto-scaling-group-name "{{user.asg_name}}" \
  --force-delete --region "{{user.region}}" --output json
```

### Describe ASG
```bash
aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names "{{user.asg_name}}" \
  --region "{{user.region}}" --output json
```

### Scale Out
```bash
aws autoscaling set-desired-capacity --auto-scaling-group-name "{{user.asg_name}}" \
  --desired-capacity {{user.desired_capacity}} --region "{{user.region}}" --output json
```

### Scaling Policy
```bash
# Target tracking
aws autoscaling put-scaling-policy --auto-scaling-group-name "{{user.asg_name}}" \
  --policy-name "{{user.policy_name}}" --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{"TargetValue":50.0,"PredefinedMetricSpecification":{"PredefinedMetricType":"ASGAverageCPUUtilization"}}' \
  --region "{{user.region}}" --output json
# Step scaling
aws autoscaling put-scaling-policy --auto-scaling-group-name "{{user.asg_name}}" \
  --policy-name "{{user.policy_name}}" --policy-type StepScaling \
  --adjustment-type ChangeInCapacity \
  --step-adjustments '[{"MetricIntervalLowerBound":0,"ScalingAdjustment":1},{"MetricIntervalLowerBound":20,"ScalingAdjustment":2}]' \
  --region "{{user.region}}" --output json
```

### Lifecycle Hook
```bash
aws autoscaling put-lifecycle-hook --lifecycle-hook-name "{{user.lifecycle_hook_name}}" \
  --auto-scaling-group-name "{{user.asg_name}}" \
  --lifecycle-transition "autoscaling:EC2_INSTANCE_LAUNCHING" \
  --heartbeat-timeout 300 --default-result CONTINUE --region "{{user.region}}" --output json
```

### Suspend / Resume
```bash
aws autoscaling suspend-processes --auto-scaling-group-name "{{user.asg_name}}" \
  --scaling-processes HealthCheck ReplaceUnhealthy --region "{{user.region}}" --output json
aws autoscaling resume-processes --auto-scaling-group-name "{{user.asg_name}}" \
  --scaling-processes HealthCheck ReplaceUnhealthy --region "{{user.region}}" --output json
```

### Instance Refresh
```bash
aws autoscaling start-instance-refresh --auto-scaling-group-name "{{user.asg_name}}" \
  --preferences '{"MinHealthyPercentage":90,"InstanceWarmup":300}' \
  --region "{{user.region}}" --output json
# Poll
aws autoscaling describe-instance-refreshes --auto-scaling-group-name "{{user.asg_name}}" \
  --region "{{user.region}}" --output json
```

## Error Handling

> See `references/troubleshooting.md` §Common API Error Codes.
> 400/403/404 → no retry | 429/500/503 → backoff 3x | ScalingActivityInProgress → wait + retry.
