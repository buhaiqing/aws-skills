---
name: aws-security-copilot
description: >-
  Unified SecOps entry point. Collects findings from GuardDuty, Security Hub,
  Config, IAM Access Analyzer, Secrets Manager, KMS, and CloudTrail; merges
  into a security posture summary; prioritizes by severity; routes to the
  appropriate remediation skill. Orchestrates only; delegates to base skills.
license: MIT
compatibility: >-
  AWS CLI v2, valid credentials, network access; delegates to
  aws-guardduty-ops, aws-securityhub-ops, aws-config-ops, aws-iam-ops,
  aws-secretsmanager-ops, aws-kms-ops, aws-cloudtrail-ops.
metadata:
  author: aws
  version: "0.1.0"
  status: "design-draft"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible
  type: composite
  provides:
    - security-posture-summary
    - finding-investigation
    - incident-response
    - compliance-check
  delegate:
    aws-guardduty-ops: [list-findings, get-findings]
    aws-securityhub-ops: [get-findings, get-insights]
    aws-config-ops: [get-compliance-summary]
    aws-iam-ops: [access-analyzer-findings]
    aws-secretsmanager-ops: [list-secrets]
    aws-kms-ops: [list-keys]
    aws-cloudtrail-ops: [lookup-events]
  cross_skill_deps: [aws-guardduty-ops, aws-securityhub-ops, aws-config-ops, aws-iam-ops, aws-secretsmanager-ops, aws-kms-ops, aws-cloudtrail-ops]
  gcl:
    enabled: true
    class: recommended
    max_iter: 3
---

# AWS Security Copilot (Composite L2 Skill)

## Trigger & Scope

**SHOULD Use When**: Cross-service security posture ("any critical findings?"), GuardDuty/SecurityHub finding investigation, compliance scan, IAM policy analysis, secrets/KMS/CloudTrail audit.

**SHOULD NOT Use When**: Direct service mutations (create/modify/delete) → use the base `aws-<svc>-ops`. User already named a specific base skill → load it directly.

## Execution Flow Pattern

1. **Collect** → Query GuardDuty (HIGH/CRITICAL), SecurityHub (severity filter), Config (compliance rate), IAM Access Analyzer, Secrets Manager (age), KMS (rotation), CloudTrail (recent events).
2. **Merge** → Merge all findings into unified `security_posture` JSON.
3. **Prioritize** → Apply [`references/findings-matrix.md`](references/findings-matrix.md) severity matrix (≥10 types).
4. **Route** → CRITICAL findings → HALT + alert; HIGH/MEDIUM → delegate to base skill remediation.

## Cross-Skill References

| Operation | Delegated skill | Notes |
|-----------|-----------------|-------|
| GuardDuty findings | `aws-guardduty-ops` | HIGH/CRITICAL severity filter |
| Security Hub findings | `aws-securityhub-ops` | Product + severity filter |
| Config compliance | `aws-config-ops` | Rule compliance summary |
| IAM Access Analyzer | `aws-iam-ops` | Policy findings |
| Secrets / KMS / CloudTrail | base skills | See playbook-routes |

See [`references/playbook-routes.md`](references/playbook-routes.md) for Finding → Remediation routing.

## Output Schema

```json
{
  "security_posture": {
    "guardduty": {"critical": 0, "high": 0, "last_updated": "ISO8601"},
    "securityhub": {"critical": 0, "high": 0},
    "config_compliance": {"compliant": 0, "non_compliant": 0, "rate": "P%"},
    "overall_score": "A|B|C|D|F"
  },
  "findings": [{ /* incident-schema per references/incident-schema.md */ }]
}
```

## Quality Gate (GCL)

| Dimension | Threshold | Notes |
|-----------|-----------|-------|
| Correctness | ≥ 0.5 | Delegation targets exist; findings routed correctly |
| Safety | = 1 | CRITICAL findings → HALT before auto-remediation |
| Idempotency | ≥ 0.8 | Same request → same posture summary |
| Traceability | ≥ 0.8 | `run_id`, delegation decisions logged |
| Spec Compliance | ≥ 0.8 | Layering contract + Charter C7 |

GCL: **recommended**, `max_iter=3`. Prompts: [`references/prompt-templates.md`](references/prompt-templates.md). Rubric: [`references/rubric.md`](references/rubric.md).

> CRITICAL findings → **HALT** + alert; require explicit user confirmation before any remediation.
