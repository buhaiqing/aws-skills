---
name: aws-ssm-ops
description: >-
  Use this skill when managing AWS SSM resources, executing remote commands via
  Run Command, starting interactive sessions via Session Manager, managing SSM
  documents, or checking command execution status; even if the user doesn't
  explicitly mention "SSM" but needs remote EC2 management without SSH access.
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, SSM Agent
  installed on target instances, network access to SSM endpoints.
metadata:
  author: aws
  version: "1.0.0"
  last_updated: "2026-05-15"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  destructive_ops_require_confirm: true
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_DEFAULT_REGION
  gcl:
    enabled: true
    class: required
    max_iter: 2
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: false
  orchestrator_aware: true
  orchestrator_compat: ">=0.1.0"
  delegate:
    accepts: ['health-check', 'self-heal', 'compliance-scan', 'change-impact']
    produces_facts: ['state', 'event', 'config']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---

# AWS Systems Manager (SSM) Operations Skill

## Common JSON Paths (Centralized)

```
# Send Command:              .Command.CommandId
# Get Invocation:            .{Status,ResponseCode,StandardOutputContent,StandardErrorContent}
# List Invocations:          .CommandInvocations[].{InstanceId,Status}
# Describe Instances:        .InstanceInformationList[].{InstanceId,PingStatus,PlatformType}
# Start Session:             .SessionId
# Cancel Command:            Empty (success)
```

## Overview

AWS Systems Manager (SSM) provides **remote command execution** and **session management** for EC2 instances without SSH access. This skill covers Run Command (batch execution), Session Manager (interactive shell), and Document management.

## Trigger & Scope

### SHOULD Use When
- User mentions "AWS SSM", "Systems Manager", "Run Command", "Session Manager"
- Task involves remote execution on EC2 instances without SSH
- Keywords: `send-command`, `run shell script`, `remote execute`, `interactive session`
- Managing SSM Documents (AWS-RunShellScript, AWS-RunPowerShellScript)
- Checking command execution status or invocation results

### SHOULD NOT Use When
- Billing/cost analysis → out of scope; use AWS Cost Explorer directly
- IAM role creation for SSM → delegate to: `aws-iam-ops`
- EC2 instance lifecycle (start/stop/terminate) → delegate to: `aws-ec2-ops`
- VPC endpoint creation → delegate to: `aws-vpc-ops`

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{user.instance_ids}}` | User input | Ask once; comma-separated list |
| `{{user.commands}}` | User input | Ask once; array of shell commands |
| `{{user.document_name}}` | User input | Default: `AWS-RunShellScript` |
| `{{output.command_id}}` | Last API response | Parse `.Command.CommandId` |

## Execution Flow Pattern

Every operation follows **Pre-flight → Execute → Validate → Recover**:

1. **Pre-flight**: `aws --version` + `aws sts get-caller-identity --region {{user.region}} --output json`
2. **Execute**: CLI primary (`--output json`); boto3 fallback after 3 CLI failures
3. **Validate**: `list-command-invocations` / `describe-instance-information` to confirm
4. **Recover**: See Common Recovery table below

## Shared Patterns

**boto3 fallback**: See [references/boto3-sdk-usage.md](references/boto3-sdk-usage.md) → matching section.

**Output**: All commands use `--region {{user.region}} --output json` (omitted in some snippets).

**Common Recovery**:
| Error | Action |
|-------|--------|
| InvalidInstanceId | Verify instance ID; check SSM Agent status |
| DocumentNotFound | Use valid document name; list with `aws ssm list-documents` |
| ThrottlingException | Backoff 10s; retry 3x |
| InternalServerError | Retry 3x; then HALT |
| AgentNotInstalled | WARN; install SSM Agent manually |

## Operations

### OP: Send Command
```bash
aws ssm send-command \
  --instance-ids "{{user.instance_ids}}" \
  --document-name "{{user.document_name}}" \
  --parameters commands="{{user.commands}}"
```

Validate: Poll `list-command-invocations --command-id {{output.command_id}} --details` every 5s, max 300s. Terminal states: `Success`, `Failed`, `Cancelled`, `TimedOut`.

### OP: Get Invocation Result
```bash
aws ssm get-command-invocation \
  --command-id "{{output.command_id}}" \
  --instance-id "{{user.instance_id}}"
```

### OP: List Managed Instances
```bash
aws ssm describe-instance-information \
  --filters key=InstanceIds,value="{{user.instance_ids}}"
```

### OP: Start Session
**Safety Gate**: Confirm with user before interactive session.
```bash
aws ssm start-session --target "{{user.instance_id}}"
```
Note: Requires `session-manager-plugin` installed locally for interactive terminal.

### OP: Cancel Command
**Safety Gate**: Confirm cancellation with user.
```bash
aws ssm cancel-command --command-id "{{output.command_id}}"
```

## SSM Documents Reference

| Document Name | Platform | Purpose |
|--------------|----------|---------|
| `AWS-RunShellScript` | Linux | Execute shell commands |
| `AWS-RunPowerShellScript` | Windows | Execute PowerShell |
| `AWS-UpdateSSMAgent` | All | Update SSM Agent |
| `AWS-InstallApplication` | All | Install packages |
| `AWS-ConfigurePackage` | All | Configure packages |

## Token Efficiency

All 6 TE rules applied (see `aws-skill-generator` SKILL.md §Token Efficiency Requirements). Key points:
- TE-1: No hardcoded document names/parameters — use `list-documents` / `describe-parameters`
- TE-2: Inline comments only in boto3 code (no docstrings)
- TE-3: Compact error tables throughout
- TE-4: JSON paths centralized in `## Common JSON Paths` block above
- TE-5: YAML anchors in `assets/example-config.yaml` where applicable
- TE-6: Flows only in SKILL.md (no duplicate in references/)

## Quality Gate (GCL)

> Phase 1 GCL rollout (2026-06-04, required). Every execution of
> `aws-ssm-ops` MUST be wrapped by the Generator-Critic-Loop defined in
> `aws-skill-generator/references/gcl-spec.md`.

| Setting | Value |
|---|---|
| Class | `required` |
| `max_iterations` | `2` |
| Rubric | `references/rubric.md` (v1) |
| Prompts | `references/prompt-templates.md` (v1) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |

Destructive ops requiring `{{user.safety_confirm}}` in trace:

- `send-command` — remote execution on EC2 instances; high blast radius; confirm `SEND_COMMAND <instance-ids>`
- `delete-parameter` — parameter stored data permanently lost; confirm `DELETE_PARAMETER <name>`
- `cancel-command` — terminates a running command; confirm with user
- `start-session` — interactive shell access; confirm with user

Relevant AWS rules from `gcl-spec.md` §8: A7 (region), A8 (InstanceId echoed from `describe-instance-information`), A9 (command output secrets masked), A10 (sts first command).

### See also

- `aws-skill-generator/references/gcl-spec.md` — full GCL specification
- `references/rubric.md` — this skill's 5-dimension rubric
- `references/prompt-templates.md` — G/C/O skeletons
- Top-level `AGENTS.md` §11 — rollout index and Per-Skill Defaults

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md)

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

