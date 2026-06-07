# Troubleshooting — EC2 Auto Scaling

## Common API Error Codes

| Error Code | HTTP | Meaning | Agent Action |
|------------|------|---------|--------------|
| AlreadyExists | 400 | ASG or resource with that name exists | HALT — use different name |
| ValidationError | 400 | Parameter validation failed | Fix args per AWS API docs |
| InvalidParameter | 400 | Invalid parameter value | Check allowed values |
| MissingParameter | 400 | Required field omitted | Add missing parameter |
| AccessDenied | 403 | IAM permission insufficient | HALT; user updates IAM policy |
| ResourceNotFoundException | 404 | Resource does not exist | Verify resource name/ARN |
| LimitExceeded | 400 | Service quota exceeded | HALT; request quota increase |
| ScalingActivityInProgress | 400 | Another scaling activity running | Wait and retry |
| ResourceContention | 400 | Service contention | Retry with exponential backoff |
| ThrottlingException | 429 | Rate limit exceeded | Retry with exponential backoff |
| InternalServiceFailure | 500 | AWS service error | Retry 3x; HALT with correlation ID |
| ServiceUnavailable | 503 | Service temporarily down | Retry 3x; HALT |

## Diagnostic Order

1. **Verify credentials**: `aws sts get-caller-identity`
2. **Verify region**: Check `AWS_DEFAULT_REGION` or pass `--region`
3. **Describe ASG**: `aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names <name>`
4. **Check scaling activities**: `aws autoscaling describe-scaling-activities --auto-scaling-group-name <name>`
5. **Check instance health**: `aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names <name> | jq '.AutoScalingGroups[0].Instances[]'`
6. **Check CloudWatch metrics**: Relevant ASG metrics for scaling policy evaluation
7. **Check CloudTrail**: Audit trail for configuration changes

## Credential Issues

| Symptom | Diagnosis | Resolution |
|---------|-----------|------------|
| "Unable to locate credentials" | No credentials configured | Configure via env vars or ~/.aws/ |
| "AccessDenied" | Missing IAM permission | Add `autoscaling:*` or specific action to policy |
| "Token refresh required" | SSO session expired | Run `aws sso login` |
| "SignatureDoesNotMatch" | Wrong secret key or clock skew | Verify credentials; sync clock |

## Resource State Issues

| State | Problem | Resolution |
|-------|---------|------------|
| ASG has 0 instances despite desired > 0 | Launch Template misconfigured | Check LT: AMI, subnet, SG; check ScalingActivities for error |
| Instances stuck in Pending | Lifecycle hook timeout | Complete hook action or set DefaultResult = CONTINUE |
| Instances constantly terminated | Health check failing | Check instance health via EC2; verify app is responding |
| "Instance failed to join LB" | TG health check failing | Check TG health check settings, instance security groups |
| ASG stuck in deleting | Scaling activity in progress | Describe activities; wait or cancel |
| Instance refresh failing | MinHealthyPercentage too high | Lower MinHealthyPercentage; check new LT validity |

## Scaling Issues

| Symptom | Possible Cause | Resolution |
|---------|----------------|------------|
| ASG does not scale out | Process(es) suspended | Check `DescribeAutoScalingGroups` → `SuspendedProcesses`; resume |
| ASG does not scale in | Cooldown too long | Reduce DefaultCooldown or per-policy cooldown |
| Target tracking over-scales | TargetValue too low | Increase TargetValue |
| Scaling policy never fires | CloudWatch alarm not in ALARM state | Check alarm metric, threshold, evaluation periods |
| Predictive scaling not working | Insufficient historical data | Wait 24h+ after ASG creation; check metric data |
| Scheduled action didn't fire | Timezone or cron expression wrong | Verify recurrence in UTC; use crontab.guru |
| ASG exceeds max size | Scheduled action or manual override | Check all scheduled actions; verify no manual set-desired-capacity |

## Launch Issues

| Symptom | Diagnosis | Resolution |
|---------|-----------|------------|
| "Invalid AMI" | AMI not found or wrong region | Verify AMI ID exists in the target region |
| "InstanceType not supported" | Instance type not available in AZ | Use different type or check AZ instance type offerings |
| "VPC/subnet not found" | Subnet IDs invalid | Verify subnets exist and are in the same VPC |
| "KeyPair not found" | Key pair does not exist | Create key pair via `aws-ec2-ops` |
| Insufficient capacity | AWS capacity shortage | Retry later; use different instance type or AZ |
| Launch Template version error | Version $Default/$Latest not set | Set DefaultVersionNumber on LT |

## Performance Issues

| Symptom | Possible Cause | Resolution |
|---------|----------------|------------|
| Slow instance launch | Large AMI or user data script | Optimize AMI size; use smaller user data |
| Slow health check transition | Long application startup | Increase HealthCheckGracePeriod |
| Too many scaling activities | Aggressive step adjustments | Increase cooldown; use TargetTracking instead |
| API throttling | High request rate | Use pagination; batch operations; reduce concurrent calls |

## Dependency Issues

| Error | Missing Dependency | Resolution |
|-------|-------------------|------------|
| "LoadBalancer not found" | LB name/ARN invalid | Verify LB exists in correct region |
| "TargetGroup not found" | TG ARN invalid | Verify TG exists; delegate to `aws-elb-ops` |
| "Invalid IAM role" | Instance profile role ARN invalid | Create instance profile via `aws-iam-ops` |
| "Lifecycle hook notification issue" | SNS topic/Role misconfigured | Verify SNS topic and notification role |

## CloudWatch Logs Integration

### Check recent scaling activities
```bash
aws autoscaling describe-scaling-activities \
  --auto-scaling-group-name "my-asg" \
  --max-items 20 \
  --region us-east-1 \
  --output json \
  | jq '.Activities[] | {ActivityId, Description, Cause, StartTime, EndTime, StatusCode, StatusMessage}'
```

### Metric-based troubleshooting
```bash
aws cloudwatch get-metric-data \
  --metric-queries '[{"Id":"asg_cpu","MetricStat":{"Metric":{"Namespace":"AWS/AutoScaling","MetricName":"GroupTotalInstances"},"Period":300,"Stat":"Average"}}]' \
  --start-time $(date -u -d '-1 hour' +%s)000 \
  --end-time $(date -u +%s)000 \
  --region us-east-1 \
  --output json
```

## When to Contact AWS Support

| Scenario | Severity | Action |
|----------|----------|--------|
| Production ASG fails to scale, causing outage | Critical | Immediate support ticket |
| Irreversible scaling loop causing high cost | Critical | Immediate support ticket |
| Instance launch consistently failing (all AZs) | High | Support ticket with scaling activities |
| Unexpected quota limit behavior | Medium | Quota increase request |
| Feature request or clarification | Low | AWS forums or documentation feedback |