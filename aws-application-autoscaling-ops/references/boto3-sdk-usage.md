# boto3 SDK Usage — Application Auto Scaling

```python
import boto3
client = boto3.client('application-autoscaling', region_name='{{env.AWS_DEFAULT_REGION}}')

# Register scalable target
client.register_scalable_target(
  serviceNamespace='{{user.service_namespace}}',
  resourceId='{{user.resource_id}}',
  scalableDimension='{{user.scalable_dimension}}',
  minCapacity={{user.min_capacity}},
  maxCapacity={{user.max_capacity}})

# Deregister (idempotent)
client.deregister_scalable_target(
  serviceNamespace='{{user.service_namespace}}',
  resourceId='{{user.resource_id}}',
  scalableDimension='{{user.scalable_dimension}}')

# Put target-tracking scaling policy (canonical AIOps auto-heal recipe)
client.put_scaling_policy(
  serviceNamespace='{{user.service_namespace}}',
  resourceId='{{user.resource_id}}',
  scalableDimension='{{user.scalable_dimension}}',
  policyName='{{user.policy_name}}',
  policyType='TargetTrackingScaling',
  targetTrackingScalingPolicyConfiguration={
    'TargetValue': {{user.target_value|default(50)}},
    'PredefinedMetricSpecification': {'PredefinedMetricType': 'ECSServiceAverageCPUUtilization'},
    'ScaleOutCooldown': {{user.scale_out_cooldown|default(60)}},
    'ScaleInCooldown': {{user.scale_in_cooldown|default(300)}}})

# Delete scaling policy (idempotent)
client.delete_scaling_policy(
  serviceNamespace='{{user.service_namespace}}',
  resourceId='{{user.resource_id}}',
  scalableDimension='{{user.scalable_dimension}}',
  policyName='{{user.policy_name}}')

# Tag (governance + chargeback)
client.tag_resource(
  ResourceARN='{{output.resource_arn}}',
  Tags=[
    {'Key': 'Project', 'Value': '{{user.tag_project}}'},
    {'Key': 'Environment', 'Value': '{{user.tag_environment}}'},
    {'Key': 'ManagedBy', 'Value': 'aiops'}])

# Describe (read-only)
client.describe_scalable_targets(
  serviceNamespace='{{user.service_namespace}}',
  ResourceIds=['{{user.resource_id}}'])

client.describe_scaling_policies(
  serviceNamespace='{{user.service_namespace}}',
  resourceId='{{user.resource_id}}')

# List tags
client.list_tags_for_resource(ResourceARN='{{output.resource_arn}}')
```

> Always set `region_name` explicitly; never rely on ambient `AWS_REGION`
> env var — Application Auto Scaling (cross-service namespace) requires
> explicit region for ARN construction and quota checks.
