---
name: aws-secretsmanager-ops
description: >-
  Use when the user needs to create, manage, or rotate secrets in AWS Secrets
  Manager (distinct from SSM Parameter Store); store and retrieve sensitive
  information like database credentials, API keys, or OAuth tokens; configure
  automatic secret rotation with Lambda functions; manage cross-account secret
  access; or implement secure credential management for applications, even if they
  don't say "Secrets Manager" and instead say "store my database password
  securely", "manage API keys", "set up credential rotation", "configure secret
  access across accounts", or "handle sensitive configuration in AWS".
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to Secrets Manager endpoints.
metadata:
  author: aws
  version: "1.0.0"
  last_updated: "2026-07-31"
  runtime: Harness AI Agent
  type: base
  provides:
  - list-secrets
  cli_applicability: dual-path
  destructive_ops_require_confirm: true
  environment: [AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION]
  gcl:
    enabled: true
    class: required
    max_iter: 2
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: false
  cross_skill_deps:
    - aws-kms-ops
    - aws-iam-ops
    - aws-cloudtrail-ops
    - aws-lambda-ops
  orchestrator_aware: true
  orchestrator_compat: ">=0.10"
  delegate:
    accepts: ['compliance-scan', 'change-impact', 'self-heal']
    produces_facts: ['state', 'config']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---
# AWS Secrets Manager Ops Skill

## Common JSON Paths (Centralized)

```
CreateSecret: .{ARN,Name,VersionId}
GetSecretValue: .{ARN,Name,SecretString,SecretBinary,VersionId}
PutSecretValue: .{ARN,Name,VersionId}
DeleteSecret: .{ARN,Name,DeletionDate}
RestoreSecret: .{ARN,Name}
RotateSecret: .{ARN,Name,VersionId}
ReplicateSecret: .{ARN,Name,ReplicationStatus}
```

## Trigger & Scope

### SHOULD Use When
Use for Secrets Manager secrets, retrieval, rotation, cross-account access, credentials, passwords, or API keys.

### SHOULD NOT Use When
Parameter Store → `aws-ssm-ops`; KMS key operations → `aws-kms-ops`.

### Delegation
KMS → `aws-kms-ops`; Lambda → `aws-lambda-ops`; IAM → `aws-iam-ops`.

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{user.SecretId}}` | User input | Secret name or ARN |
| `{{user.SecretName}}` | User input | prod/db/password |
| `{{user.SecretString}}` | User input | Secret value (plain text) |
| `{{user.KmsKeyId}}` | User input | alias/aws/secretsmanager |

## Execution Flow

**Pre-flight**: `aws --version` + `aws sts get-caller-identity`. Check KMS key exists if custom key specified.

**CLI (primary)**: `aws secretsmanager [command] --region {{r.region}} --output json` — see [references/aws-cli-usage.md](references/aws-cli-usage.md).

**boto3 (fallback)**: After 3 CLI failures, switch to SDK — see [references/boto3-sdk-usage.md](references/boto3-sdk-usage.md).

**Validate**: Use `get-secret-value` to confirm create/update. For delete, verify DeletionDate is set.

**Common Recovery**:
| Error | Action |
|-------|--------|
| ResourceNotFoundException (404) | HALT — verify secret name/ARN |
| InvalidRequestException | HALT — operation not allowed in current state |
| EncryptionFailure | FIX — check KMS key permissions |
| Throttling (429) | Backoff, retry 3x |
| InternalServiceError (5xx) | Retry 3x; HALT |

## Safety Gates

### Secret Deletion
```
⚠️ Deleting {{user.SecretName}} will remove all versions. Default recovery window: 30 days.
Use --force-delete-without-recovery for immediate deletion (no recovery).
Confirm: `confirm=DELETE_SECRET {{user.SecretName}}` (or `confirm=FORCE_DELETE_SECRET {{user.SecretName}}` for immediate deletion).
```

## Token Efficiency
TE-1…TE-6 apply; query live secret metadata, keep SDK examples comment-only, centralize JSON paths above, use asset anchors, and keep flows single-sourced.

## Quality Gate (GCL)
Required GCL, `max_iter=2`, rubric `references/rubric.md`, prompts `references/prompt-templates.md`; persist traces under `./audit-results/`. Confirm `confirm=DELETE_SECRET <name>` before deletion, `confirm=FORCE_DELETE_SECRET <name>` for immediate deletion, and confirm before `put-secret-value`; apply A7–A10, with SecretString/Binary always masked.

## Reference Files
[aws-cli-usage.md](references/aws-cli-usage.md) · [boto3-sdk-usage.md](references/boto3-sdk-usage.md) · [core-concepts.md](references/core-concepts.md) · [troubleshooting.md](references/troubleshooting.md) · [integration.md](../aws-skill-generator/references/integration.md)

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md): parse `aiops_delegate`; deduplicate writes by `idempotency_key` for 24h; require `confirmation_token` for destructive ops; `MANUAL` never writes, `AI_ASSIST` writes only with token, `AUTO_HEAL` permits non-destructive writes; propagate `trace_id` as `User-Agent: aiops-orchestrator/<trace_id>` and always emit `aiops_context` JSON. Never expose secret values. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).
