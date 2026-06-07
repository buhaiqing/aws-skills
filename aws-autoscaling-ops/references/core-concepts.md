# Core Concepts — EC2 Auto Scaling

## What is EC2 Auto Scaling

- **Purpose**: Automatically maintain target capacity of EC2 instances across AZs, with health check replacement and scaling policies
- **Category**: Compute (Management)
- **AWS Console URL**: https://console.aws.amazon.com/ec2autoscaling/
- **Official Docs**: https://docs.aws.amazon.com/autoscaling/ec2/userguide/

## Primary Resources

| Resource | Description | Parent Scope |
|----------|-------------|-------------|
| Auto Scaling Group (ASG) | Core resource: manages EC2 instance count per AZ | Region / VPC |
| Launch Template | Instance provisioning template (EC2) | Region |
| Launch Configuration | Legacy instance configuration (replaced by LT) | Region |
| Scaling Policy | Rule for scaling out/in based on metrics | ASG |
| Scheduled Action | Time-based capacity change | ASG |
| Lifecycle Hook | Pause instance launch/terminate for custom actions | ASG |
| Instance Refresh | Rolling instance replacement with new LT/LC | ASG |
| Warm Pool | Pre-initialized instances for faster scale-out | ASG |

## Architecture & Limits

### Region & AZ
- Regional service; ASGs span multiple AZs in one region
- AZ rebalancing: Auto Scaling distributes instances evenly

### Quotas (Service Limits)
| Quota Name | Default | Adjustable? |
|------------|---------|-------------|
| Auto Scaling groups per region | 200 | Yes |
| Launch configurations per region | 200 | Yes |
| Scaling policies per ASG | 50 | No |
| Scheduled actions per ASG | 125 | No |
| Lifecycle hooks per ASG | 50 | No |
| SNS topics per ASG | 10 | No |
| Classic LBs per ASG | 10 | No |
| Target groups per ASG | 50 | No |
| Tags per ASG | 50 | No |
| Instances per ASG | varies (default 500) | Yes |

### Limits
- Max instance warmup: 3,600 seconds
- Max cooldown: 3,600 seconds
- Max heartbeat timeout (lifecycle hook): 4,800 seconds (2h with custom notification)
- Instance refresh max healthy percentage: 100%, min: 0%
- MinHealthyPercentage for instance refresh: default 90%

## Scaling Process Types

| Process | Description | Impact if Suspended |
|---------|-------------|---------------------|
| **Launch** | Add instances to meet desired capacity | New instances not launched |
| **Terminate** | Remove instances exceeding desired capacity | Extra instances remain running |
| **HealthCheck** | Replace unhealthy instances | Unhealthy instances NOT replaced |
| **ReplaceUnhealthy** | Replace unhealthy instances (separate from HealthCheck) | Unhealthy instances remain |
| **AZRebalance** | Rebalance across AZs after capacity change | AZ imbalance persists |
| **AlarmNotification** | Respond to CloudWatch alarms | Alarm-driven scaling disabled |
| **ScheduledActions** | Execute scheduled scaling actions | Scheduled actions skipped |
| **AddToLoadBalancer** | Register new instances with LB/TG | New instances not registered |

## Resource Lifecycle

### ASG Lifecycle
| State | Description | Allowed Operations |
|-------|-------------|-------------------|
| Active | Healthy and operational | All operations |
| Deleting | Deletion in progress | None |
| Deleted | Terminal state | N/A |

### Instance Lifecycle within ASG
| State | Description |
|-------|-------------|
| Pending | Launching; before warmup completes |
| Pending:Wait | Lifecycle hook paused (launch) |
| Pending:Proceed | Lifecycle hook resumed (launch) |
| Quarantined | Health check failed; under investigation |
| InService | Healthy and serving traffic |
| Terminating | Being terminated |
| Terminating:Wait | Lifecycle hook paused (terminate) |
| Terminating:Proceed | Lifecycle hook resumed (terminate) |
| Terminated | Removed from ASG |
| Detaching | Being detached from ASG |
| Detached | Removed from ASG (independent instance) |
| Standby | InService → Standby (health check temporarily disabled) |

## Dependencies

| Dependency | Required? | Created By |
|------------|-----------|------------|
| Launch Template | Yes (or legacy LC) | `aws-ec2-ops` |
| AMI | Yes (via LT/LC) | `aws-ec2-ops` |
| Subnets (≥ 1) | Yes | `aws-vpc-ops` |
| Security Groups | Yes (via LT/LC) | `aws-vpc-ops` |
| IAM Role | Instance profile (optional) | `aws-iam-ops` |
| Load Balancer / TG | For ELB health checks | `aws-elb-ops` |
| CloudWatch Alarm | For step/simple policies | `aws-cloudwatch-ops` |

## Delegation Rules

1. Launch Template must exist before creating ASG → delegate to `aws-ec2-ops`
2. Subnets must exist in the target VPC → delegate to `aws-vpc-ops`
3. Load Balancer / Target Group for ELB health checks → delegate to `aws-elb-ops`
4. CloudWatch Alarm for metric-based step policies → delegate to `aws-cloudwatch-ops`
5. IAM instance profile for EC2 instances → delegate to `aws-iam-ops`

## Scaling Policy Types

| Type | Use Case | Cooldown | Pros | Cons |
|------|----------|----------|------|------|
| **Target Tracking** | Maintain metric at target value (e.g., 50% CPU) | ASG cooldown | Simple, AWS-managed, auto-adjusts | No custom metrics without math |
| **Step Scaling** | Scale by step adjustments per metric breach size | Per-policy | Fine-grained control, size-based response | Complex to configure |
| **Simple Scaling** | Single adjustment per alarm breach | Per-policy | Simplest (legacy) | No step tiers; waits for cooldown |
| **Predictive Scaling** | ML-based forecast + scheduled scaling | N/A | Proactive scaling | Requires 24h+ of metric data |

## Instance Refresh

- **Purpose**: Rolling update of ASG instances to new LT version, new LC, or new configuration
- **Warmup**: New instances wait for `InstanceWarmup` before receiving traffic
- **MinHealthyPercentage**: Minimum percentage of instances that must remain healthy

## Warm Pool

- Pre-launched instances in `Stopped` or `Running` state for fast scale-out
- `MaxGroupPreparedCapacity`: max instances in pool (including running ASG instances)
- `MinSize`: minimum pool size

## Pricing Model

- **Cost**: No additional charge for Auto Scaling itself
- **Pay for**: EC2 instances, Elastic Load Balancing, CloudWatch metrics/alarms
- **Estimator**: https://calculator.aws/#/

## Best Practices

### Security
- Use Launch Templates (not Launch Configurations) for IMDSv2, encryption, and newer features
- Attach least-privilege IAM instance profiles
- Encrypt EBS volumes via Launch Template
- Use `--no-associate-public-ip-address` for private subnets

### Availability
- Minimum 2 AZs for production ASGs
- Use ELB health checks for accurate instance health
- Set `HealthCheckGracePeriod` to account for application startup time
- Enable `GroupMetrics` for detailed CloudWatch monitoring

### Cost
- Use MixedInstancesPolicy to diversify instance types and use Spot
- Right-size instances based on ASG metrics (CPU, Network, MEM)
- Use scheduled actions to scale down during off-hours
- Consider Warm Pools for latency-sensitive scale-out

### Operations
- Use `terminate-instances` for zero-downtime deployments (as opposed to rolling ASG delete)
- Keep Launch Templates versioned; use `$Default` for stable, `$Latest` for testing
- Monitor `ScalingActivities` for failure diagnostics
- Use lifecycle hooks for pre-termination cleanup or pre-launch bootstrapping