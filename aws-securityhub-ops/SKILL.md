---
name: aws-securityhub-ops
description: >-
  Use when the user needs to enable, configure, or manage AWS Security Hub;
  create or delete insights, action targets, or automation rules; manage
  standards and controls; import or update findings; enable or disable product
  subscriptions; or work with Security Hub configuration policies in AWS
  Organizations. Keywords: Security Hub, security findings, compliance,
  security standards, CIS, PCI DSS, NIST, action target, insight, automation
  rule, security score, configuration policy.
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to Security Hub endpoints.
metadata:
  author: aws
  version: "1.0.0"
  last_updated: "2026-07-31"
  runtime: Harness AI Agent
  type: base
  provides:
  - get-findings
  - get-insights
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
  cross_skill_deps:
    - aws-guardduty-ops
    - aws-cloudtrail-ops
    - aws-config-ops
    - aws-cloudwatch-ops
    - aws-iam-ops
  orchestrator_aware: true
  orchestrator_compat: ">=0.10"
  delegate:
    accepts: ['health-check', 'compliance-scan']
    produces_facts: ['finding']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---

# AWS Security Hub Operations Skill

Use for Security Hub findings, standards, controls, insights, action targets, products, automation rules, configuration policies, aggregation, compliance, and response orchestration. Detailed commands remain in references.

## Common JSON Paths

Hub: .{HubArn,SubscribedAt,AutoEnableControls}
Insights: .Insights[].{Name,InsightArn,Filters}
Actions: .ActionTargets[].{Name,ActionTargetArn,Description}
Findings: .Findings[].{Id,Title,Severity,Compliance,Workflow,RecordState}
Standards: .Standards[].{StandardsArn,Name,Enabled}
Controls: .Controls[].{ControlId,Title,ControlStatus,ComplianceStatus}

## Trigger & Scope

### SHOULD Use When
Security Hub, findings, standards, controls, insights, action targets, product subscriptions, automation rules, policies, aggregation, or compliance posture.

### SHOULD NOT Use When
GuardDuty detector operations → `aws-guardduty-ops`; Config rules → `aws-config-ops`; IAM/KMS/EventBridge/SNS resources → respective skills.

### Delegation
Threat detection → `aws-guardduty-ops`; compliance evidence → `aws-config-ops`; response routing → `aws-eventbridge-ops`; notifications → `aws-sns-ops`.

## Variable Convention

| Placeholder | Source | Use |
|---|---|---|
| `{{env.AWS_*}}` | Runtime env | Never ask; fail closed if unset |
| `{{user.insight_arn}}`, `{{user.action_target_arn}}` | User input | Insight/action IDs |
| `{{user.product_subscription_arn}}`, `{{user.automation_rule_arn}}`, `{{user.policy_id}}` | User input | Product/rule/policy IDs |
| `{{output.*}}` | API response | Reuse hub, finding, standard, control identifiers |

## Execution Flow

Every operation follows **Pre-flight → Execute → Validate → Recover**. Run `aws --version` and `aws sts get-caller-identity --output json`; verify Hub state, enabled standards/products, delegated-admin/region scope, resource ARN, dependencies, and finding filters. Use CLI `--output json`, then boto3 after 3 CLI failures. Read back state/findings; recover with bounded throttling retries and halt on access, quota, or missing resources. See [aws-cli-usage.md](references/aws-cli-usage.md), [boto3-sdk-usage.md](references/boto3-sdk-usage.md), and [troubleshooting.md](references/troubleshooting.md).

## Operations and Safety

| Operation | Pre-flight / validation | Confirmation |
|---|---|---|
| Disable Security Hub | List enabled standards and products; show loss of aggregation/score | `confirm=DISABLE_SECURITY_HUB` |
| Delete insight | Describe ARN and filters | `confirm=DELETE_INSIGHT <arn>` |
| Delete action target | Inspect automations/users | `confirm=DELETE_ACTION_TARGET <arn>` |
| Disable product import | Inspect subscription and downstream findings | `confirm=DISABLE_PRODUCT <arn>` |
| Delete automation rule | Describe rule/actions/order | `confirm=DELETE_AUTOMATION_RULE <arn>` |
| Delete configuration policy | Inspect associations and affected accounts/OUs | `confirm=DELETE_POLICY <id>` |

Mask finding details that contain credentials, tokens, personal data, or sensitive resource metadata. AUTO_HEAL may update finding workflow only when policy permits; it must not disable controls or the Hub.

## Quality Gate (GCL)

Required GCL, `max_iter=2`, rubric `references/rubric.md`, prompts `references/prompt-templates.md`; persist traces under `./audit-results/`. Apply A7, A8, A9, A10; Safety=0 aborts.

## Token Efficiency

TE-1…TE-6 apply; query live standards/control IDs, keep SDK examples comment-only, centralize JSON paths above, use asset anchors, and keep flows single-sourced.

## Reference Files

[aws-cli-usage.md](references/aws-cli-usage.md) · [boto3-sdk-usage.md](references/boto3-sdk-usage.md) · [core-concepts.md](references/core-concepts.md) · [troubleshooting.md](references/troubleshooting.md) · [rubric.md](references/rubric.md) · [prompt-templates.md](references/prompt-templates.md) · [example-config.yaml](assets/example-config.yaml)

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md): parse `aiops_delegate`; deduplicate writes by `idempotency_key` for 24h; require `confirmation_token` for destructive/disable actions; `MANUAL` never writes, `AI_ASSIST` writes only with token, `AUTO_HEAL` permits policy-approved non-destructive finding updates; propagate `trace_id` as `User-Agent: aiops-orchestrator/<trace_id>` and always emit `aiops_context` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).
