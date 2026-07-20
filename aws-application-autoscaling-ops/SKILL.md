---
name: aws-application-autoscaling-ops
description: >-
  Use when operating AWS Application Auto Scaling (cross-service scaler
  namespace) for ECS Service DesiredCount, DynamoDB Table Capacity, Lambda
  Provisioned Concurrency, or Spot Fleet; user mentions "Application Auto
  Scaling", "scalable target", "scaling policy", "target tracking", or
  "step scaling". MVP scope covers ECS-only (other ServiceNamespace
  deferred to follow-up plans).
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network
  access to Application Auto Scaling endpoints.
metadata:
  author: aws
  version: "1.2.0"
  last_updated: "2026-07-21"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  type: base
  provides:
    - app-autoscaling-register-target
    - app-autoscaling-deregister-target
    - app-autoscaling-put-policy
    - app-autoscaling-delete-policy
    - app-autoscaling-tag-resource
    - app-autoscaling-describe
  destructive_ops_require_confirm: true
  gcl:
    enabled: true
    class: required
    max_iter: 2
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: false
  cross_skill_deps:
    - aws-ecs-ops           # ECS Service / Cluster lookup
    - aws-cloudwatch-ops    # Alarm source for target tracking
    - aws-cloudtrail-ops    # Change audit for App Auto Scaling API calls
  orchestrator_aware: true
  orchestrator_compat: ">=0.1.0"
  delegate:
    accepts: ['capacity-forecast', 'self-heal']
    produces_facts: ['state']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_SESSION_TOKEN
    - AWS_DEFAULT_REGION
    - AWS_PROFILE
---

# AWS Application Auto Scaling Operations Skill

## Layering Contract (type / provides / delegate)

`metadata.type: base` (L1 single-service runbook). `provides:` lists 6
operations this skill handles. `delegate:` declares what this skill
*accepts* from upstream (orchestrator) and *produces_facts* downstream.
This skill is orchestrator-aware — composite skills like
`aws-finops-core` and `aws-aiops-orchestrator` may invoke it via the
delegate envelope per Charter C7.

## Overview

AWS Application Auto Scaling is a **cross-service scaler namespace**
for Elastic Container Service, DynamoDB, Lambda, Spot Fleet, EMR, and
more. Single API surface for registering *scalable targets* and
attaching *scaling policies* (target-tracking, step, or scheduled).
**MVP scope: ECS-only**. Lambda / DynamoDB / Spot Fleet are deferred
to follow-up plans (see ADR defer in plan).

## Common JSON Paths (Centralized — TE-4)

```
# ScalableTarget:  .ScalableTargets[].{ServiceNamespace,ResourceId,ScalableDimension,
#                       MinCapacity,MaxCapacity,RoleARN,CreationTime}
# ScalingPolicy:   .ScalingPolicies[].{PolicyName,ServiceNamespace,ResourceId,ScalableDimension,
#                       PolicyType,TargetTrackingScalingPolicyConfiguration,StepScalingPolicyConfiguration,
#                       Alarms[],CreationTime}
# TagResponse:     no body (HTTP 200)
```

## Trigger & Scope

### SHOULD Use When
- User mentions "Application Auto Scaling", "scaling policy", "scalable target"
- Task involves registering/deregistering scalable targets for ECS Service `DesiredCount`
- Task involves putting/deleting scaling policies (target-tracking on `ECSServiceAverageCPUUtilization`, step scaling on CloudWatch alarms, scheduled actions)
- Task involves attaching cost-allocation / governance tags to Application Auto Scaling resources
- Keywords: target-tracking, step-scaling, scheduled-action,
  ECSServiceAverageCPUUtilization, ECSServiceAverageMemoryUtilization,
  scalable-target, MinCapacity, MaxCapacity

### SHOULD NOT Use When
- EC2 Auto Scaling (ASG) only → delegate to: `aws-autoscaling-ops`
- ECS service / cluster / task CRUD only → delegate to: `aws-ecs-ops`
- CloudWatch alarm CRUD only → delegate to: `aws-cloudwatch-ops`
- DynamoDB-only capacity scaling (non-orchestrator, single-service use case) → use `aws-dynamodb-ops` (`register-scalable-target` inline call at SKILL.md line 716)
- Lambda Provisioned Concurrency (deferred — no skill yet)

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default; allow override |
| `{{env.AWS_PROFILE}}` | Runtime env | Overrides explicit keys |
| `{{user.service_namespace}}` | User input | ECS MVP; other namespaces deferred |
| `{{user.resource_id}}` | User input | Format `service/<cluster>/<service>` for ECS |
| `{{user.scalable_dimension}}` | User input | Default `ecs:service:DesiredCount` |
| `{{user.min_capacity}}` / `{{user.max_capacity}}` | User input | Integer bounds; Min ≤ Max |
| `{{user.policy_name}}` | User input | Unique within (namespace, resource_id, dimension) |
| `{{user.policy_type}}` | User input | `TargetTrackingScaling` \| `StepScaling` |
| `{{user.tag_project}}` / `{{user.tag_environment}}` | User input | Cost Allocation tags |
| `{{output.scalable_target}}` | Last API response | Per JSON paths above |
| `{{output.policy_arn}}` | Last API response | `.ScalingPolicies[0].PolicyARN` |
| `{{output.resource_arn}}` | Constructed locally | `arn:aws:application-autoscaling:<region>:<acct>:scalable-target/<hash>` |

## Config File Placeholders

`assets/example-config.yaml` uses `{{env.*}}` for environment and
`{{user.*}}` for resource-specific values. YAML anchors (`&anchor` /
`*anchor`) share fields across examples (TE-5).

## Execution Flow Pattern

Every operation: **Pre-flight → Execute → Validate → Recover**

```
Pre-flight  →  Execute (CLI / SDK)  →  Validate (read-back)  →  Recover (on error)
```

### Operation: Register Scalable Target

Bind an ECS service to Application Auto Scaling with capacity bounds.

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `aws --version` | Install AWS CLI v2 |
| Credentials | `aws sts get-caller-identity` | HALT |
| Service exists | `aws ecs describe-services` | HALT |
| Current target | `describe-scalable-targets` | Idempotent overwrite |

#### Execute — CLI
```bash
aws application-autoscaling register-scalable-target \
  --service-namespace "{{user.service_namespace}}" \
  --resource-id "{{user.resource_id}}" \
  --scalable-dimension "{{user.scalable_dimension}}" \
  --min-capacity {{user.min_capacity}} \
  --max-capacity {{user.max_capacity}} \
  --region "{{env.AWS_DEFAULT_REGION}}" \
  --output json
```

#### Execute — boto3
```python
import boto3
client = boto3.client('application-autoscaling', region_name='{{env.AWS_DEFAULT_REGION}}')
client.register_scalable_target(
  serviceNamespace='{{user.service_namespace}}',
  resourceId='{{user.resource_id}}',
  scalableDimension='{{user.scalable_dimension}}',
  minCapacity={{user.min_capacity}},
  maxCapacity={{user.max_capacity}})
```

#### Validate
```bash
aws application-autoscaling describe-scalable-targets \
  --service-namespace "{{user.service_namespace}}" --resource-id "{{user.resource_id}}" \
  --query "ScalableTargets[0].{min:MinCapacity, max:MaxCapacity, dim:ScalableDimension}" \
  --output json
```

#### Recover
| Error | Action |
|-------|--------|
| `ValidationException` | Verify resource_id format matches ServiceNamespace |
| `LimitExceededException` | Request quota increase (Service Quotas L-7B6389E7) |

### Operation: Deregister Scalable Target

**Safety Gate**: MUST obtain explicit user confirmation. Service loses
auto-scale capability on deregister.

```
[WARN] Deregistering scalable target {{user.resource_id}} will remove any attached scaling policies. Type 'DEREGISTER_SCALABLE_TARGET {{user.resource_id}}' to confirm.
```

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
| Target exists | `describe-scalable-targets` | HALT (verify state) |
| Active policies | `describe-scaling-policies` | HALT — delete policies first (rule A11) |
| Production confirm | User types `DEREGISTER_SCALABLE_TARGET <id>` | HALT |
| ResourceId echo | describe returns ResourceId exactly | Verify A8 |

#### Execute — CLI
```bash
aws application-autoscaling deregister-scalable-target \
  --service-namespace "{{user.service_namespace}}" \
  --resource-id "{{user.resource_id}}" \
  --scalable-dimension "{{user.scalable_dimension}}" \
  --region "{{env.AWS_DEFAULT_REGION}}" --output json
```

#### Execute — boto3
```python
client.deregister_scalable_target(
  serviceNamespace='{{user.service_namespace}}',
  resourceId='{{user.resource_id}}',
  scalableDimension='{{user.scalable_dimension}}')
```

#### Validate
`describe-scalable-targets` returns empty `ScalableTargets[]` for the resource_id.

#### Recover
| Error | Action |
|-------|--------|
| `ObjectNotFoundException` | Already deregistered — idempotent |
| `ConcurrentUpdateException` | Backoff 5s; retry once |

### Operation: Put Scaling Policy

Attach a target-tracking or step scaling policy to a registered
target. **Canonical AIOps auto-heal recipe**: target tracking on
`ECSServiceAverageCPUUtilization`.

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
| Target registered | `describe-scalable-targets` | HALT |
| Alarm exists (step) | `aws cloudwatch describe-alarms` | HALT |
| Cooldown bounds | user input ≤ 3600s | HALT (rule A12) |

#### Execute — CLI (Target Tracking)
```bash
aws application-autoscaling put-scaling-policy \
  --service-namespace "{{user.service_namespace}}" --resource-id "{{user.resource_id}}" \
  --scalable-dimension "{{user.scalable_dimension}}" --policy-name "{{user.policy_name}}" \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{"TargetValue":{{user.target_value|default(50)}},"PredefinedMetricSpecification":{"PredefinedMetricType":"ECSServiceAverageCPUUtilization"},"ScaleOutCooldown":{{user.scale_out_cooldown|default(60)}},"ScaleInCooldown":{{user.scale_in_cooldown|default(300)}}}' \
  --output json
```

#### Execute — boto3 (Target Tracking)
```python
client.put_scaling_policy(
  serviceNamespace='{{user.service_namespace}}', resourceId='{{user.resource_id}}',
  scalableDimension='{{user.scalable_dimension}}', policyName='{{user.policy_name}}',
  policyType='TargetTrackingScaling',
  targetTrackingScalingPolicyConfiguration={
    'TargetValue': {{user.target_value|default(50)}},
    'PredefinedMetricSpecification': {'PredefinedMetricType': 'ECSServiceAverageCPUUtilization'},
    'ScaleOutCooldown': {{user.scale_out_cooldown|default(60)}},
    'ScaleInCooldown': {{user.scale_in_cooldown|default(300)}}})
```

#### Validate
```bash
aws application-autoscaling describe-scaling-policies \
  --service-namespace "{{user.service_namespace}}" --resource-id "{{user.resource_id}}" \
  --query "ScalingPolicies[?PolicyName=='{{user.policy_name}}'].{arn:PolicyARN,type:PolicyType}"
```

#### Recover
| Error | Action |
|-------|--------|
| `ValidationException` | Verify metric namespace + cooldown bounds |
| `LimitExceededException` | 50 policies / target soft cap; cleanup unused |

### Operation: Delete Scaling Policy

**Safety Gate**: MUST obtain explicit user confirmation. Service will
fall back to manual capacity (no auto-recovery on metric spike).

```
[WARN] Deleting scaling policy {{user.policy_name}} from {{user.resource_id}} disables auto-scale. Type 'DELETE_SCALING_POLICY {{user.policy_name}}' to confirm.
```

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
| Policy exists | `describe-scaling-policies` | HALT |
| Production confirm | User types `DELETE_SCALING_POLICY <name>` | HALT |
| PolicyName echo | describe returns PolicyName exactly | Verify A8 |

#### Execute — CLI
```bash
aws application-autoscaling delete-scaling-policy \
  --service-namespace "{{user.service_namespace}}" --resource-id "{{user.resource_id}}" \
  --scalable-dimension "{{user.scalable_dimension}}" --policy-name "{{user.policy_name}}" \
  --region "{{env.AWS_DEFAULT_REGION}}" --output json
```

#### Execute — boto3
```python
client.delete_scaling_policy(
  serviceNamespace='{{user.service_namespace}}', resourceId='{{user.resource_id}}',
  scalableDimension='{{user.scalable_dimension}}', policyName='{{user.policy_name}}')
```

#### Validate
`describe-scaling-policies` for the resource_id returns no match for `PolicyName`.

#### Recover
| Error | Action |
|-------|--------|
| `ObjectNotFoundException` | Idempotent — already deleted |

### Operation: Tag Resource

Attach cost-allocation / governance tags to an Application Auto
Scaling resource. **Chargeback entrance ticket** (compounds with
`aws-ecs-ops` `--tags` convention per CHANGELOG 1.1.0).

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
| Resource exists | `describe-scalable-targets` or `describe-scaling-policies` | HALT |

#### Execute — CLI
```bash
aws application-autoscaling tag-resource \
  --resource-arn "{{output.resource_arn}}" \
  --tags Key=Project,Value={{user.tag_project}} Key=Environment,Value={{user.tag_environment}} Key=ManagedBy,Value=aiops \
  --region "{{env.AWS_DEFAULT_REGION}}" --output json
```

#### Execute — boto3
```python
client.tag_resource(
  ResourceARN='{{output.resource_arn}}',
  Tags=[{'Key':'Project','Value':'{{user.tag_project}}'},
        {'Key':'Environment','Value':'{{user.tag_environment}}'},
        {'Key':'ManagedBy','Value':'aiops'}])
```

#### Validate
```bash
aws application-autoscaling list-tags-for-resource \
  --resource-arn "{{output.resource_arn}}" \
  --query "Tags[?Key=='Project']"
```

#### Recover
| Error | Action |
|-------|--------|
| `ResourceNotFoundException` | Verify ARN; for ECS, scalable-targets don't expose ARN directly — use ResourceId-keyed describe |

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md) — CLI + JSON paths (canonical, TE-6)
- [boto3 SDK Usage](references/boto3-sdk-usage.md) — SDK patterns (no docstrings, TE-2)
- [Core Concepts](references/core-concepts.md) — ServiceNamespace / ScalableDimension (no static tables >5 rows, TE-1)
- [Troubleshooting](references/troubleshooting.md) — Error codes (compact, TE-3)
- [GCL Rubric](references/rubric.md) — 5-dimension scoring (v1)
- [GCL Prompt Templates](references/prompt-templates.md) — shared skeleton specialization
- [Example Config](assets/example-config.yaml) — YAML anchors for ECS patterns
- [EMR Patterns](references/emr.md) — EMR InstanceGroup scaling
- [SageMaker Patterns](references/sagemaker.md) — endpoint variant
- [Comprehend Patterns](references/comprehend.md) — NLP inference units
- [Keyspace Patterns](references/keyspace.md) — Cassandra-compatible
- [Lambda Patterns](references/lambda.md) — Lambda Provisioned Concurrency
- [DynamoDB Patterns](references/dynamodb.md) — DynamoDB Table / GSI capacity
- [Spot Fleet Patterns](references/spot-fleet.md) — ec2:spot-fleet-request:TargetCapacity
- [CHANGELOG](CHANGELOG.md) — v1.1.0+ history

## Token Efficiency Guidelines (P0)

### TE-1: API Query > Static Tables
All ServiceNamespace / ScalableDimension / Quota data via API call (`aws service-quotas get-service-quota`); never hardcoded.

### TE-2: No docstrings in boto3
Inline comments only in `references/boto3-sdk-usage.md`.

### TE-3: Compact error tables
One row per error in `references/troubleshooting.md` and per Operation's Recover block.

### TE-4: JSON paths at file top
`## Common JSON Paths` block above + per-reference file top.

### TE-5: YAML anchors in example-config.yaml
Shared fields use `&anchor` / `*anchor` references.

### TE-6: No duplicate flows across SKILL.md and references
Full CLI flow in references/; SKILL.md holds operation summaries + Safety Gates only.

## Quality Gate (GCL)

| Setting | Value |
|---|---|
| Class | `required` |
| `max_iterations` | `2` |
| Rubric | `references/rubric.md` (v1) |
| Prompts | `references/prompt-templates.md` (shared skeleton specialization) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |

Destructive ops requiring `{{user.safety_confirm}}`:
- `deregister-scalable-target` — confirm `DEREGISTER_SCALABLE_TARGET <resource_id>`
- `delete-scaling-policy` — confirm `DELETE_SCALING_POLICY <policy_name>`

Relevant AWS rules (per `aws-skill-generator/references/gcl-spec.md` §8): A7 (region), A8 (resource_id / policy_name echoed via describe-* before destructive ops), A9 (no secrets), A10 (sts first), A11 (no active policy before deregister), A12 (cooldown ≤ 3600s).

## AIOps Delegate Contract

Orchestrator-aware per [`aws-aiops-orchestrator/references/delegate-routing.md`](../aws-aiops-orchestrator/references/delegate-routing.md). Parse `aiops_delegate:` (`request_id`, `parent_intent`, `action_mode`, `decision_tier`, `scope`, `trace_id`). Writes: idempotency_key (24h dedup); destructive ops need `confirmation_token`; propagate `trace_id` in User-Agent; always emit `aiops_context:` JSON. Runbooks: `aws-aiops-orchestrator/references/runbook-recipes.md`.

> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。
