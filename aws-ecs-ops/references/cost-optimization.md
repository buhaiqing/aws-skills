# ECS Cost Optimization

> Reference for `aws-ecs-ops`. Fargate is billed by the second; right-sizing, Fargate Spot, and tag governance are the three biggest levers.
> Audience: Platform engineers / FinOps / SRE.

## Fargate Spot

- Mix on-demand FARGATE with FARGATE_SPOT via Capacity Provider Strategy; weight 20 / 80 = 20% baseline on-demand + 80% spot burst.
- Operation: `aws-ecs-ops` SKILL.md → `Operation: Update Capacity Providers` (requires `{{user.opt_in_spot}} = Y`).
- Spot interruption becomes an AIOps signal source (`task.stoppedReason == "SpotInterruption"`) — handle via `references/deployment-health.md` and future cruise inference rule `ECS-SPOT-01` (deferred).
- Read-back: `aws ecs describe-clusters --clusters <arn> --query "clusters[0].capacityProviders"`.

## Compute Optimizer

- API: `aws compute-optimizer get-ecs-service-recommendations --service-arn <arn> --output json`.
- Use case: Fargate CPU / memory right-sizing recommendations on a per-service basis.
- **Rate-limit: 1 call / day max** (Compute Optimizer refreshes once daily; more frequent calls waste API quota).
- When recommendation differs from current: edit task definition (`aws-ecs-ops` `Operation: Register Task Definition`) and roll forward with `update-service --force-new-deployment`.

## Savings Plans

- API: `aws savingsplans describe-savings-plans-coverage --time-period Start=YYYY-MM-DD,End=YYYY-MM-DD --granularity DAILY` (or `aws ce get-savings-plans-coverage`).
- Coverage: Fargate eligible for Compute Savings Plans; expected ~25% discount.
- This skill **does not purchase** SP / RI; refer to `aws-finops-core` or finance-controlled workflow.

## Idle Service Discovery

- List candidates: `aws ecs list-services --cluster <name> --query "serviceArns[]"`.
- Drill down: `aws ecs describe-services --cluster <name> --services <arn> --query "services[].{name:serviceName,desired:desiredCount,running:runningCount}"`.
- Idle rule: `desiredCount == 0 && runningCount == 0` and no in-flight `deployments[]` → candidate for `delete-service --force` (subject to confirmation gate in `aws-ecs-ops` `Operation: Delete Service`).
- Variant (low utilization, not yet idle): `aws cloudwatch get-metric-statistics --namespace AWS/ECS --metric-name CPUUtilization --start-time ... --end-time ... --period 86400 --statistics Average` 7-day mean < 5% → review.

## VPC Endpoint (NAT Cost Reduction)

- Pain point: Fargate tasks pulling ECR images via NAT Gateway can cost hundreds of USD per month on a busy service.
- Fix: `aws ec2 create-vpc-endpoint --vpc-id <vpc> --service-name com.amazonaws.<region>.ecr.dkr --route-table-ids <rtb> --output json` (Gateway Endpoint, free).
- Mirror for `logs.<region>.amazonaws.com` (Interface Endpoint) and `s3` (Gateway Endpoint).
- Result: NAT egress for image pulls / CloudWatch Logs writes drops to ~0.

## Tag Governance

- Recommended tags (Cost Allocation / Chargeback critical): `Project`, `Environment`, `CostCenter`, `ManagedBy`.
- Tag injection templates live in `aws-ecs-ops` `Operation: Create Service` / `Register Task Definition` (see SKILL.md).
- Coverage audit: `aws resourcegroupstaggingapi get-resources --resource-type-filters ecs:service ecs:task ecs:cluster --output json`.
- Compliance rule: `covered / total * 100`; alert <80% WARNING, <60% CRITICAL.

## ADR defer

- `aws-application-autoscaling-ops` (TODO: not yet in repo). ECS Service Auto Scaling recipes deferred to next plan — see `docs/superpowers/plans/2026-07-21-aws-ecs-ops-aiops-finops.md` §ADR defer for rationale and decision options.
