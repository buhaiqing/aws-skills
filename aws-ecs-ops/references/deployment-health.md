# ECS Deployment Health

> Reference for `aws-ecs-ops`. Detection / diagnosis / alarms around service deployments.
> Audience: Platform / SRE / DevOps.
> Shares metric signals with `aws-aiops-cruise` but does NOT duplicate inference rules (see spec §3 D4).

## Deployment Circuit Breaker

- Enable via `aws ecs create-service ... --deployment-configuration "deploymentCircuitBreaker={enable=true,rollback=true}"` (or `update-service`).
- Three states: `DISABLED` / `ENABLED` (fail-only, no rollback) / `ENABLED+ROLLBACK` (auto rollback on failure).
- Recommended for Fargate: `minimumHealthyPercent=100`, `maximumPercent=200`.

## rolloutState Diagnostics

- State machine: `IN_PROGRESS` → `COMPLETED` or `FAILED`.
- Command: `aws ecs describe-services --cluster <c> --services <s> --query "services[0].deployments[].{status:status,rolloutState:rolloutState,taskDef:taskDefinition,failedTasks:failedTasks,createdAt:createdAt}"`.
- On `FAILED`: read `services[0].events[]` — message starts with `Service deployment failed: <reason>` (image pull, OOM, health-check timeout, etc.).
- Recovery flow:
  1. Read `events[].message` to identify root cause.
  2. Fix task definition / image.
  3. Trigger `aws ecs update-service --force-new-deployment` (CLI in [references/aws-cli-usage.md](aws-cli-usage.md)).
  4. Wait: `aws ecs wait services-stable --cluster <c> --services <s>`.

## Deployment Alarms

- Metric: `DeploymentRolloutAlarm` (namespace `AWS/ECS`, dimensions `ServiceName` + `ClusterName`).
- Trigger: deployment timeout or failure → ALARM.
- Create: `aws cloudwatch put-metric-alarm --alarm-name <name> --metric-name DeploymentRolloutAlarm --namespace AWS/ECS --statistic Maximum --period 60 --evaluation-periods 5 --threshold 0 --comparison-operator GreaterThanThreshold --dimensions Name=ServiceName,Value=<svc> Name=ClusterName,Value=<cluster> --alarm-actions <sns-arn> --output json`.
- AIOps path: alarm → EventBridge → `aws-aiops-cruise` runbook `RB-DEPLOY-01` (to be registered in follow-up work).
