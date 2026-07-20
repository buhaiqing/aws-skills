# Keyspace — Application Auto Scaling

> ServiceNamespace `cassandra` 的 reference 文档(覆盖 Amazon Keyspace,即 Apache Cassandra-compatible),配合主 [SKILL.md](../../SKILL.md) 使用。
> 用途:对 Keyspace table 容量(Cassandra 风格的 read/write capacity units)scaling。

## ServiceNamespace × ScalableDimension

| ServiceNamespace | ScalableDimension | 用途 |
|------------------|-------------------|------|
| `cassandra` | `cassandra:table:ReadCapacityUnits`  | Table-level read capacity |
| `cassandra` | `cassandra:table:WriteCapacityUnits` | Table-level write capacity |

## resource_id 格式

```
keyspace/<keyspace-name>/table/<table-name>
```

例:`keyspace/my_ks/table/UserProfile`

## 常用 CLI

```bash
aws application-autoscaling register-scalable-target \
  --service-namespace cassandra \
  --resource-id "keyspace/my_ks/table/UserProfile" \
  --scalable-dimension cassandra:table:ReadCapacityUnits \
  --min-capacity 5 --max-capacity 100 \
  --region "{{env.AWS_DEFAULT_REGION}}" --output json

aws application-autoscaling put-scaling-policy \
  --service-namespace cassandra \
  --resource-id "keyspace/my_ks/table/UserProfile" \
  --scalable-dimension cassandra:table:ReadCapacityUnits \
  --policy-name "ks-read-70" \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{"TargetValue":70,"ScaleOutCooldown":60,"ScaleInCooldown":300}' \
  --region "{{env.AWS_DEFAULT_REGION}}" --output json

aws service-quotas get-service-quota \
  --service-code cassandra \
  --region "{{env.AWS_DEFAULT_REGION}}" --output json
```

## boto3 模板

```python
import boto3
client = boto3.client('application-autoscaling', region_name='{{env.AWS_DEFAULT_REGION}}')
client.register_scalable_target(
  serviceNamespace='cassandra',
  resourceId='keyspace/my_ks/table/UserProfile',
  scalableDimension='cassandra:table:ReadCapacityUnits',
  minCapacity=5, maxCapacity=100)
client.put_scaling_policy(
  serviceNamespace='cassandra', resourceId='keyspace/my_ks/table/UserProfile',
  scalableDimension='cassandra:table:ReadCapacityUnits',
  policyName='ks-read-70', policyType='TargetTrackingScaling',
  targetTrackingScalingPolicyConfiguration={
    'TargetValue': 70,
    'CustomizedMetricSpecification': {
      'MetricName': 'ConsumedReadCapacityUnits',
      'Namespace': 'AWS/Cassandra',
      'Statistic': 'Average',
      'Dimensions': [{'Name': 'TableName', 'Value': 'UserProfile'}]}})
```

## 注意事项

- **Cassandra-compatible (Apache Cassandra CQL protocol)**:不是 DynamoDB;底层是 Keyspace
- **On-demand vs Provisioned**:On-demand mode 不支持 Auto Scaling,需 `update-table --capacity-mode=provisioned` 先
- **PredefinedMetricType 不预定义**:必须 `CustomizedMetricSpecification` + CloudWatch namespace `AWS/Cassandra`
- **Provisioned 模式 `min-capacity ≥ 1`**:不允许 0(provisioned 必须 ≥ 1 才有 capacity)

## Quota

> API:`aws service-quotas list-service-quotas --service-code cassandra --region {{env.AWS_DEFAULT_REGION}} --output json`
