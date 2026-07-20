# EMR — Application Auto Scaling

> ServiceNamespace `elasticmapreduce` 的 reference 文档,配合主 [SKILL.md](../../SKILL.md) 使用。

## ServiceNamespace × ScalableDimension

| ServiceNamespace | ScalableDimension | 用途 |
|------------------|-------------------|------|
| `elasticmapreduce` | `elasticmapreduce:instancegroup:InstanceCount` | EMR Cluster InstanceGroup scaling (CORE / TASK) |

## resource_id 格式

```
instancegroup/<cluster-id>/<instance-group-id>
```

例:`instancegroup/j-XXXXXXXXXXXXX/ig-XXXXXXXXXXXXX`(CORE / Master group)

## 常用 CLI

```bash
aws application-autoscaling register-scalable-target \
  --service-namespace elasticmapreduce \
  --resource-id "instancegroup/j-XXXXX/ig-XXXXX" \
  --scalable-dimension elasticmapreduce:instancegroup:InstanceCount \
  --min-capacity 1 --max-capacity 20 \
  --region "{{env.AWS_DEFAULT_REGION}}" --output json

aws application-autoscaling put-scaling-policy \
  --service-namespace elasticmapreduce \
  --resource-id "instancegroup/j-XXXXX/ig-XXXXX" \
  --scalable-dimension elasticmapreduce:instancegroup:InstanceCount \
  --policy-name "emr-cpu-60" \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{"TargetValue":60,"PredefinedMetricSpecification":{"PredefinedMetricType":"EMRClusterCoreCPUUtilization"},"ScaleOutCooldown":300,"ScaleInCooldown":600}' \
  --region "{{env.AWS_DEFAULT_REGION}}" --output json

aws service-quotas get-service-quota \
  --service-code elasticmapreduce \
  --quota-code L-74D8EC28 \
  --region "{{env.AWS_DEFAULT_REGION}}" --output json
```

## boto3 模板

```python
import boto3
client = boto3.client('application-autoscaling', region_name='{{env.AWS_DEFAULT_REGION}}')
client.register_scalable_target(
  serviceNamespace='elasticmapreduce',
  resourceId='instancegroup/j-XXXXX/ig-XXXXX',
  scalableDimension='elasticmapreduce:instancegroup:InstanceCount',
  minCapacity=1, maxCapacity=20)
client.put_scaling_policy(
  serviceNamespace='elasticmapreduce', resourceId='instancegroup/j-XXXXX/ig-XXXXX',
  scalableDimension='elasticmapreduce:instancegroup:InstanceCount',
  policyName='emr-cpu-60', policyType='TargetTrackingScaling',
  targetTrackingScalingPolicyConfiguration={
    'TargetValue': 60,
    'PredefinedMetricSpecification': {'PredefinedMetricType': 'EMRClusterCoreCPUUtilization'},
    'ScaleOutCooldown': 300, 'ScaleInCooldown': 600})
```

## 注意事项

- **CORE vs TASK**:每个 InstanceGroup 可单独 register;Master/CORE group 较少 scale,TASK group scale 多
- **Instance Fleet 不需要 Application Auto Scaling** — Instance Fleet 用 Spot / On-Demand mix strategies,不用 scaling policy
- **Termination protection**:Auto Scaling 缩容时默认保护 CORE / Master group;可通过配置覆盖
- **Bootstrap**:scale-up 后新 instance 走完整 bootstrap(YARN capacity scheduler 才列入 active)

## Quota

> API 验证:`aws service-quotas list-service-quotas --service-code elasticmapreduce --region {{env.AWS_DEFAULT_REGION}} --output json`
