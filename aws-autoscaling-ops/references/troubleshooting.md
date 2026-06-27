# Troubleshooting — EC2 Auto Scaling

## Common API Error Codes

| Error Code | HTTP | Agent Action |
|------------|------|-------------|
| AlreadyExists | 400 | HALT — use different name |
| ValidationError | 400 | Fix args per AWS docs |
| InvalidParameter | 400 | Check allowed values |
| MissingParameter | 400 | Add missing parameter |
| AccessDenied | 403 | HALT; add IAM permission |
| ResourceNotFoundException | 404 | Verify resource name/ARN |
| LimitExceeded | 400 | HALT; request quota increase |
| ScalingActivityInProgress | 400 | Wait + retry |
| ResourceContention | 400 | Retry with backoff |
| ThrottlingException | 429 | Retry with backoff |
| InternalServiceFailure | 500 | Retry 3x then HALT |
| ServiceUnavailable | 503 | Retry 3x then HALT |

## Diagnostic Order

1. `aws sts get-caller-identity` — credentials
2. `describe-auto-scaling-groups` — ASG state
3. `describe-scaling-activities` — recent events
4. `describe-auto-scaling-groups | jq '.Instances[]'` — instance health
5. `describe-scaling-activities | jq '.SuspendedProcesses'` — paused processes

## Key Symptom → Resolution

| Symptom | Resolution |
|---------|-----------|
| ASG 0 instances despite desired > 0 | Check LT (AMI, subnet, SG); see `ScalingActivities` |
| Instances stuck Pending | Lifecycle hook timeout → complete hook or set DefaultResult=CONTINUE |
| Instances constantly terminated | Health check failing → verify via EC2 describe |
| "Instance failed to join LB" | TG health check failing → check TG settings + SGs |
| ASG does not scale out | Processes suspended → `describe-auto-scaling-groups.SuspendedProcesses` |
| ASG does not scale in | Cooldown too long → reduce DefaultCooldown |
| Scaling policy never fires | Alarm not in ALARM → check CloudWatch metric/threshold |
| Scheduled action didn't fire | Cron wrong timezone → recurrence must be UTC |
| "Invalid AMI" | AMI not in target region or deleted |
| "InstanceType not supported" | AZ lacks that type → try different type or AZ |
| "VPC/subnet not found" | Subnet not in same VPC |
| "KeyPair not found" | Create key pair via `aws-ec2-ops` |
| "LoadBalancer not found" | LB not in correct region or wrong name |
| "TargetGroup not found" | Verify TG; delegate to `aws-elb-ops` |
| API throttling | Pagination; reduce concurrent calls; backoff |
| Instance refresh failing | MinHealthyPercentage too high → lower it; check LT validity |

## Diagnostic Commands

```bash
# ASG state + instance health
aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names "{{user.asg_name}}" \
  --region "{{user.region}}" --output json

# Recent scaling activities
aws autoscaling describe-scaling-activities --auto-scaling-group-name "{{user.asg_name}}" \
  --max-items 20 --region "{{user.region}}" --output json

# Suspended processes
aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names "{{user.asg_name}}" \
  --region "{{user.region}}" --output json | jq '.[0].SuspendedProcesses'
```
