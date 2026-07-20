# Changelog

All notable changes to `aws-ecs-ops`.

## [1.2.0] - 2026-07-21

### Changed
- `references/cost-optimization.md` ADR defer stub (line 49) replaced with valid cross-reference to `aws-application-autoscaling-ops` (new L1 skill shipped same day per ADR defer §`docs/superpowers/plans/2026-07-21-aws-ecs-ops-aiops-finops.md`). Compounds the FinOps savings with AIOps auto-heal on `ECSServiceAverageCPUUtilization`.

## [1.1.0] - 2026-07-21

### Added (AIOps)
- Container Insights metric path block at top of `SKILL.md` (Cluster / Container / Service / Task stoppedReason / Deployment rollout)
- New `Operation: Update Capacity Providers` (Fargate / Fargate Spot toggle, `UPDATE_CAPACITY_PROVIDERS` safety confirmation)
- New reference: `references/deployment-health.md` — Deployment Circuit Breaker, `rolloutState` diagnostics, `DeploymentRolloutAlarm`

### Added (FinOps)
- New reference: `references/cost-optimization.md` — Fargate Spot, Compute Optimizer (1 call / day), Savings Plans coverage, Idle Service Discovery, VPC Gateway Endpoint (NAT cost), Tag Governance
- `--tags` template on `Create Service` + `Register Task Definition` (Project / Environment / CostCenter / ManagedBy)
- New CLI in reference: `aws ecs tag-resource` + `update-service --force-new-deployment`

### Added (Cross-skill)
- `aws-finops-core` SKILL.md: 3 new `provides` (ecs-idle-service-discovery / ecs-fargate-rightsizing / ecs-fargate-spot-optimization) + 3 delegate mappings (`ecs-idle` / `ecs-rightsizing` / `ecs-fargate-spot` → `aws-ecs-ops`) + 3 lines in Execution Flow Idle Detection

### Changed
- `references/troubleshooting.md` error table +6 task stoppedReason entries (`SpotInterruption` / `EssentialContainerExited` / `CannotPullContainerError` / `ResourceInitializationFailed` / `OOMKilled` / `TimeoutError`); new H3 `### Deployment circuit breaker tripped`
- Frontmatter `provides` (7 entries); `version` 1.0.0 → 1.1.0; `last_updated` 2026-07-06 → 2026-07-21

### Deferred
- `aws-application-autoscaling-ops` (not yet in repo) — ECS Service Auto Scaling recipes. ADR in `docs/superpowers/plans/2026-07-21-aws-ecs-ops-aiops-finops.md` §ADR defer.

## [1.0.0] - 2026-07-06

Initial release: cluster / service / task definition / task lifecycle CRUD, GCL required, Safety gate for `delete-service` / `delete-cluster`.
