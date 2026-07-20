# Spot Fleet — Application Auto Scaling

> ServiceNamespace `ec2` 的 reference 文档(Spot Fleet 子集),配合主 [SKILL.md](../../SKILL.md) 使用。
> 用途:cost optimization — target tracking on Spot price 自适应 target capacity。

## ServiceNamespace × ScalableDimension

| ServiceNamespace | ScalableDimension | 用途 |
|------------------|-------------------|------|
| `ec2`           | `ec2:spot-fleet-request:TargetCapacity` | Spot Fleet Request target capacity |

## resource_id 格式

```
spot-fleet-request/<request-id>
```

例:`spot-fleet-request/sfr-12345678-aaaa-bbbb-cccc-deadbeef0000`

## 常用 CLI

```bash
aws application-autoscaling register-scalable-target \
  --service-namespace ec2 \
  --resource-id "spot-fleet-request/sfr-xxxxx" \
  --scalable-dimension ec2:spot-fleet-request:TargetCapacity \
  --min-capacity 0 --max-capacity 50 \
  --region "{{env.AWS_DEFAULT_REGION}}" --output json

aws application-autoscaling put-scaling-policy \
  --service-namespace ec2 \
  --resource-id "spot-fleet-request/sfr-xxxxx" \
  --scalable-dimension ec2:spot-fleet-request:TargetCapacity \
  --policy-name "spot-cost-opt" \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{"TargetValue":60,"CustomizedMetricSpecification":{"MetricName":"SpotPrice","Namespace":"AWS/EC2SpotFleetRequest","Statistic":"Average","Dimensions":[{"Name":"FleetRequestId","Value":"sfr-xxxxx"}]}}' \
  --region "{{env.AWS_DEFAULT_REGION}}" --output json
```

## boto3 模板

```python
import boto3
client = boto3.client('application-autoscaling', region_name='{{env.AWS_DEFAULT_REGION}}')
client.register_scalable_target(
  serviceNamespace='ec2',
  resourceId='spot-fleet-request/sfr-xxxxx',
  scalableDimension='ec2:spot-fleet-request:TargetCapacity',
  minCapacity=0, maxCapacity=50)
```

## Spot 限制

- `min_capacity` 可为 0(fleet 可完全缩到 0)
- Application Auto Scaling 不主动管理 Spot 实例 lifecycle(Spot interruption 由 Spot Fleet 自己 retry / rebalance 处理)
- **Cross-region Spot Fleet 不支持**;每 Region 单独 fleet

## 与 `aws-autoscaling-ops`(EC2 ASG) 的区别

| 维度 | `aws-application-autoscaling-ops` | `aws-autoscaling-ops` |
|------|----------------------------------|----------------------|
| Namespace  | `ec2:spot-fleet-request:TargetCapacity` | `aws autoscaling` (ASG) |
| Resource  | Spot Fleet Request              | Auto Scaling Group    |
| 入口         | Application Auto Scaling 单 API surface | EC2 ASG 直接 API |
| Use case  | Spot price optimization         | EC2 fleet stability |

两个 skill **不冲突**,可同时使用,各管各的 fleet 类型。
