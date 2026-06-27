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
  orchestrator_compat: ">=0.1.0"
  delegate:
    accepts: ['self-heal', 'capacity-forecast']
    produces_facts: ['state', 'metric']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---

# AWS Auto Scaling Operations Skill

## Common JSON Paths (Centralized)

```
# ASGs:              .AutoScalingGroups[].{AutoScalingGroupName,MinSize,MaxSize,DesiredCapacity,Instances[*].InstanceId,Status,
#                                          LaunchConfigurationName,LaunchTemplate.{LaunchTemplateName,Version},
#                                          VPCZoneIdentifier,TargetGroupARNs,LoadBalancerNames,CreatedTime}
# Describe ASG:       .AutoScalingGroups[0].{AutoScalingGroupName,MinSize,MaxSize,DesiredCapacity,Instances[*].{InstanceId,LifecycleState,HealthStatus}}
# Create ASG:         no body (HTTP 200)
# Update ASG:         no body (HTTP 200)
# Delete ASG:         no body (HTTP 200)
# Scale Policies:     .ScalingPolicies[].{PolicyName,PolicyType,ScalingAdjustment,AdjustmentType,Cooldown}
# Scheduled Actions:  .ScheduledUpdateGroupActions[].{ScheduledActionName,Recurrence,MinSize,MaxSize,DesiredCapacity}
# Lifecycle Hooks:    .LifecycleHooks[].{LifecycleHookName,LifecycleTransition,HeartbeatTimeout,DefaultResult}
# Instance Refresh:   .InstanceRefresh.{InstanceRefreshId,Status,PercentageComplete,EndTime}
# Launch Config:      .LaunchConfigurations[0].{LaunchConfigurationName,ImageId,InstanceType,KeyName,SecurityGroups}
# Activities:         .Activities[].{ActivityId,Description,Cause,StartTime,EndTime,StatusCode}
```

## Overview

Amazon EC2 Auto Scaling automatically maintains target capacity and scales
EC2 instances based on policies, schedules, or health checks. This skill is
an **operational runbook** with explicit scope, credential rules, pre-flight
checks, dual-path execution (AWS CLI + boto3 SDK), validation, and recovery.

## Trigger & Scope

### SHOULD Use When
- User mentions "Auto Scaling", "ASG", "autoscaling", "scale out/in"
- Task involves CRUD on **Auto Scaling Groups** (create, describe, update, delete)
- Task involves **scaling policies** (step, simple, target tracking, predictive)
- Task involves **scheduled actions**, **lifecycle hooks**, **instance refresh**
- Task involves **launch configurations** or **launch templates** for ASGs
- Task involves **attach/detach** instances, LBs, or target groups
- Keywords: auto-scaling, asg, scale-out, scale-in, scaling-policy, instance-refresh, lifecycle-hook, warm-pool, suspend-process, resume-process

### SHOULD NOT Use When
- IAM only → delegate to: `aws-iam-ops`
- EC2 instance lifecycle (launch/stop/terminate) → delegate to: `aws-ec2-ops`
- Load Balancer / Target Group management → delegate to: `aws-elb-ops`
- VPC / Subnet / Security Group → delegate to: `aws-vpc-ops`
- Standalone CloudWatch alarm without ASG context → delegate to: `aws-cloudwatch-ops`

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default `us-east-1` if unset |
| `{{env.AWS_PROFILE}}` | Runtime env | Use named profile over explicit keys |
| `{{user.region}}` | User input | Ask once; reuse |
| `{{user.asg_name}}` | User input | Auto Scaling Group name |
| `{{user.lt_name}}` | User input | Launch Template name (or ID) |
| `{{user.lt_version}}` | User input | Launch Template version (`$Default`, `$Latest`, or number) |
| `{{user.lc_name}}` | User input | Launch Configuration name |
| `{{user.min_size}}` | User input | Minimum group size |
| `{{user.max_size}}` | User input | Maximum group size |
| `{{user.desired_capacity}}` | User input | Desired instance count |
| `{{user.subnet_ids}}` | User input | Comma-separated subnet IDs |
| `{{user.sg_ids}}` | User input | Security group IDs |
| `{{user.policy_name}}` | User input | Scaling policy name |
| `{{user.scheduled_action_name}}` | User input | Scheduled action name |
| `{{user.lifecycle_hook_name}}` | User input | Lifecycle hook name |
| `{{user.target_group_arns}}` | User input | Target group ARNs |
| `{{user.instance_id}}` | User input/output | Instance ID |
| `{{output.asg_name}}` | API response | Parse: `.AutoScalingGroups[0].AutoScalingGroupName` |
| `{{output.instance_ids}}` | API response | Parse: `.AutoScalingGroups[0].Instances[*].InstanceId` |
| `{{output.activity_id}}` | API response | Parse: `.Activities[0].ActivityId` |

## Execution Flow Pattern

Every operation: **Pre-flight → Execute → Validate → Recover**

```
Pre-flight → Execute (CLI/SDK) → Validate (Poll) → Recover (On Error)
```

> **Token Efficiency**: Full CLI/boto3 command blocks are in
> `references/aws-cli-usage.md` (CLI patterns) and
> `references/boto3-sdk-usage.md` (SDK patterns).
> This section is the summary runbook — operation headers + critical pre-flight
> checks + safety gates only.

### Operation: Create Auto Scaling Group

**Pre-flight checks** (all required; HALT on failure):
| Check | Command |
|-------|---------|
| CLI | `aws --version` |
| Credentials | `aws sts get-caller-identity --output json` |
| Launch Template | `aws ec2 describe-launch-template-versions --launch-template-name {{user.lt_name}} --output json` |
| Subnets | `aws ec2 describe-subnets --subnet-ids {{user.subnet_ids}} --output json` |
| Quota | `aws autoscaling describe-auto-scaling-groups --max-items 1 --output json` |

**Execute — CLI** (see `references/aws-cli-usage.md` §Create Auto Scaling Group):
```bash
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name "{{user.asg_name}}" \
  --launch-template "LaunchTemplateName={{user.lt_name}},Version={{user.lt_version}}" \
  --min-size {{user.min_size}} --max-size {{user.max_size}} --desired-capacity {{user.desired_capacity}} \
  --vpc-zone-identifier "{{user.subnet_ids}}" --region "{{user.region}}" --output json
```

**Validate**: `describe-auto-scaling-groups` → confirm `{{output.asg_name}}` matches with correct capacity.
**Recover**: see `references/troubleshooting.md` §Common API Error Codes.

### Operation: Delete Auto Scaling Group

**Safety Gate**: `confirm=DELETE {{user.asg_name}}` required before Execute.

**Pre-flight**:
```bash
aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names "{{user.asg_name}}" --region "{{user.region}}" --output json
aws autoscaling describe-load-balancers --auto-scaling-group-name "{{user.asg_name}}" --region "{{user.region}}" --output json
aws autoscaling describe-load-balancer-target-groups --auto-scaling-group-name "{{user.asg_name}}" --region "{{user.region}}" --output json
```
Log: instance count, attached LBs/TGs, current Min/Max/Desired.

**Execute**: scale-to-0 first, then delete. Full CLI + boto3 in `references/aws-cli-usage.md` §Delete Auto Scaling Group.
**Validate**: `describe-auto-scaling-groups` returns empty `AutoScalingGroups` array.
**Recover**: see `references/troubleshooting.md`.

### Operation: Update Auto Scaling Group

**Pre-flight**: `describe-auto-scaling-groups` — verify min ≤ desired ≤ max.
**Execute**: `aws autoscaling update-auto-scaling-group` (see `references/aws-cli-usage.md`).
**Validate**: read-back + compare MinSize/MaxSize/DesiredCapacity.

### Operation: Suspend / Resume Processes

**Pre-flight**: `describe-auto-scaling-groups` → check `SuspendedProcesses`.
**Execute**: `suspend-processes` / `resume-processes` (see `references/aws-cli-usage.md`).
**Safety**: HealthCheck / ReplaceUnhealthy suspend blocks instance replacement — confirm impact.

### Operation: Create Scaling Policy

**Pre-flight**: verify ASG exists.
**Execute**: target-tracking (recommended) or step-scaling. Full commands in `references/aws-cli-usage.md` §Create Scaling Policy.

### Operation: Create Scheduled Action

**Execute**: `put-scheduled-update-group-action` (see `references/aws-cli-usage.md` §Create Scheduled Action).
**Validate**: recurrence cron is UTC; verify `describe-scheduled-actions`.

### Operation: Instance Refresh

**Pre-flight**: verify no other refresh in progress.
**Execute**: `start-instance-refresh` with MinHealthyPercentage ≥ 90% for prod (see `references/aws-cli-usage.md`).
**Validate**: poll `describe-instance-refreshes` until `Status = Successful | Failed`.

### Operation: Attach / Detach Instances

**Detach Safety Gate**: `confirm=DETACH {{user.instance_id}}` required. Agent MUST ask about `--should-decrement-desired-capacity`.
**Execute**: see `references/aws-cli-usage.md` §Attach / Detach Instances.

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md) ← CLI commands (TE-6: canonical source)
- [boto3 SDK Usage](references/boto3-sdk-usage.md) ← SDK patterns (TE-6: canonical source)
- [Core Concepts](references/core-concepts.md) ← architecture, limits, scaling types
- [Troubleshooting](references/troubleshooting.md) ← error codes, diagnostics (TE-3 canonical)
- [Integration Setup](references/integration.md)

## Quality Gate (GCL)

GCL adversarial quality gate for destructive ops. Full spec: [`gcl-spec.md`](../../aws-skill-generator/references/gcl-spec.md). 5-dimension rubric in `references/rubric.md`: Correctness / Safety / Idempotency / Traceability / Spec Compliance (0/0.5/1). **Safety=0 → ABORT**.

| Op | GCL | Confirm token |
|----|-----|---------------|
| `delete-auto-scaling-group` | required | `confirm=DELETE <asg-name>` |
| `delete-launch-configuration` | required | `confirm=DELETE_LC <lc-name>` |
| `delete-policy` | required | `confirm=DELETE_POLICY <name>` |
| `delete-scheduled-action` | required | `confirm=DELETE_SCHEDULE <name>` |
| `delete-lifecycle-hook` | required | `confirm=DELETE_HOOK <name>` |
| `detach-instances` | required | `confirm=DETACH <id>` + explicit `--should-decrement-desired-capacity` |
| `detach-lb-tg` | required | `confirm=DETACH_TG <arn>` |
| `set-desired-capacity → 0` | required | effectively terminates all instances |
| `suspend-processes` | recommended | HealthCheck/ReplaceUnhealthy = high impact |
| all others | not required | |

Trace: `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json`. Templates: `references/prompt-templates.md`.

## Token Efficiency Guidelines (P0)

### TE-1: API Query > Static Tables
Use API commands instead of hardcoding instance types or scaling limits.
```markdown
# DO: minimal table + API fallback
aws autoscaling describe-auto-scaling-groups --query "..."
```
### TE-2: No docstrings in boto3 SDK
Inline comments only; omit docstrings.
### TE-3: Compact error tables
| Error | Resolution |
|-------|-----------|
| ScalingActivityInProgress | Wait and retry |
### TE-4: Centralized JSON paths
See `## Common JSON Paths` block above.
### TE-5: YAML anchors in example-config.yaml
Use `&dev` / `&prod` anchors.
### TE-6: Eliminate cross-file duplicate flows
Full CLI flow in `references/aws-cli-usage.md`; full SDK flow in `references/boto3-sdk-usage.md`.
SKILL.md holds operation headers, pre-flight checks, and safety gates only.

**See**: `aws-skill-generator` SKILL.md §Token Efficiency Requirements for detailed examples.

## AIOps Delegate Contract

Orchestrator-aware. Parse `aiops_delegate:` block (see [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md)):
`request_id`, `parent_intent` (health-check|rca|self-heal|cost-forecast|capacity-forecast|change-impact|compliance-scan|forensic), `action_mode` (observe|recommend|auto-heal|manual), `decision_tier` (AUTO_HEAL|AI_ASSIST|MANUAL), `scope.resource_ids`.

Rules: (1) idempotency via `idempotency_key` → 24h cache; (2) destructive ops require `confirmation_token` → refuse if absent; (3) MANUAL = read-only, AI_ASSIST = recommendations + exec with token, AUTO_HEAL = non-destructive exec directly; (4) include `trace_id` in User-Agent; (5) always output `aiops_context:` JSON block.

Runbook library: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).

