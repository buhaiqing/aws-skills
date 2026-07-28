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
  orchestrator_compat: ">=0.10"
  delegate:
    accepts: ['health-check', 'self-heal', 'compliance-scan', 'change-impact']
    produces_facts: ['state', 'event', 'config']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---

# AWS Systems Manager (SSM) Operations Skill

Use for SSM Run Command, Session Manager, managed instances, command status, and SSM documents without SSH. Detailed CLI/SDK patterns remain in references.

## Common JSON Paths

SendCommand: .Command.CommandId
GetInvocation: .{Status,ResponseCode,StandardOutputContent,StandardErrorContent}
ListInvocations: .CommandInvocations[].{InstanceId,Status}
ManagedInstances: .InstanceInformationList[].{InstanceId,PingStatus,PlatformType}
StartSession: .SessionId

## Trigger & Scope

### SHOULD Use When
SSM, Systems Manager, Run Command, Session Manager, remote EC2 execution, managed instances, or SSM documents.

### SHOULD NOT Use When
IAM roles → `aws-iam-ops`; EC2 lifecycle → `aws-ec2-ops`; VPC endpoints → `aws-vpc-ops`; billing → Cost Explorer.

## Variable Convention

| Placeholder | Source | Use |
|---|---|---|
| `{{env.AWS_*}}` | Runtime env | Never ask; fail closed if unset |
| `{{user.instance_ids}}`, `{{user.instance_id}}` | User input | Targets |
| `{{user.commands}}`, `{{user.document_name}}` | User input | Command payload/document |
| `{{output.command_id}}` | API response | Reuse `.Command.CommandId` |

## Execution Flow Pattern

Every operation follows **Pre-flight → Execute → Validate → Recover**. Run `aws --version` and `aws sts get-caller-identity --output json`; verify target IDs with `describe-instance-information`, agent reachability, document existence, and session plugin when needed. Use CLI `--output json`, then boto3 after 3 CLI failures. Poll invocation status to a terminal state; recover with bounded throttling retries and halt on invalid instances/documents. See [aws-cli-usage.md](references/aws-cli-usage.md), [boto3-sdk-usage.md](references/boto3-sdk-usage.md), and [troubleshooting.md](references/troubleshooting.md).

## Operations and Safety

| Operation | Pre-flight / validation | Confirmation |
|---|---|---|
| Send command | Echo targets, inspect command/document, poll each invocation | `SEND_COMMAND <instance-ids>` |
| Get/list invocation | Verify command and instance IDs; read-only | — |
| List managed instances | Read-only; validate PingStatus | — |
| Start session | Verify target and plugin; interactive shell access | Human confirmation |
| Cancel command | Verify command is running; validate cancelled state | Human confirmation |
| Delete parameter/document | Inspect dependencies and versions | `DELETE_PARAMETER <name>` or operation-specific token |

Mask secrets from command parameters, stdout, stderr, and traces. Never log credentials or session material.

## Quality Gate (GCL)

Required GCL, `max_iter=2`, rubric `references/rubric.md`, prompts `references/prompt-templates.md`; persist traces under `./audit-results/`. Apply A7 (region), A8 (instance echoed from describe), A9 (output secret masking), and A10 (STS first command).

## Token Efficiency

TE-1…TE-6 apply; discover documents/parameters live, keep SDK examples comment-only, centralize JSON paths above, use asset anchors, and keep flows single-sourced.

## Reference Files

[aws-cli-usage.md](references/aws-cli-usage.md) · [boto3-sdk-usage.md](references/boto3-sdk-usage.md) · [core-concepts.md](references/core-concepts.md) · [troubleshooting.md](references/troubleshooting.md) · [integration.md](references/integration.md) · [rubric.md](references/rubric.md) · [prompt-templates.md](references/prompt-templates.md)

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md): parse `aiops_delegate`; deduplicate writes by `idempotency_key` for 24h; require `confirmation_token` for remote/destructive actions; `MANUAL` never writes, `AI_ASSIST` writes only with token, `AUTO_HEAL` permits non-destructive writes; propagate `trace_id` as `User-Agent: aiops-orchestrator/<trace_id>` and always emit `aiops_context` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).
