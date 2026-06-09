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
  last_updated: "2026-06-08"
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
  orchestrator_aware: true
  orchestrator_compat: ">=0.1.0"
  delegate:
    accepts: ['health-check', 'compliance-scan']
    produces_facts: ['finding']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---

AWS Security Hub operational skill for AI Agent automation.

## Trigger & Scope

### SHOULD Use When
- User mentions "Security Hub", "security findings", "security score"
- User requests enabling/disabling Security Hub in an account or Organization
- User asks to create, update, or delete insights or action targets
- User needs to manage security standards (CIS, PCI DSS, NIST, etc.) or controls
- User wants to import, update, or batch-update findings
- User asks about product subscriptions or disabling import for a product
- User requests automation rules (create, update, delete, list)
- User needs configuration policies for Organizations
- Keywords: security hub, findings, compliance, standards, controls, insight,
  action target, automation rule, security score, configuration policy

### SHOULD NOT Use When
- IAM policies → delegate to: `aws-iam-ops`
- GuardDuty findings → delegate to: `aws-guardduty-ops`
- KMS encryption keys → delegate to: `aws-kms-ops`
- EventBridge for automated response → delegate to: `aws-eventbridge-ops`
- Config compliance rules → delegate to: `aws-config-ops`

### Delegation
- IAM roles/policies → `aws-iam-ops` | KMS keys → `aws-kms-ops`
- EventBridge rules → `aws-eventbridge-ops` | SNS topics → `aws-sns-ops`
- Config recorders/rules → `aws-config-ops`

## Scope

| Operation | Safety Gate |
|-----------|-------------|
| Enable Security Hub | None |
| Describe Hub | None |
| Disable Security Hub | **Human confirm** |
| Create/Update/Delete Insight | Delete: **Human confirm** |
| Create/Describe/List/Delete Action Target | Delete: **Human confirm** |
| Batch Import Findings | None |
| Batch Update Findings | None |
| Get Findings | None |
| Enable/Disable Standard | None |
| Enable/Disable Control | None |
| Enable/Disable Import Findings for Product | Disable: **Human confirm** |
| Create/Update/Delete/List Automation Rule | Delete: **Human confirm** |
| Configuration Policy (Orgs) | Create/Update/Delete: **Human confirm** |

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{user.region}}` | User input | Ask once; reuse |
| `{{user.insight_arn}}` | User input | Ask once; reuse |
| `{{user.action_target_arn}}` | User input | Ask once; reuse |
| `{{user.product_subscription_arn}}` | User input | Ask once; reuse |
| `{{user.standard_arn}}` | User input | e.g. `arn:aws:securityhub:::ruleset/cis-aws-foundations-benchmark/v/1.2.0` |
| `{{user.control_id}}` | User input | e.g. `CIS.1.1` |
| `{{user.automation_rule_arn}}` | User input | Ask once; reuse |
| `{{output.HubArn}}` | Last API response | Parse: `.HubArn` |
| `{{output.InsightArn}}` | Last API response | Parse: `.InsightArn` |
| `{{output.ActionTargetArn}}` | Last API response | Parse: `.ActionTargetArn` |

## Execution Flow

### Pre-flight
```bash
aws --version && aws sts get-caller-identity --output json
```
Log: `[OK] Region={{env.AWS_DEFAULT_REGION}} Credential verified. Identity: arn:aws:iam::{{env.AWS_ACCOUNT_ID}}:user/xxx`
On failure: `[FAIL] AWS credential verification failed. Action: Check .env`
```bash
aws securityhub describe-hub --region {{env.AWS_DEFAULT_REGION}} --output json
```
Log: `[OK] Security Hub status: {{output.SubscribedAt}}` or `[INFO] Security Hub not enabled`

### Execute (Primary: CLI)
See [references/aws-cli-usage.md](references/aws-cli-usage.md) for full command reference.

### Execute (Fallback: boto3)
After 3 CLI failures, switch to SDK — see [references/boto3-sdk-usage.md](references/boto3-sdk-usage.md).

### Validate
```
1. Poll: aws securityhub describe-hub
2. For insights: aws securityhub get-insights --insight-arns {{user.insight_arn}}
3. For action targets: aws securityhub describe-action-targets --action-target-arns {{user.action_target_arn}}
4. For standards: aws securityhub describe-standards-controls --standards-subscription-arn {{user.standard_arn}}
```

### Recover
| Error Type | Action |
|------------|--------|
| ResourceNotFoundException | HALT — verify ARN |
| InvalidAccessException | HALT — check IAM permissions |
| LimitExceededException | HALT — request quota increase |
| Throttling (429) | Exponential backoff, max 3 retries |
| 5xx Internal | Retry 3x; HALT |

## Safety Gates

### Disable Security Hub
```
BEFORE disable-security-hub:
1. Display: "Disabling Security Hub will stop all finding aggregation and security score calculation"
2. Ask: "Type 'DISABLE_SECURITY_HUB' to confirm"
3. Pre-flight: list all enabled standards and product subscriptions
```

### Delete Insight
```
BEFORE delete-insight:
1. Display: "Deleting insight {{user.insight_arn}}"
2. Ask: "Type 'DELETE_INSIGHT {{user.insight_arn}}' to confirm"
```

### Delete Action Target
```
BEFORE delete-action-target:
1. Display: "Deleting action target {{user.action_target_arn}}"
2. Ask: "Type 'DELETE_ACTION_TARGET {{user.action_target_arn}}' to confirm"
```

### Disable Import Findings for Product
```
BEFORE disable-import-findings-for-product:
1. Display: "Disabling import findings for product {{user.product_subscription_arn}}"
2. Ask: "Type 'DISABLE_PRODUCT {{user.product_subscription_arn}}' to confirm"
```

### Delete Automation Rule
```
BEFORE delete-automation-rule:
1. Display: "Deleting automation rule {{user.automation_rule_arn}}"
2. Ask: "Type 'DELETE_AUTOMATION_RULE {{user.automation_rule_arn}}' to confirm"
```

### Delete Configuration Policy
```
BEFORE delete-configuration-policy:
1. Display: "Deleting configuration policy {{user.policy_id}}"
2. Ask: "Type 'DELETE_POLICY {{user.policy_id}}' to confirm"
```

## Output Convention
All commands use `--output json`. Key JSON paths:
- Hub: `.HubArn`, `.SubscribedAt`, `.AutoEnableControls`
- Insights: `.Insights[].{Name,InsightArn,Filters}`
- Action Targets: `.ActionTargets[].{Name,ActionTargetArn,Description}`
- Findings: `.Findings[].{Id,Title,Severity,Compliance,Workflow,RecordState}`
- Standards: `.Standards[].{StandardsArn,Name,Enabled}`
- Controls: `.Controls[].{ControlId,Title,ControlStatus,ComplianceStatus}`

## Related Skills
- `aws-iam-ops` — IAM roles/policies | `aws-kms-ops` — Encryption
- `aws-eventbridge-ops` — Automated response | `aws-sns-ops` — Notifications
- `aws-config-ops` — Config compliance | `aws-guardduty-ops` — Threat detection

## Cross-Skill Orchestration
| Scenario | Chain |
|----------|-------|
| Security Finding Response | securityhub → eventbridge → sns (finding → automation → alert) |
| Compliance Audit | securityhub → config → iam (controls → rules → permissions) |
| Multi-Account Security | securityhub → guardduty (central findings aggregation) |

## Reference Files
- `references/aws-cli-usage.md` — CLI command reference
- `references/boto3-sdk-usage.md` — Python SDK patterns
- `references/core-concepts.md` — Security Hub architecture, concepts
- `references/troubleshooting.md` — Error codes, recovery procedures
- `references/rubric.md` — GCL 5-dimension rubric
- `references/prompt-templates.md` — GCL G/C/O skeletons
- `assets/example-config.yaml` — Configuration examples

## Quality Gate (GCL)

> Phase 1 GCL rollout (2026-06-08, required). Every execution of
> `aws-securityhub-ops` MUST be wrapped by the Generator-Critic-Loop defined in
> `aws-skill-generator/references/gcl-spec.md`.

| Setting | Value |
|---|---|
| Class | `required` |
| `max_iterations` | `2` |
| Rubric | `references/rubric.md` (v1) |
| Prompts | `references/prompt-templates.md` (v1) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |

Destructive ops requiring `{{user.safety_confirm}}` in trace
(exact format `confirm=<OPERATION> <resource>`):

- `delete-insight` — `confirm=DELETE_INSIGHT {{user.insight_arn}}`
- `delete-action-target` — `confirm=DELETE_ACTION_TARGET {{user.action_target_arn}}`
- `disable-security-hub` — `confirm=DISABLE_SECURITY_HUB`
- `disable-import-findings-for-product` — `confirm=DISABLE_PRODUCT {{user.product_subscription_arn}}`
- `delete-configuration-policy` — `confirm=DELETE_POLICY {{user.policy_id}}`
- `delete-automation-rule` — `confirm=DELETE_AUTOMATION_RULE {{user.automation_rule_arn}}`

Relevant AWS rules from `gcl-spec.md` §8: A7 (region), A8 (resource echo-back),
A10 (sts first command).

See `references/rubric.md` for the 5-dimension rubric and
`references/prompt-templates.md` for G/C/O skeletons.

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

