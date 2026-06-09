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
  version: "1.0.0"
  last_updated: "2026-06-07"
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

### Operation: Create Auto Scaling Group

#### Pre-flight

**Step 1: Check CLI**
```bash
aws --version
```
Log: `[OK] AWS CLI v2.x.x detected` or `[FAIL] AWS CLI not found. Install: uv pip install awscli`

**Step 2: Load & Verify Credentials**
```bash
aws sts get-caller-identity --output json
```

Log format:
```
[SKILL] Loading AWS credentials...
[OK]   AWS_DEFAULT_REGION={{env.AWS_DEFAULT_REGION}} (from env)
[OK]   Credential verification passed
[OK]   Identity: arn:aws:iam::{{env.AWS_ACCOUNT_ID}}:user/xxx
```

**Step 3: Verify Launch Template / Configuration exists**
```bash
# If using Launch Template
aws ec2 describe-launch-template-versions --launch-template-name {{user.lt_name}} --output json
# If using Launch Configuration
aws autoscaling describe-launch-configurations --launch-configuration-names {{user.lc_name}} --output json
```

**Step 4: Verify Subnets exist**
```bash
aws ec2 describe-subnets --subnet-ids {{user.subnet_ids}} --output json
```

| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `aws --version` | Install AWS CLI v2 |
| Credentials | `aws sts get-caller-identity` | HALT; guide to integration.md |
| Region | `AWS_DEFAULT_REGION` or `--region` | Set region |
| Launch Template | `aws ec2 describe-launch-template-versions` | HALT; create launch template first |
| Subnets | `aws ec2 describe-subnets` | HALT; verify subnet IDs |
| Quota | Describe ASGs to check count | HALT; request quota increase |

#### Execute — CLI (Primary)
```bash
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name "{{user.asg_name}}" \
  --launch-template "LaunchTemplateName={{user.lt_name}},Version={{user.lt_version}}" \
  --min-size {{user.min_size}} \
  --max-size {{user.max_size}} \
  --desired-capacity {{user.desired_capacity}} \
  --vpc-zone-identifier "{{user.subnet_ids}}" \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
import boto3
client = boto3.client('autoscaling', region_name='{{user.region}}')
response = client.create_auto_scaling_group(
    AutoScalingGroupName='{{user.asg_name}}',
    LaunchTemplate={
        'LaunchTemplateName': '{{user.lt_name}}',
        'Version': '{{user.lt_version}}'
    },
    MinSize={{user.min_size}},
    MaxSize={{user.max_size}},
    DesiredCapacity={{user.desired_capacity}},
    VPCZoneIdentifier='{{user.subnet_ids}}'
)
```

#### Validate
```bash
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names "{{user.asg_name}}" \
  --region "{{user.region}}" \
  --output json
```
Confirm: `{{output.asg_name}}` exists with `MinSize`, `MaxSize`, `DesiredCapacity` matching request.

#### Recover
| Error | Action |
|-------|--------|
| AlreadyExists | HALT — group with that name exists; use different name |
| InvalidParameter | Fix args per AWS API docs; retry once |
| ValidationError | Check launch template / subnet IDs; retry |
| QuotaExceeded | HALT — request quota increase |
| Throttling (429) | Backoff 0s → 2s → 4s; retry 3x |
| InternalError (5xx) | Retry 3x; then HALT |

### Operation: Delete Auto Scaling Group

**Safety Gate**: MUST obtain explicit user confirmation before deletion.

#### Pre-flight

**Step 1: Identify ASG and describe current state**
```bash
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names "{{user.asg_name}}" \
  --region "{{user.region}}" \
  --output json
```
Log instance count and current instances.

**Step 2: Check for attached LBs / Target Groups**
```bash
# List attached load balancers
aws autoscaling describe-load-balancers \
  --auto-scaling-group-name "{{user.asg_name}}" \
  --region "{{user.region}}" \
  --output json
# List attached target groups
aws autoscaling describe-load-balancer-target-groups \
  --auto-scaling-group-name "{{user.asg_name}}" \
  --region "{{user.region}}" \
  --output json
```

**Step 3: Human Confirmation**
```
[WARN] Destructive operation: DELETE {{user.asg_name}}
[WARN] Current state: MinSize={{min}}, MaxSize={{max}}, DesiredCapacity={{desired}}
[WARN] Instances: {{count}} running
[WARN] Attached LBs: {{lb_count}}  Target Groups: {{tg_count}}
Require user confirmation: confirm=DELETE {{user.asg_name}}
```

#### Execute — CLI (Primary)
```bash
# For empty ASG (MinSize=MaxSize=DesiredCapacity=0 first if needed)
aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name "{{user.asg_name}}" \
  --min-size 0 --max-size 0 --desired-capacity 0 \
  --region "{{user.region}}" \
  --output json
# Wait for instances to terminate, then delete
aws autoscaling delete-auto-scaling-group \
  --auto-scaling-group-name "{{user.asg_name}}" \
  --region "{{user.region}}" \
  --output json
# With force-delete (non-empty ASG with instances still running)
# aws autoscaling delete-auto-scaling-group \
#   --auto-scaling-group-name "{{user.asg_name}}" \
#   --force-delete \
#   --region "{{user.region}}" \
#   --output json
```

#### Execute — boto3 (Fallback)
```python
import boto3
client = boto3.client('autoscaling', region_name='{{user.region}}')
client.update_auto_scaling_group(
    AutoScalingGroupName='{{user.asg_name}}',
    MinSize=0, MaxSize=0, DesiredCapacity=0
)
# Wait for instances to terminate
waiter = client.get_waiter('group_not_exists')
waiter.wait(AutoScalingGroupNames=['{{user.asg_name}}'])
```

#### Validate
```bash
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names "{{user.asg_name}}" \
  --region "{{user.region}}" \
  --output json
```
Confirm: ASG no longer exists (empty `AutoScalingGroups` array).

#### Recover
| Error | Action |
|-------|--------|
| ScalingActivityInProgress | Wait for activity to finish; retry |
| ResourceInUse | Check if ASG has running instances; use `--force-delete` or scale to 0 first |
| NotFound | HALT — ASG does not exist |
| Throttling | Backoff; retry 3x |

### Operation: Update Auto Scaling Group

#### Pre-flight

**Step 1: Describe current state**
```bash
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names "{{user.asg_name}}" \
  --region "{{user.region}}" \
  --output json
```

#### Execute — CLI (Primary)
```bash
aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name "{{user.asg_name}}" \
  --min-size {{user.min_size}} \
  --max-size {{user.max_size}} \
  --desired-capacity {{user.desired_capacity}} \
  --region "{{user.region}}" \
  --output json
```

#### Validate
```bash
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names "{{user.asg_name}}" \
  --region "{{user.region}}" \
  --output json \
  | jq '.AutoScalingGroups[0] | {MinSize, MaxSize, DesiredCapacity}'
```

### Operation: Suspend / Resume Processes

#### Pre-flight
Describe ASG to list current suspended processes.

#### Execute
```bash
# Suspend a process (e.g., HealthCheck, ReplaceUnhealthy, AZRebalance)
aws autoscaling suspend-processes \
  --auto-scaling-group-name "{{user.asg_name}}" \
  --scaling-processes HealthCheck ReplaceUnhealthy \
  --region "{{user.region}}" \
  --output json

# Resume processes
aws autoscaling resume-processes \
  --auto-scaling-group-name "{{user.asg_name}}" \
  --scaling-processes HealthCheck ReplaceUnhealthy \
  --region "{{user.region}}" \
  --output json
```

### Operation: Create Scaling Policy

#### Pre-flight
Describe ASG to verify it exists.

#### Execute — CLI (Primary)
```bash
# Target Tracking Policy (recommended)
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name "{{user.asg_name}}" \
  --policy-name "{{user.policy_name}}" \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{ "TargetValue": 50.0, "PredefinedMetricSpecification": { "PredefinedMetricType": "ASGAverageCPUUtilization" } }' \
  --region "{{user.region}}" \
  --output json

# Step Scaling Policy
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name "{{user.asg_name}}" \
  --policy-name "{{user.policy_name}}" \
  --policy-type StepScaling \
  --adjustment-type ChangeInCapacity \
  --step-adjustments '[{"MetricIntervalLowerBound": 0, "ScalingAdjustment": 1}, {"MetricIntervalLowerBound": 20, "ScalingAdjustment": 2}]' \
  --region "{{user.region}}" \
  --output json
```

### Operation: Create Scheduled Action

#### Execute
```bash
aws autoscaling put-scheduled-update-group-action \
  --auto-scaling-group-name "{{user.asg_name}}" \
  --scheduled-action-name "{{user.scheduled_action_name}}" \
  --recurrence "0 9 * * 1-5" \
  --min-size {{user.min_size}} \
  --max-size {{user.max_size}} \
  --desired-capacity {{user.desired_capacity}} \
  --region "{{user.region}}" \
  --output json
```

### Operation: Instance Refresh

#### Pre-flight
Describe ASG for current state; verify no other refresh in progress.

#### Execute
```bash
aws autoscaling start-instance-refresh \
  --auto-scaling-group-name "{{user.asg_name}}" \
  --preferences '{"MinHealthyPercentage": 90, "InstanceWarmup": 300}' \
  --region "{{user.region}}" \
  --output json
```

#### Validate
```bash
aws autoscaling describe-instance-refreshes \
  --auto-scaling-group-name "{{user.asg_name}}" \
  --region "{{user.region}}" \
  --output json
```
Poll until `Status` is `Successful` or `Failed`.

### Operation: Attach / Detach Instances

**Safety Gate** (detach): MUST obtain explicit user confirmation.

#### Execute
```bash
# Attach instances
aws autoscaling attach-instances \
  --auto-scaling-group-name "{{user.asg_name}}" \
  --instance-ids "{{user.instance_id}}" \
  --region "{{user.region}}" \
  --output json

# Detach instances (with decrement)
aws autoscaling detach-instances \
  --auto-scaling-group-name "{{user.asg_name}}" \
  --instance-ids "{{user.instance_id}}" \
  --should-decrement-desired-capacity \
  --region "{{user.region}}" \
  --output json
```

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md)

## Quality Gate (GCL)

This skill implements the **Generator-Critic-Loop (GCL)** adversarial quality
gate for all destructive operations. Full specification:
[`aws-skill-generator/references/gcl-spec.md`](../../aws-skill-generator/references/gcl-spec.md).

### Rubric

5-dimension scoring (0 / 0.5 / 1) in [`references/rubric.md`](references/rubric.md):
**Correctness, Safety, Idempotency, Traceability, Spec Compliance**.

**Safety = 0 → ABORT immediately.**

### Per-operation gating

| Operation | GCL required | Notes |
|---|---|---|
| `delete-auto-scaling-group` | **required** | `--force-delete` guard; `confirm=DELETE <asg-name>` |
| `delete-launch-configuration` | **required** | `confirm=DELETE_LC <lc-name>` |
| `delete-policy` | **required** | `confirm=DELETE_POLICY <policy-name>` |
| `delete-scheduled-action` | **required** | `confirm=DELETE_SCHEDULE <action-name>` |
| `delete-lifecycle-hook` | **required** | `confirm=DELETE_HOOK <hook-name>` |
| `detach-instances` | **required** | `--should-decrement-desired-capacity` guard; `confirm=DETACH <instance-id>` |
| `detach-load-balancer-target-groups` | **required** | `confirm=DETACH_TG <tg-arn>` |
| `suspend-processes` | **recommended** | HealthCheck/ReplaceUnhealthy suspend is high-impact |
| `set-desired-capacity → 0` | **required** | Effectively terminates all instances |
| All other operations | **not required** | Create, describe, update (non-destructive), resume |

### Prompt templates

Generator, Critic, and Orchestrator skeletons in
[`references/prompt-templates.md`](references/prompt-templates.md).

### Trace path

`./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` (git-ignored).

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
Full flow only in SKILL.md.

**See**: `aws-skill-generator` SKILL.md §Token Efficiency Requirements for detailed examples.

## AIOps Delegate Contract

This skill is orchestrator-aware. When invoked by
`aws-aiops-orchestrator`, it MUST honor the delegate contract.

### Recognition

If the incoming prompt contains an `aiops_delegate:` block (see
[aws-aiops-orchestrator/references/delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md)),
parse and validate:

- `request_id` — non-empty string
- `parent_intent` — one of: health-check | rca | self-heal
  | cost-forecast | capacity-forecast | change-impact
  | compliance-scan | forensic
- `action_mode` — observe | recommend | auto-heal | manual
- `decision_tier` — AUTO_HEAL | AI_ASSIST | MANUAL
- `scope.resource_ids` — array (may be empty for discovery)

### Behavior rules

1. **Idempotency**: every write operation MUST accept an
   `idempotency_key` parameter. If the same key was executed within
   the last 24h, return the cached result with
   `aiops_context.status: "ok"` and
   `aiops_context.facts[*].deduplicated: true`.
2. **Confirmation gate**: any destructive operation (delete, terminate,
   deregister, detach, disable, rotate) MUST require a
   `confirmation_token`. If absent, refuse and return
   `aiops_context.status: "failed"` with summary
   `"confirmation_token required for destructive op"`.
3. **Decision tier respect**:
   - `decision_tier: MANUAL` — never execute writes; recommendations only.
   - `decision_tier: AI_ASSIST` — recommendations; execute only if
     `confirmation_token` is present.
   - `decision_tier: AUTO_HEAL` — execute non-destructive writes
     directly; destructive ones still require `confirmation_token`.
4. **Trace propagation**: every AWS CLI / boto3 call MUST include the
   `trace_id` from the delegate block in the User-Agent header
   (`User-Agent: aiops-orchestrator/<trace_id>`).
5. **Output format**: always include a final `aiops_context:` JSON
   block in the response, even on failure.

### Cross-reference

This skill participates in the orchestrator's runbook library. See
[aws-aiops-orchestrator/references/runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md)
for which runbooks invoke this skill.

