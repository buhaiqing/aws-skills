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
  last_updated: "2026-07-31"
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
  orchestrator_compat: ">=0.10"
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

Use for scalable targets and policies across ECS, DynamoDB, Lambda, SageMaker, and other supported services. Detailed CLI/SDK patterns remain in references.

## Common JSON Paths

Targets: .ScalableTargets[].{ResourceId,ServiceNamespace,ScalableDimension,MinCapacity,MaxCapacity,RoleARN}
Policies: .ScalingPolicies[].{PolicyName,PolicyARN,PolicyType,ResourceId,ScalableDimension}
Activities: .ScalingActivities[].{ActivityId,StatusCode,Description,Cause}

## Trigger & Scope

### SHOULD Use When
Application Auto Scaling scalable targets, min/max capacity, target/step policies, tags, and scaling activities.

### SHOULD NOT Use When
EC2 ASGs → `aws-autoscaling-ops`; ECS service internals → `aws-ecs-ops`; DynamoDB tables → `aws-dynamodb-ops`; Lambda code → `aws-lambda-ops`.

## Variable Convention

| Placeholder | Source | Use |
|---|---|---|
| `{{env.AWS_*}}` | Runtime env | Never ask; fail closed if unset |
| `{{user.service_namespace}}`, `{{user.resource_id}}`, `{{user.scalable_dimension}}` | User input | Target identity |
| `{{user.min_capacity}}`, `{{user.max_capacity}}`, `{{user.policy_name}}` | User input | Capacity/policy |
| `{{output.*}}` | API response | Reuse target/policy/activity IDs |

## Execution Flow

Every operation follows **Pre-flight → Execute → Validate → Recover**. Verify service namespace, resource existence, IAM role, current target/policies, capacity bounds, and production impact. Use CLI `--output json`, then boto3 after 3 CLI failures. Read back target/policy and poll scaling activities; recover with bounded retries and halt on active policy conflicts. See references for commands and errors.

## Operations and Safety

| Operation | Pre-flight / validation | Confirmation |
|---|---|---|
| Register target | Verify resource and namespace/dimension; validate min≤max | — |
| Update target capacity | Show current and requested capacity and outage/cost impact | Token for production or scale-to-zero |
| Put policy | Verify target and policy uniqueness; validate metric/threshold | Token for aggressive/production policy |
| Deregister target | List and remove scaling policies first (A11); validate absent | `confirm=DEREGISTER_SCALABLE_TARGET {{user.resource_id}}` |
| Delete policy | Verify target/policy and auto-scale impact | `confirm=DELETE_SCALING_POLICY {{user.policy_name}}` |
| Tag resource | Diff keys/values; mask sensitive tags | Human confirmation for ownership/cost tags |

## Quality Gate (GCL)

Required GCL, `max_iter=2`, rubric `references/rubric.md`, prompts `references/prompt-templates.md`; persist traces under `./audit-results/`. Apply A7–A10; Safety=0 aborts.

## Token Efficiency

TE-1…TE-6 apply; query live targets/policies, keep SDK examples comment-only, centralize JSON paths above, use asset anchors, and keep flows single-sourced.

## Reference Files

[aws-cli-usage.md](references/aws-cli-usage.md) · [boto3-sdk-usage.md](references/boto3-sdk-usage.md) · [core-concepts.md](references/core-concepts.md) · [troubleshooting.md](references/troubleshooting.md) · [rubric.md](references/rubric.md) · [prompt-templates.md](references/prompt-templates.md)

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md): parse `aiops_delegate`; deduplicate writes by `idempotency_key` for 24h; require `confirmation_token` for scale/policy/destructive actions; `MANUAL` never writes, `AI_ASSIST` writes only with token, `AUTO_HEAL` permits bounded non-destructive tuning; propagate `trace_id` as `User-Agent: aiops-orchestrator/<trace_id>` and always emit `aiops_context` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).
