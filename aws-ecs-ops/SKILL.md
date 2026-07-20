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
  version: "1.1.0"
  provides:
    - ecs-cluster-lifecycle
    - ecs-service-lifecycle
    - ecs-task-definition-lifecycle
    - ecs-task-lifecycle
    - ecs-idle-service-discovery
    - ecs-fargate-rightsizing
    - ecs-fargate-spot-optimization
  last_updated: "2026-07-21"
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
  orchestrator_compat: ">=0.1.0"
  delegate:
    accepts: ["health-check", "rca", "capacity-review"]
    produces_facts: ["state", "metric", "event"]
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true
---

# AWS ECS Operations Skill

## Overview

AWS Elastic Container Service (ECS) is a fully managed container orchestration service. This skill covers **cluster, service, task definition, and task lifecycle management** with Fargate and EC2 launch types, plus AIOps detection signals (Container Insights) and FinOps levers (Fargate Spot, Compute Optimizer, tag governance, idle discovery).

## Common Container Insights metric path

```
Cluster     — aws.ecs.cluster.cpu.utilization, aws.ecs.cluster.memory.utilization
Container   — ContainerInsights_CPUUtilization, ContainerInsights_MemoryUtilization
Service     — ECSServiceAverageCPUUtilization, ECSServiceAverageMemoryUtilization
Task stoppedReason — EssentialContainerExited, CannotPullContainerError, SpotInterruption, ResourceInitializationFailed
Deployment  — .services[].deployments[].{rolloutState, taskDefinition, failedTasks}
```

## Trigger & Scope

### SHOULD Use When
- User mentions "ECS", "container service", "Fargate", "task definition"
- Task involves CRUD on **ECS resources** (cluster, service, task definition, task)
- Keywords: ecs, fargate, container, task-definition, service, cluster

### SHOULD NOT Use When
- EC2 instance management → delegate to: `aws-ec2-ops`
- IAM roles/policies for tasks → delegate to: `aws-iam-ops`
- ALB/target group config → delegate to: `aws-elb-ops`
- VPC/subnet/security group → delegate to: `aws-vpc-ops`
- Container image registry → delegate to: `aws-ecr-ops`

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default; allow override |
| `{{user.cluster_name}}` | User input | Ask once; reuse |
| `{{user.service_name}}` | User input | Ask once; reuse |
| `{{user.task_definition}}` | User input | Family name or ARN |
| `{{output.cluster_arn}}` | Last API response | `.clusters[0].clusterArn` |
| `{{output.service_arn}}` | Last API response | `.service.serviceArn` |
| `{{output.task_arn}}` | Last API response | `.task.taskArn` |
| `{{user.opt_in_spot}}` | User input | Y/N; required before Capacity Provider Spot toggle |
| `{{user.tag_project}}` | User input | Cost Allocation: Project tag value |
| `{{user.tag_environment}}` | User input | Cost Allocation: Environment tag value |
| `{{user.tag_cost_center}}` | User input | Cost Allocation: CostCenter tag value |
| `{{output.cluster_capacity_providers}}` | Last API response | `.cluster.capacityProviders` |

## Execution Flow Pattern

**Pre-flight → Execute → Validate → Recover**

### Operation: Create Cluster

#### Pre-flight

| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `aws --version` | Install AWS CLI v2 |
| Credentials | `aws sts get-caller-identity` | HALT; log error |
| Cluster name unique | `aws ecs list-clusters` | Warn if similar name exists |

#### Execute — CLI
```bash
aws ecs create-cluster \
  --cluster-name "{{user.cluster_name}}" \
  --tags Key=ManagedBy,Value=aiops \
  --output json
```

#### Execute — boto3
```python
client = boto3.client('ecs', region_name='{{env.AWS_DEFAULT_REGION}}')
resp = client.create_cluster(clusterName='{{user.cluster_name}}')
```

#### Validate
```bash
aws ecs describe-clusters --clusters "{{user.cluster_arn}}" \
  --query "clusters[0].{Status:status,Running:runningCount,Pending:pendingCount}"
```

### Operation: Register Task Definition

#### Pre-flight
- Verify container image is accessible (ECR or public)
- Verify IAM execution role exists (for Fargate)

#### Execute — CLI
```bash
aws ecs register-task-definition \
  --family "{{user.task_family}}" \
  --network-mode awsvpc \
  --requires-compatibilities FARGATE \
  --cpu "256" \
  --memory "512" \
  --container-definitions '[{
    "name": "app",
    "image": "{{user.container_image}}",
    "portMappings": [{"containerPort": 80, "protocol": "tcp"}]
  }]' \
  --tags Key=Project,Value={{user.tag_project}} Key=Environment,Value={{user.tag_environment}} Key=ManagedBy,Value=aiops \
  --output json
```

#### Validate
```bash
aws ecs describe-task-definition --task-definition "{{user.task_family}}" \
  --query "taskDefinition.{Arn:taskDefinitionArn,Rev:revision,Status:status}"
```

### Operation: Create Service

#### Pre-flight
- Task definition must exist
- Cluster must exist
- For Fargate: subnets and security groups required

#### Execute — CLI
```bash
aws ecs create-service \
  --cluster "{{user.cluster_name}}" \
  --service-name "{{user.service_name}}" \
  --task-definition "{{user.task_definition}}" \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={
    subnets=[{{user.subnets}}],
    securityGroups=[{{user.security_groups}}],
    assignPublicIp=ENABLED
  }" \
  --tags Key=Project,Value={{user.tag_project}} Key=Environment,Value={{user.tag_environment}} Key=CostCenter,Value={{user.tag_cost_center}} Key=ManagedBy,Value=aiops \
  --output json
```

#### Validate
```bash
aws ecs describe-services \
  --cluster "{{user.cluster_name}}" \
  --services "{{user.service_name}}" \
  --query "services[0].{Status:status,Desired:desiredCount,Running:runningCount}"
```

Poll until `status == ACTIVE` and `runningCount == desiredCount`.

### Operation: Update Service (Scale)

```bash
aws ecs update-service \
  --cluster "{{user.cluster_name}}" \
  --service "{{user.service_name}}" \
  --desired-count {{user.desired_count}} \
  --output json
```

### Operation: Stop Task

**Safety Gate**: Confirm before stopping running tasks in production.

```bash
aws ecs stop-task \
  --cluster "{{user.cluster_name}}" \
  --task "{{user.task_arn}}" \
  --reason "Manual stop by operator" \
  --output json
```

### Operation: Delete Service

**Safety Gate**: MUST obtain explicit user confirmation. Service must be scaled to 0 or drained.

```bash
# Pre-flight: scale to 0 first
aws ecs update-service \
  --cluster "{{user.cluster_name}}" \
  --service "{{user.service_name}}" \
  --desired-count 0

# Wait for draining
aws ecs wait services-stable \
  --cluster "{{user.cluster_name}}" \
  --services "{{user.service_name}}"

# Delete
aws ecs delete-service \
  --cluster "{{user.cluster_name}}" \
  --service "{{user.service_name}}" \
  --force \
  --output json
```

```
[WARN] Deleting service {{user.service_name}} will stop all running tasks.
Type 'DELETE_SERVICE {{user.service_name}}' to confirm.
```

### Operation: Deregister Task Definition

```bash
aws ecs deregister-task-definition \
  --task-definition "{{user.task_definition}}" \
  --output json
```

### Operation: Update Capacity Providers

#### Pre-flight

| Check | Method | On Failure |
|-------|--------|------------|
| `{{user.opt_in_spot}} == Y` | User confirm | HALT — safety |
| Cluster exists | `aws ecs describe-clusters` | HALT |
| Current capacity providers | `.cluster.capacityProviders` | Read first |

#### Execute — CLI
```bash
aws ecs put-cluster-capacity-providers \
  --cluster "{{user.cluster_name}}" \
  --capacity-providers 'capacityProvider=[{name=FARGATE,weight={{user.fargate_weight|default(20)}},base={{user.fargate_base|default(20)}}},{name=FARGATE_SPOT,weight={{user.spot_weight|default(80)}},base={{user.spot_base|default(0)}}}]' \
  --output json
```

#### Execute — boto3
```python
client = boto3.client('ecs', region_name='{{env.AWS_DEFAULT_REGION}}')
client.put_cluster_capacity_providers(
  cluster='{{user.cluster_name}}',
  capacityProviders=[
    {'name':'FARGATE','weight':{{user.fargate_weight|default(20)}},'base':{{user.fargate_base|default(20)}}},
    {'name':'FARGATE_SPOT','weight':{{user.spot_weight|default(80)}},'base':{{user.spot_base|default(0)}}},
  ]
)
```

#### Validate
```bash
aws ecs describe-clusters --clusters "{{user.cluster_name}}" \
  --query "clusters[0].capacityProviders"
```

```
[WARN] Toggling capacity provider may interrupt running tasks. Type 'UPDATE_CAPACITY_PROVIDERS {{user.cluster_name}}' to confirm.
```

| Error | Action |
|-------|--------|
| `InvalidParameterException` | Verify weight / base are integers; FARGATE_SPOT must be one of providers |

### Operation: Delete Cluster

**Safety Gate**: Cluster must have no services. Confirm before deletion.

```bash
# Pre-flight: check for services
aws ecs list-services --cluster "{{user.cluster_name}}" \
  --query "serviceArns[]"

# Delete
aws ecs delete-cluster --cluster "{{user.cluster_name}}" --output json
```

```
[WARN] Deleting cluster {{user.cluster_name}} will remove all associated resources.
Type 'DELETE_CLUSTER {{user.cluster_name}}' to confirm.
```

## Recover

| Error | Action |
|-------|--------|
| `ClusterNotFoundException` | Verify cluster name/ARN; list existing clusters |
| `ServiceNotActiveException` | Service must be ACTIVE to update/delete |
| `InvalidParameterException` | Check CPU/memory valid combos for Fargate |
| `ThrottlingException` | Backoff and retry; reduce API call rate |
| `AccessDeniedException` | Check IAM execution role permissions |

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Cost Optimization](references/cost-optimization.md) — Fargate Spot / Compute Optimizer / Savings Plans / Idle / Gateway Endpoint / Tag governance
- [Deployment Health](references/deployment-health.md) — Circuit breaker / `rolloutState` / deployment alarms

## Token Efficiency

All 6 TE rules applied. Key points:
- TE-1: No hardcoded instance types/limits — use `describe-clusters` / `list-container-instances`
- TE-2: Inline comments only in boto3 code
- TE-3: Compact error tables
- TE-4: JSON paths declared inline
- TE-5: YAML anchors in `assets/example-config.yaml`
- TE-6: Flows only in SKILL.md

## Quality Gate (GCL)

| Setting | Value |
|---|---|
| Class | `required` |
| `max_iterations` | `2` |
| Rubric | `references/rubric.md` (v1) |
| Prompts | `references/prompt-templates.md` (v1) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |

Destructive ops requiring `{{user.safety_confirm}}`:
- `delete-service` — drains and removes; confirm `DELETE_SERVICE <name>`
- `delete-cluster` — confirm `DELETE_CLUSTER <name>`

Relevant AWS rules: A7 (region), A8 (ARN echoed from describe), A10 (sts first).
