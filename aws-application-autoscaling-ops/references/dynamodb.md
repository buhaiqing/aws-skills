# DynamoDB — Application Auto Scaling

> ServiceNamespace `dynamodb` 的 reference 文档,配合主 [SKILL.md](../../SKILL.md) 使用。
> **重点**:与 `aws-dynamodb-ops/SKILL.md` line 716 inline `register-scalable-target` 是同一 API,通过本 skill 提供完整 delegate 路径。

## ServiceNamespace × ScalableDimension

| ServiceNamespace | ScalableDimension | 用途 |
|------------------|-------------------|------|
| `dynamodb`       | `dynamodb:table:ReadCapacityUnits`  | Table-level read capacity |
| `dynamodb`       | `dynamodb:table:WriteCapacityUnits` | Table-level write capacity |
| `dynamodb`       | `dynamodb:index:ReadCapacityUnits`  | GSI/LSI read capacity |
| `dynamodb`       | `dynamodb:index:WriteCapacityUnits` | GSI/LSI write capacity |

## resource_id 格式

```
table/<table-name>
index/<table-name>/<index-name>
```

例:`table/MyTable` / `index/MyTable/MyGSI`

## 常用 CLI — Target tracking (recommended)

```bash
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id "table/MyTable" \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --min-capacity 5 --max-capacity 100 \
  --region "{{env.AWS_DEFAULT_REGION}}" --output json

aws application-autoscaling put-scaling-policy \
  --service-namespace dynamodb \
  --resource-id "table/MyTable" \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --policy-name "scaling-on-util" \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{"TargetValue":70,"PredefinedMetricSpecification":{"PredefinedMetricType":"DynamoDBReadCapacityUtilization"},"ScaleOutCooldown":60,"ScaleInCooldown":300}' \
  --region "{{env.AWS_DEFAULT_REGION}}" --output json
```

## boto3 — GSI read capacity scaling

```python
import boto3
client = boto3.client('application-autoscaling', region_name='{{env.AWS_DEFAULT_REGION}}')
client.register_scalable_target(
  serviceNamespace='dynamodb',
  resourceId='index/MyTable/MyGSI',
  scalableDimension='dynamodb:index:ReadCapacityUnits',
  minCapacity=5, maxCapacity=100)
client.put_scaling_policy(
  serviceNamespace='dynamodb', resourceId='index/MyTable/MyGSI',
  scalableDimension='dynamodb:index:ReadCapacityUnits',
  policyName='gsi-scaling-70', policyType='TargetTrackingScaling',
  targetTrackingScalingPolicyConfiguration={
    'TargetValue': 70,
    'PredefinedMetricSpecification': {'PredefinedMetricType': 'DynamoDBReadCapacityUtilization'}})
```

## On-demand vs Provisioned 模式

- **On-demand (PAY_PER_REQUEST)**:Application Auto Scaling 不适用;需调 `update-table` 切到 PROVISIONED 模式才有 Auto Scaling
- **Provisioned**:`min/max_capacity` 直接映射 RCU/WCU;无 base 概念
- 切换 on-demand ↔ provisioned:policy 自动 deregister,target remains

## Quota & 注意事项

> API:`aws service-quotas list-service-quotas --service-code dynamodb --region {{env.AWS_DEFAULT_REGION}} --output json`

- Table-level Read/Write Capacity 单 max 40000 (default);账户级别按需提单
- 每个 table / GSI 最大 5 个 active scaling policy
- Auto Scaling **仅适用于 PROVISIONED 模式**;切换到 PAY_PER_REQUEST 后所有 policy 自动 deregister
