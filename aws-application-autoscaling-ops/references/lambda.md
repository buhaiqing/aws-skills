# Lambda — Application Auto Scaling

> ServiceNamespace `lambda` 的 reference 文档,配合主 [SKILL.md](../../SKILL.md) 使用。

## ServiceNamespace × ScalableDimension

| ServiceNamespace | ScalableDimension | 用途 |
|------------------|-------------------|------|
| `lambda`         | `lambda:function:ProvisionedConcurrency` | 控制 Lambda Provisioned Concurrency (不同于 Reserved Concurrency) |

## resource_id 格式

```
function/<function-name>[:<qualifier>]   # qualifier 可选(版本或 alias)
```

例:`function/my-service:$LATEST` / `function/my-service:prod`

## 常用 CLI

```bash
# 注册 scalable target (Provisioned concurrency p50 默认)
aws application-autoscaling register-scalable-target \
  --service-namespace lambda \
  --resource-id "function/my-function" \
  --scalable-dimension lambda:function:ProvisionedConcurrency \
  --min-capacity 1 --max-capacity 100 \
  --region "{{env.AWS_DEFAULT_REGION}}" --output json

# Target tracking p50 (utilization)
aws application-autoscaling put-scaling-policy \
  --service-namespace lambda \
  --resource-id "function/my-function" \
  --scalable-dimension lambda:function:ProvisionedConcurrency \
  --policy-name "concurrency-target-50" \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{"TargetValue":50,"PredefinedMetricSpecification":{"PredefinedMetricType":"LambdaProvisionedConcurrencyUtilization"},"ScaleOutCooldown":60,"ScaleInCooldown":300}' \
  --region "{{env.AWS_DEFAULT_REGION}}" --output json

# Quota 检查 (verify via API, 不硬编码)
aws service-quotas get-service-quota \
  --service-code lambda \
  --quota-code L-9FDBE1FE \
  --region "{{env.AWS_DEFAULT_REGION}}" --output json
```

## boto3 模板

```python
import boto3
client = boto3.client('application-autoscaling', region_name='{{env.AWS_DEFAULT_REGION}}')
client.register_scalable_target(
  serviceNamespace='lambda',
  resourceId='function/my-function',
  scalableDimension='lambda:function:ProvisionedConcurrency',
  minCapacity=1, maxCapacity=100)
client.put_scaling_policy(
  serviceNamespace='lambda', resourceId='function/my-function',
  scalableDimension='lambda:function:ProvisionedConcurrency',
  policyName='concurrency-target-50', policyType='TargetTrackingScaling',
  targetTrackingScalingPolicyConfiguration={
    'TargetValue': 50,
    'PredefinedMetricSpecification': {'PredefinedMetricType': 'LambdaProvisionedConcurrencyUtilization'},
    'ScaleOutCooldown': 60, 'ScaleInCooldown': 300})
```

## 与 Reserved Concurrency 的关系

- **Reserved Concurrency**:函数最大并发数(硬上限,无 scaling)
- **Provisioned Concurrency**:预热并发数(可 Auto Scaling,按需扩容)
- Application Auto Scaling **只作用于** Provisioned Concurrency,不可作用于 Reserved
- 设置 `min_capacity > 0` 会**立即预热容量**(billing 立即开始)

## Quota & Limits

> API 验证(不硬编码):
> `aws service-quotas list-service-quotas --service-code lambda --region {{env.AWS_DEFAULT_REGION}} --output json`

常见 cap:
- 每个 function 的 Provisioned Concurrency:账户级别 quota(默认低,需提单)
- 每个 Region 的 scalable targets:同 Application Auto Scaling namespace 限制(`L-7B6389E7`)
