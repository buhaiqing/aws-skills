# Comprehend — Application Auto Scaling

> ServiceNamespace `comprehend` 的 reference 文档,配合主 [SKILL.md](../../SKILL.md) 使用。
> 主要场景:**custom Comprehend model**(document classifier / entity recognizer)**inference units** 弹性伸缩。

## ServiceNamespace × ScalableDimension

| ServiceNamespace | ScalableDimension | 用途 |
|------------------|-------------------|------|
| `comprehend` | `comprehend:document-classifier:DesiredInferenceUnits` | custom document classifier 推理容量 scaling |

> 另一个可用 dimension:`comprehend:entity-recognizer:DesiredInferenceUnits`(结构相同,本文档不重复)。

## resource_id 格式

```
document-classifier/<arn-suffix>/<endpoint-name>     # ARN 末尾 + endpoint suffix
```

详细 rule:`describe-document-classifier` 返回的 `DocumentClassifierArn` 末尾 `<arn-after-colon>` 部分 + endpoint 名。

## 常用 CLI

```bash
aws application-autoscaling register-scalable-target \
  --service-namespace comprehend \
  --resource-id "document-classifier/<arn-suffix>/<endpoint-name>" \
  --scalable-dimension comprehend:document-classifier:DesiredInferenceUnits \
  --min-capacity 1 --max-capacity 10 \
  --region "{{env.AWS_DEFAULT_REGION}}" --output json

aws application-autoscaling put-scaling-policy \
  --service-namespace comprehend \
  --resource-id "document-classifier/<arn-suffix>/<endpoint-name>" \
  --scalable-dimension comprehend:document-classifier:DesiredInferenceUnits \
  --policy-name "comprehend-throughput-60" \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{"TargetValue":60,"ScaleOutCooldown":60,"ScaleInCooldown":300}' \
  --region "{{env.AWS_DEFAULT_REGION}}" --output json

aws service-quotas get-service-quota \
  --service-code comprehend \
  --quota-code L-7A50B5C7 \
  --region "{{env.AWS_DEFAULT_REGION}}" --output json
```

## boto3 模板

```python
import boto3
client = boto3.client('application-autoscaling', region_name='{{env.AWS_DEFAULT_REGION}}')
client.register_scalable_target(
  serviceNamespace='comprehend',
  resourceId='document-classifier/<arn-suffix>/<endpoint-name>',
  scalableDimension='comprehend:document-classifier:DesiredInferenceUnits',
  minCapacity=1, maxCapacity=10)
client.put_scaling_policy(
  serviceNamespace='comprehend', resourceId='document-classifier/<arn-suffix>/<endpoint-name>',
  scalableDimension='comprehend:document-classifier:DesiredInferenceUnits',
  policyName='comprehend-throughput-60', policyType='TargetTrackingScaling',
  targetTrackingScalingPolicyConfiguration={'TargetValue': 60})
```

## 注意事项

- **Custom model only**:Built-in model 不支持 Auto Scaling(按 API 区分)
- **PredefinedMetricType 不预定义**:必须 `CustomizedMetricSpecification` 或 step scaling on CloudWatch alarm(`AWS/Comprehend` namespace)
- **Inference endpoint 必先存在**:`CreateEndpoint` 后才可 register scalable target;否则 ValidationException
- **Training 阶段不伸缩**:Scaling 只对 endpoint inference capacity 生效

## Quota

> API:`aws service-quotas list-service-quotas --service-code comprehend --region {{env.AWS_DEFAULT_REGION}} --output json`
