---
name: aws-ecs-ops
description: >-
  Use when operating AWS ECS (Elastic Container Service) resources via AWS CLI
  or boto3 SDK; user mentions ECS, container service, Fargate, EC2 launch type,
  task definition, service, cluster, or task.
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to AWS endpoints.
metadata:
  author: aws
  version: "1.2.0"
  provides:
    - ecs-cluster-lifecycle
    - ecs-service-lifecycle
    - ecs-task-definition-lifecycle
    - ecs-task-lifecycle
    - ecs-idle-service-discovery
    - ecs-fargate-rightsizing
    - ecs-fargate-spot-optimization
  last_updated: "2026-07-31"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  destructive_ops_require_confirm: true
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_SESSION_TOKEN
    - AWS_DEFAULT_REGION
    - AWS_PROFILE
  gcl:
    enabled: true
    class: required
    max_iter: 2
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: false
  cross_skill_deps:
    - aws-ec2-ops            # EC2 launch type instances
    - aws-iam-ops            # Task roles, execution roles
    - aws-elb-ops            # ALB target groups for services
    - aws-cloudwatch-ops     # Container Insights, service metrics
    - aws-vpc-ops            # VPC/networking for tasks
  orchestrator_aware: true
  orchestrator_compat: ">=0.10"
  delegate:
    accepts: ["health-check", "rca", "capacity-review"]
    produces_facts: ["state", "metric", "event"]
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true
---
# AWS ECS Operations Skill

Use for ECS clusters, task definitions, services, tasks, capacity providers, deployments, networking, scaling, and container health. Detailed commands remain in references.

## Common JSON Paths

Cluster: .clusters[].{clusterArn,clusterName,status,activeServicesCount,runningTasksCount}
Service: .services[].{serviceArn,serviceName,status,desiredCount,runningCount,pendingCount}
Tasks: .tasks[].{taskArn,lastStatus,healthStatus,taskDefinitionArn}
TaskDefinition: .taskDefinition.{taskDefinitionArn,revision,status,containerDefinitions}

## Trigger & Scope

### SHOULD Use When
ECS clusters/services/tasks, task definitions, deployments, scaling, capacity providers, and container health.

### SHOULD NOT Use When
EKS → `aws-eks-ops`; EC2 → `aws-ec2-ops`; ECR images → `aws-ecr-ops`; ELB → `aws-elb-ops`.

## Variable Convention

| Placeholder | Source | Use |
|---|---|---|
| `{{env.AWS_*}}` | Runtime env | Never ask; fail closed if unset |
| `{{user.cluster_name}}`, `{{user.service_name}}`, `{{user.task_definition}}` | User input | ECS identity |
| `{{user.desired_count}}`, `{{user.task_arn}}` | User input | Scale/task operation |
| `{{output.*}}` | API response | Reuse service/task/deployment IDs |

## Execution Flow

Every operation follows **Pre-flight → Execute → Validate → Recover**. Run `aws --version` and `aws sts get-caller-identity --output json`; verify cluster, task definition, image, IAM, subnet/SG, service deployment, desired/running counts, and capacity. Use CLI `--output json`, then boto3 after 3 CLI failures. Poll deployment/task health; recover with bounded retries and halt on inactive services, capacity, or ambiguous task IDs. See [aws-cli-usage.md](references/aws-cli-usage.md), [boto3-sdk-usage.md](references/boto3-sdk-usage.md), and [troubleshooting.md](references/troubleshooting.md).

## Operations and Safety

| Operation | Pre-flight / validation | Confirmation |
|---|---|---|
| Create/update cluster/service | Validate task definition, network, capacity, desired count; read back | Token for production scale/deploy |
| Stop task | Echo task and reason; assess service replacement | `confirm=STOP_TASK {{user.task_arn}}` in production |
| Delete service | Drain/scale to 0 and inspect traffic/dependencies | `confirm=DELETE_SERVICE {{user.service_name}}` |
| Deregister task definition | Verify revisions and live service references | Human confirmation |
| Delete cluster | Verify no services/tasks remain | `confirm=DELETE_CLUSTER {{user.cluster_name}}` |
| Update capacity providers | Diff capacity/fallback impact | Human confirmation |

Mask container environment variables, secrets, image credentials, task payloads, and logs in traces.

## Quality Gate (GCL)

Required GCL, `max_iter=2`, rubric `references/rubric.md`, prompts `references/prompt-templates.md`; persist traces under `./audit-results/`. Apply A7–A10; Safety=0 aborts.

## Token Efficiency

TE-1…TE-6 apply; query live task/capacity state, keep SDK examples comment-only, centralize JSON paths above, use asset anchors, and keep flows single-sourced.

## Reference Files

[aws-cli-usage.md](references/aws-cli-usage.md) · [boto3-sdk-usage.md](references/boto3-sdk-usage.md) · [core-concepts.md](references/core-concepts.md) · [troubleshooting.md](references/troubleshooting.md) · [rubric.md](references/rubric.md) · [prompt-templates.md](references/prompt-templates.md)

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md): parse `aiops_delegate`; deduplicate writes by `idempotency_key` for 24h; require `confirmation_token` for stop/scale/deploy/destructive actions; `MANUAL` never writes, `AI_ASSIST` writes only with token, `AUTO_HEAL` permits bounded non-destructive scaling; propagate `trace_id` as `User-Agent: aiops-orchestrator/<trace_id>` and always emit `aiops_context` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).
