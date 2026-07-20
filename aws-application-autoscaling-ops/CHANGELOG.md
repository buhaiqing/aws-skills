# Changelog — aws-application-autoscaling-ops

All notable changes to `aws-application-autoscaling-ops`.

## [1.1.0] - 2026-07-21

### Added (ServiceNamespace expansion)
- `references/lambda.md` — Lambda Provisioned Concurrency (`lambda:function:ProvisionedConcurrency`)
- `references/dynamodb.md` — DynamoDB Table / GSI (4 ScalableDimensions: ReadCapacityUnits / WriteCapacityUnits × table / index)
- `references/spot-fleet.md` — Spot Fleet (`ec2:spot-fleet-request:TargetCapacity`)
- `references/core-concepts.md` ServiceNamespace × ScalableDimension 表 +6 行;移除 3 处 stub `<!-- TODO -->` 注释

### Added (AIOps detection)
- 4 inference rules appended to `aws-aiops-cruise/references/inference-rules.md` § Application Auto Scaling:
  - `PD-AUTOSCALING-01`: ECS `runningCount == MaxCapacity` 无 headroom
  - `CO-AUTOSCALING-01`: ECS `MinCapacity == MaxCapacity` 0 headroom
  - `CO-AUTOSCALING-02`: TargetTracking `ScaleInCooldown > 600s`
  - `FD-AUTOSCALING-01`: ECS service 任务 deficit + active policy 不 firing

### Added (AIOps runbook)
- `RB-AUTOSCALING-01` added to `aws-aiops-orchestrator/references/runbook-recipes.md` § 28 — capacity right-size 决策路径 (AI_ASSIST, 8 steps, PT15M)

### Changed
- Frontmatter `version: "1.0.0" → "1.1.0"`;新增 3 行 Reference Files 段

## [1.0.0] - 2026-07-21

Initial L1 skill. ECS-only MVP (`ecs:service:DesiredCount`). 5 operations (Register / Deregister Scalable Target, Put / Delete Scaling Policy, Tag Resource) + GCL required safety gates.
