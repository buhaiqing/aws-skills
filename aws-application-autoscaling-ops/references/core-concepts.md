# Core Concepts — Application Auto Scaling

## What is Application Auto Scaling

Cross-service scaler namespace for **ECS Service DesiredCount**,
**DynamoDB Table / GSI Capacity**, **Lambda Provisioned Concurrency**,
**Spot Fleet**, **EMR Cluster**, **SageMaker Endpoint**, etc.
Single API surface (`aws application-autoscaling`) replaces per-service
ad-hoc scaling integrations.

## ServiceNamespace × ScalableDimension (ECS MVP)

| ServiceNamespace | ScalableDimension | Status in this skill |
|------------------|-------------------|----------------------|
| `ecs`            | `ecs:service:DesiredCount` | MVP — full coverage |
| `lambda`         | `lambda:function:ProvisionedConcurrency` | v1.1.0 — full coverage |
| `dynamodb`       | `dynamodb:table:ReadCapacityUnits` | v1.1.0 — full coverage |
| `dynamodb`       | `dynamodb:table:WriteCapacityUnits` | v1.1.0 — full coverage |
| `dynamodb`       | `dynamodb:index:ReadCapacityUnits` | v1.1.0 — full coverage |
| `dynamodb`       | `dynamodb:index:WriteCapacityUnits` | v1.1.0 — full coverage |
| `ec2`            | `ec2:spot-fleet-request:TargetCapacity` | v1.1.0 — full coverage |
| `elasticmapreduce` | `elasticmapreduce:instancegroup:InstanceCount` | v1.2.0 — full coverage |
| `sagemaker`         | `sagemaker:variant:DesiredInstanceCount` | v1.2.0 — full coverage |
| `comprehend`       | `comprehend:document-classifier:DesiredInferenceUnits` | v1.2.0 — full coverage |
| `cassandra`        | `cassandra:table:ReadCapacityUnits`  | v1.2.0 — full coverage |
| `cassandra`        | `cassandra:table:WriteCapacityUnits` | v1.2.0 — full coverage |

## Scaling Policy Types

| Type | Use case | Notes |
|------|----------|-------|
| `TargetTrackingScaling` | Most cases (`ECSServiceAverageCPUUtilization` p50) | AWS-managed; adjusts ScaleIn/Out |
| `StepScaling` | Burst / step tiers with CloudWatch alarms | Complex |
| (Scheduled actions) | Predictable peaks | Use cron-style time targets |

## Quotas

> Verify via API; **never hardcode**:
> `aws service-quotas get-service-quota --service-code application-autoscaling --quota-code L-7B6389E7 --region "{{env.AWS_DEFAULT_REGION}}" --output json`

Common caps (verify with API):
- Scalable targets / region: 100 (default)
- Scaling policies / target: 50 (soft)
- Step adjustments / policy: 20

## Integration with `aws-ecs-ops`

ECS Service is registered with capacity via `aws-ecs-ops` (e.g.
`CapacityProvider strategy` + `desiredCount`). Once ECS Service is
`ACTIVE`, this skill manages MinCapacity / MaxCapacity / scaling
policies on top.

## Best Practices

**Targeting**: `TargetValue=50` for typical web services; 70 for batch.
**Cooldowns**: `ScaleOutCooldown=60`, `ScaleInCooldown=300` prevents flapping.
**Tags**: Always attach `Project`/`Environment`/`ManagedBy` for Cost Allocation.
