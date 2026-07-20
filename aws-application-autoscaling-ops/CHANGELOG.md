# Changelog — aws-application-autoscaling-ops

All notable changes to `aws-application-autoscaling-ops`.

## [1.2.0] - 2026-07-21

### Added (ServiceNamespace expansion)
- `references/emr.md` — EMR InstanceGroup (`elasticmapreduce:instancegroup:InstanceCount`)
- `references/sagemaker.md` — SageMaker endpoint variant (`sagemaker:variant:DesiredInstanceCount`)
- `references/comprehend.md` — Comprehend NLP inference units (`comprehend:document-classifier:DesiredInferenceUnits`)
- `references/keyspace.md` — Keyspace (Cassandra-compatible, `cassandra:table:{Read,Write}CapacityUnits`)
- `references/core-concepts.md` ServiceNamespace 表 +5 行 (EMR + SageMaker + Comprehend + Keyspace × 2)

### Deferred (next plan)
- Per-namespace inference rules in `aws-aiops-cruise` (各 ServiceNamespace 专属 CloudWatch metric namespace 须独立 rule 设计)
- Python handler 实施 (`aws-aiops-cruise/runbooks/scripts/_inference.py` 新 rule detector)
- Schedule actions (Lambda cron / 全 namespace) 完整覆盖

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
