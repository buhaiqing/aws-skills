# SageMaker — Application Auto Scaling

> ServiceNamespace `sagemaker` 的 reference 文档,配合主 [SKILL.md](../../SKILL.md) 使用。
> 主要场景:**real-time endpoint** instance count scaling(替换 deprecated `sagemaker:endpoint-variant` namespace 路径)。

## ServiceNamespace × ScalableDimension

| ServiceNamespace | ScalableDimension | 用途 |
|------------------|-------------------|------|
| `sagemaker` | `sagemaker:variant:DesiredInstanceCount` | real-time endpoint variant 实例数 scaling |

> 注:`sagemaker:endpoint-variant` (legacy) 已被 `sagemaker:variant` 取代,新代码只用后者。

## resource_id 格式

```
endpoint/<endpoint-config-name>/variant/<variant-name>
```

例:`endpoint/my-endpoint-config/variant/prod-variant`

> **EndpointConfig 与 Endpoint 区别**:`endpoint-config` 是 deployment spec;`endpoint` 是 deployed runtime。resource_id 用 runtime endpoint + variant 路径(2-level 嵌套)。

## 常用 CLI

```bash
aws application-autoscaling register-scalable-target \
  --service-namespace sagemaker \
  --resource-id "endpoint/my-endpoint/variant/prod" \
  --scalable-dimension sagemaker:variant:DesiredInstanceCount \
  --min-capacity 1 --max-capacity 10 \
  --region "{{env.AWS_DEFAULT_REGION}}" --output json

aws application-autoscaling put-scaling-policy \
  --service-namespace sagemaker \
  --resource-id "endpoint/my-endpoint/variant/prod" \
  --scalable-dimension sagemaker:variant:DesiredInstanceCount \
  --policy-name "sagemaker-invocations-60" \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{"TargetValue":60,"PredefinedMetricSpecification":{"PredefinedMetricType":"SageMakerVariantInvocationsPerInstance"},"ScaleOutCooldown":60,"ScaleInCooldown":300}' \
  --region "{{env.AWS_DEFAULT_REGION}}" --output json

aws service-quotas get-service-quota \
  --service-code sagemaker \
  --quota-code L-564E5032 \
  --region "{{env.AWS_DEFAULT_REGION}}" --output json
```

## boto3 模板

```python
import boto3
client = boto3.client('application-autoscaling', region_name='{{env.AWS_DEFAULT_REGION}}')
client.register_scalable_target(
  serviceNamespace='sagemaker',
  resourceId='endpoint/my-endpoint/variant/prod',
  scalableDimension='sagemaker:variant:DesiredInstanceCount',
  minCapacity=1, maxCapacity=10)
client.put_scaling_policy(
  serviceNamespace='sagemaker', resourceId='endpoint/my-endpoint/variant/prod',
  scalableDimension='sagemaker:variant:DesiredInstanceCount',
  policyName='sagemaker-invocations-60', policyType='TargetTrackingScaling',
  targetTrackingScalingPolicyConfiguration={
    'TargetValue': 60,
    'PredefinedMetricSpecification': {'PredefinedMetricType': 'SageMakerVariantInvocationsPerInstance'}})
```

## 注意事项

- **Real-time vs Async inference**:仅 real-time endpoint 支持 variant Auto Scaling;async inference endpoint 用 `InferenceComponent` (separate API)
- **Multi-variant / Multi-endpoint**:每个 variant 单独 register;同 endpoint 下 multi-variant 互不影响
- **Endpoint update vs scale**:Scaling 改变 instance count,不改变 model artifact;deploy 新 model 用 SageMaker EndpointConfig update 路径

## Quota & Limits

> API 验证:`aws service-quotas list-service-quotas --service-code sagemaker --region {{env.AWS_DEFAULT_REGION}} --output json`

- `L-564E5032`:生产变体最大实例数 per endpoint per account(默认 500)
- Auto Scaling cooldown 单位 seconds,默认 300;按 endpoint 业务而定
