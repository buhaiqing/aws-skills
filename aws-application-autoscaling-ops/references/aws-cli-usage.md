# AWS CLI Usage — Application Auto Scaling

> **Pre-condition**: `aws sts get-caller-identity` before any command.

## Common JSON Paths

- ScalableTarget: `.ScalableTargets[].{ServiceNamespace,ResourceId,ScalableDimension,MinCapacity,MaxCapacity,RoleARN,CreationTime}`
- ScalingPolicy: `.ScalingPolicies[].{PolicyName,ServiceNamespace,ResourceId,ScalableDimension,PolicyType,PolicyARN,Alarms[],CreationTime}`
- TagResponse: no body (HTTP 200)
- ListTagsForResource: `.Tags[].{Key,Value}`

## Commands

```bash
# Pre-flight
aws sts get-caller-identity --output json

# Scalable Targets
aws application-autoscaling describe-scalable-targets \
  --service-namespace "{{user.service_namespace}}" \
  --resource-id "{{user.resource_id}}" \
  --output json

aws application-autoscaling register-scalable-target \
  --service-namespace "{{user.service_namespace}}" \
  --resource-id "{{user.resource_id}}" \
  --scalable-dimension "{{user.scalable_dimension}}" \
  --min-capacity {{user.min_capacity}} --max-capacity {{user.max_capacity}} \
  --region "{{env.AWS_DEFAULT_REGION}}" \
  --output json

aws application-autoscaling deregister-scalable-target \
  --service-namespace "{{user.service_namespace}}" \
  --resource-id "{{user.resource_id}}" \
  --scalable-dimension "{{user.scalable_dimension}}" \
  --region "{{env.AWS_DEFAULT_REGION}}" \
  --output json

# Scaling Policies
aws application-autoscaling describe-scaling-policies \
  --service-namespace "{{user.service_namespace}}" \
  --resource-id "{{user.resource_id}}" \
  --output json

aws application-autoscaling put-scaling-policy \
  --service-namespace "{{user.service_namespace}}" \
  --resource-id "{{user.resource_id}}" \
  --scalable-dimension "{{user.scalable_dimension}}" \
  --policy-name "{{user.policy_name}}" \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{"TargetValue":{{user.target_value|default(50)}},"PredefinedMetricSpecification":{"PredefinedMetricType":"ECSServiceAverageCPUUtilization"},"ScaleOutCooldown":{{user.scale_out_cooldown|default(60)}},"ScaleInCooldown":{{user.scale_in_cooldown|default(300)}}}' \
  --region "{{env.AWS_DEFAULT_REGION}}" \
  --output json

aws application-autoscaling delete-scaling-policy \
  --service-namespace "{{user.service_namespace}}" \
  --resource-id "{{user.resource_id}}" \
  --scalable-dimension "{{user.scalable_dimension}}" \
  --policy-name "{{user.policy_name}}" \
  --region "{{env.AWS_DEFAULT_REGION}}" \
  --output json

# Tags
aws application-autoscaling tag-resource \
  --resource-arn "{{output.resource_arn}}" \
  --tags Key=Project,Value={{user.tag_project}} Key=Environment,Value={{user.tag_environment}} Key=ManagedBy,Value=aiops \
  --region "{{env.AWS_DEFAULT_REGION}}" \
  --output json

aws application-autoscaling untag-resource \
  --resource-arn "{{output.resource_arn}}" \
  --tag-keys Project Environment \
  --region "{{env.AWS_DEFAULT_REGION}}" \
  --output json

# Quota check (verification pattern — never hardcode in skill file)
aws service-quotas get-service-quota \
  --service-code application-autoscaling \
  --quota-code L-7B6389E7 \
  --region "{{env.AWS_DEFAULT_REGION}}" \
  --output json
```

## Anti-pattern

- **Never** use `aws --output json application-autoscaling ...` (incorrect placement). Always `aws application-autoscaling <op> --output json`.
- **Never** omit `--region` — Application Auto Scaling is region-scoped.
