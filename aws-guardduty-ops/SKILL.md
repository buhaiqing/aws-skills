---
name: aws-guardduty-ops
description: >-
  Use when operating AWS GuardDuty resources via AWS CLI or boto3 SDK;
  user mentions GuardDuty, GuardDuty detector, GuardDuty filter, GuardDuty IP set, GuardDuty threat intel set, or GuardDuty findings.
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to AWS endpoints.
metadata:
  author: aws
  version: "1.0.0"
  last_updated: "2026-07-31"
  runtime: Harness AI Agent
  type: base
  provides:
  - list-findings
  - get-findings
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
    - aws-cloudtrail-ops
    - aws-eventbridge-ops
    - aws-cloudwatch-ops
    - aws-s3-ops
  orchestrator_aware: true
  orchestrator_compat: ">=0.10"
  delegate:
    accepts: ['health-check', 'compliance-scan']
    produces_facts: ['finding']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---
# AWS GuardDuty Operations Skill

Use for GuardDuty detectors, findings, filters, IP/domain/threat lists, members, publishing, malware protection, and security response. Detailed commands remain in references.

## Common JSON Paths

Detector: .DetectorId
Findings: .FindingIds[]
Filters: .Findings[].{Id,Name,Action,Rank,FindingCriteria}
Members: .Members[].{AccountId,MemberId,RelationshipStatus}

## Trigger & Scope

### SHOULD Use When
GuardDuty detectors, findings, filters, threat lists, members, malware protection, publishing, or threat response.

### SHOULD NOT Use When
Security Hub → `aws-securityhub-ops`; Config → `aws-config-ops`; IAM/KMS/EventBridge → respective skills.

## Variable Convention

| Placeholder | Source | Use |
|---|---|---|
| `{{env.AWS_*}}` | Runtime env | Never ask; fail closed if unset |
| `{{user.detector_id}}`, `{{user.filter_name}}`, `{{user.resource_name}}` | User input | Detector/filter identity |
| `{{user.finding_ids}}`, `{{user.criteria}}` | User input | Findings/filter payload |
| `{{output.*}}` | API response | Reuse detector/finding/member IDs |

## Execution Flow

Every operation follows **Pre-flight → Execute → Validate → Recover**. Run `aws --version` and `aws sts get-caller-identity --output json`; verify detector, account/member scope, finding identity, criteria, and region. Use CLI `--output json`, then boto3 after 3 CLI failures. Read back findings/filter state; recover with bounded retries and halt on access, quota, or ambiguous IDs. See [aws-cli-usage.md](references/aws-cli-usage.md), [boto3-sdk-usage.md](references/boto3-sdk-usage.md), and [troubleshooting.md](references/troubleshooting.md).

## Operations and Safety

| Operation | Pre-flight / validation | Confirmation |
|---|---|---|
| Describe/list findings | Read-only; verify detector and filters | — |
| Create/update filter/list | Validate criteria and action/rank | Token for broad archive/suppression |
| Delete filter | Verify exact filter and findings impact | `confirm=DELETE_GUARDDUTY_FILTER <name>` |
| Disable/delete detector | Show account-wide detection impact and members | Human confirmation |
| Archive finding | Echo finding IDs and reason; preserve evidence | Token for bulk archive |
| Update threat/member/publishing | Diff scope and downstream response | Human confirmation for impact |

Mask finding evidence, IPs, credentials, and sensitive account metadata in traces.

## Quality Gate (GCL)

Required GCL, `max_iter=2`, rubric `references/rubric.md`, prompts `references/prompt-templates.md`; persist traces under `./audit-results/`. Apply A7–A10; Safety=0 aborts.

## Token Efficiency

TE-1…TE-6 apply; query live detector/member state, keep SDK examples comment-only, centralize JSON paths above, use asset anchors, and keep flows single-sourced.

## Reference Files

[aws-cli-usage.md](references/aws-cli-usage.md) · [boto3-sdk-usage.md](references/boto3-sdk-usage.md) · [core-concepts.md](references/core-concepts.md) · [troubleshooting.md](references/troubleshooting.md) · [rubric.md](references/rubric.md) · [prompt-templates.md](references/prompt-templates.md)

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md): parse `aiops_delegate`; deduplicate writes by `idempotency_key` for 24h; require `confirmation_token` for destructive/bulk finding actions; `MANUAL` never writes, `AI_ASSIST` writes only with token, `AUTO_HEAL` permits bounded finding updates; propagate `trace_id` as `User-Agent: aiops-orchestrator/<trace_id>` and always emit `aiops_context` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).

