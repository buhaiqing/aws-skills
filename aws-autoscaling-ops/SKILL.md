---
name: aws-autoscaling-ops
description: >-
  Use when the user needs to manage Auto Scaling Groups (ASGs), launch
  configurations/templates, scaling policies, scheduled actions, lifecycle
  hooks, or instance refresh operations in EC2 Auto Scaling; user mentions
  "Auto Scaling", "ASG", "autoscaling", "scale out/in", "scaling policy",
  "instance refresh", or "lifecycle hook".
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to EC2 Auto Scaling endpoints.
metadata:
  author: aws
  version: "1.1.0"
  last_updated: "2026-06-27"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  gcl:
    enabled: true
    class: required
    max_iter: 2
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: false
  destructive_ops_require_confirm: true
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_DEFAULT_REGION
    - AWS_PROFILE
  cross_skill_deps:
    - aws-ec2-ops              # Launch Template / AMI / Instance diagnostics
    - aws-elb-ops              # Target group / Load balancer attachment
    - aws-cloudwatch-ops       # Metric alarms for scaling policies
    - aws-vpc-ops              # Subnet / Security Group management
  orchestrator_aware: true
  orchestrator_compat: ">=0.10"
  delegate:
    accepts: ['self-heal', 'capacity-forecast']
    produces_facts: ['state', 'metric']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---

# AWS Auto Scaling Operations Skill

Use for EC2 Auto Scaling Groups, launch templates/configurations, scaling policies, schedules, lifecycle hooks, refreshes, attachments, and capacity changes. Detailed commands remain in references.

## Common JSON Paths

Groups: .AutoScalingGroups[].{AutoScalingGroupName,MinSize,MaxSize,DesiredCapacity,Instances,Status}
Group: .AutoScalingGroups[0].{AutoScalingGroupName,MinSize,MaxSize,DesiredCapacity,Instances}
Policies: .ScalingPolicies[].{PolicyName,PolicyType,ScalingAdjustment,AdjustmentType,Cooldown}
Schedules: .ScheduledUpdateGroupActions[].{ScheduledActionName,Recurrence,MinSize,MaxSize,DesiredCapacity}
Hooks: .LifecycleHooks[].{LifecycleHookName,LifecycleTransition,HeartbeatTimeout,DefaultResult}
Refresh: .InstanceRefresh.{InstanceRefreshId,Status,PercentageComplete,EndTime}
Activities: .Activities[].{ActivityId,Description,Cause,StartTime,EndTime,StatusCode}

## Trigger & Scope

### SHOULD Use When
ASGs, scale-in/out, desired capacity, policies, scheduled actions, lifecycle hooks, instance refresh, warm pools, or ASG attachments.

### SHOULD NOT Use When
IAM → `aws-iam-ops`; EC2 lifecycle → `aws-ec2-ops`; load balancers → `aws-elb-ops`; VPC → `aws-vpc-ops`; standalone alarms → `aws-cloudwatch-ops`.

## Variable Convention

| Placeholder | Source | Use |
|---|---|---|
| `{{env.AWS_*}}` | Runtime env | Never ask; fail closed if unset |
| `{{user.asg_name}}`, `{{user.instance_id}}` | User input | Group/instance IDs |
| `{{user.min_size}}`, `{{user.max_size}}`, `{{user.desired_capacity}}` | User input | Capacity bounds |
| `{{user.lt_name}}`, `{{user.lt_version}}`, `{{user.subnet_ids}}` | User input | Launch/network settings |
| `{{output.*}}` | API response | Reuse group, instance, activity, refresh IDs |

## Execution Flow Pattern

Every operation follows **Pre-flight → Execute → Validate → Recover**. Run `aws --version` and `aws sts get-caller-identity --output json`; verify launch template, subnets, quotas, identifiers, and `min ≤ desired ≤ max`. Use CLI `--output json`, then boto3 after 3 CLI failures. Validate with describe/read-back and poll activities/refreshes; recover via [troubleshooting.md](references/troubleshooting.md) with bounded retries.

## Operations and Safety

| Operation | Required checks | Confirmation |
|---|---|---|
| Create/update ASG | Verify launch template, subnets, quota, capacity bounds | Token for desired capacity 0 |
| Delete ASG | Describe instances/LBs/TGs; scale to 0 first; validate group absent | `DELETE {{user.asg_name}}` |
| Delete launch config/policy/schedule/hook | Verify target and dependencies | `DELETE_LC`, `DELETE_POLICY`, `DELETE_SCHEDULE`, or `DELETE_HOOK` + name |
| Suspend processes | Inspect suspended processes; warn for HealthCheck/ReplaceUnhealthy | Human confirmation for high-impact processes |
| Instance refresh | No active refresh; production MinHealthyPercentage ≥90%; poll completion | Human confirmation |
| Attach/detach instance | Inspect group/capacity; ask whether desired capacity decrements | `DETACH {{user.instance_id}}` |
| Detach target group | Inspect traffic impact and attachments | `DETACH_TG <arn>` |

## Quality Gate (GCL)

Required GCL, `max_iter=2`, rubric `references/rubric.md`, prompts `references/prompt-templates.md`; `Safety=0` aborts and traces persist under `./audit-results/`. Apply A7–A10 and A16: force deletion with desired capacity >0 must scale to 0 first.

## Token Efficiency

TE-1…TE-6 apply; query live limits and ASG state, keep SDK examples comment-only, centralize JSON paths above, use asset anchors, and keep flows single-sourced.

## Reference Files

[aws-cli-usage.md](references/aws-cli-usage.md) · [boto3-sdk-usage.md](references/boto3-sdk-usage.md) · [core-concepts.md](references/core-concepts.md) · [troubleshooting.md](references/troubleshooting.md) · [integration.md](references/integration.md) · [rubric.md](references/rubric.md) · [prompt-templates.md](references/prompt-templates.md)

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md): parse `aiops_delegate`; deduplicate writes by `idempotency_key` for 24h; require `confirmation_token` for destructive ops; `MANUAL` never writes, `AI_ASSIST` writes only with token, `AUTO_HEAL` permits non-destructive writes; propagate `trace_id` as `User-Agent: aiops-orchestrator/<trace_id>` and always emit `aiops_context` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).
