# Core Concepts — EC2 Auto Scaling

## What is EC2 Auto Scaling

Automatically maintain target EC2 capacity across AZs. Includes health-check replacement, scaling policies, scheduled actions, lifecycle hooks, instance refresh, and warm pools.
Console: https://console.aws.amazon.com/ec2autoscaling/ | Docs: https://docs.aws.amazon.com/autoscaling/ec2/userguide/

## Primary Resources

ASG (core) | Launch Template (preferred over LC) | Scaling Policy | Scheduled Action | Lifecycle Hook | Instance Refresh | Warm Pool.

## Architecture & Limits

### Region & AZ
- Regional service; ASGs span multiple AZs in one region
- AZ rebalancing: Auto Scaling distributes instances evenly

### Quotas (Service Limits)

> **TE-1**: Query live limits via API. Defaults: ASGs/region: 200 | Launch configs/region: 200 | Policies/ASG: 50 | Scheduled actions/ASG: 125 | Instances/ASG: 500.
> API: `aws service-quotas list-service-quotas --service-code auto-scaling --region "{{user.region}}" --output json`

### Limits
- Max instance warmup: 3,600 seconds
- Max cooldown: 3,600 seconds
- Max heartbeat timeout (lifecycle hook): 4,800 seconds (2h with custom notification)
- Instance refresh max healthy percentage: 100%, min: 0%
- MinHealthyPercentage for instance refresh: default 90%

## Scaling Process Types

`Launch` | `Terminate` | `HealthCheck` (replace unhealthy) | `ReplaceUnhealthy` | `AZRebalance` | `AlarmNotification` | `ScheduledActions` | `AddToLoadBalancer`. Suspending `HealthCheck`/`ReplaceUnhealthy` blocks automatic replacement — high impact, confirm before suspend.

## Resource Lifecycle

### ASG Lifecycle
Active | Deleting (in progress) | Deleted (terminal).

### Instance Lifecycle
`Pending` → `Pending:Wait` (hook paused) → `Pending:Proceed` → `InService` → `Terminating` → `Terminating:Wait` (hook) → `Terminated`. Also: `Quarantined` (health fail), `Standby` (admin disabled), `Detaching/Detached`.

## Dependencies

Launch Template or Launch Config → `aws-ec2-ops` | Subnets → `aws-vpc-ops` | LB/TG → `aws-elb-ops` | CloudWatch alarms → `aws-cloudwatch-ops` | IAM role → `aws-iam-ops`.

## Scaling Policy Types

| Type | Best for | Notes |
|------|----------|-------|
| Target Tracking | Most cases (e.g., 50% CPU) | AWS-managed, auto-adjusts |
| Step Scaling | Fine-grained, size-based | Complex; needs CloudWatch alarm |
| Simple Scaling | Legacy, simplest | Cooldown waits; no step tiers |
| Predictive Scaling | Proactive, ML-based | Needs 24h+ metric history |

## Instance Refresh

Rolling replacement of ASG instances to new LT/LC. New instances wait for `InstanceWarmup`. Set `MinHealthyPercentage ≥ 90%` for prod. Use `start-instance-refresh`; poll via `describe-instance-refreshes`.

## Warm Pool

Pre-launched instances (`Stopped`/`Running`) for fast scale-out. Configure via `put-warm-pool`. `MaxGroupPreparedCapacity` limits pool + running instances.

## Best Practices

**Security**: Launch Templates (not LC) for IMDSv2 + encryption. Least-privilege IAM. **Availability**: ≥2 AZs, ELB health checks, `HealthCheckGracePeriod` for app startup. **Cost**: MixedInstancesPolicy with Spot. Scheduled scale-down off-hours. **Ops**: Keep LTs versioned; use `$Default` for stable deployments.