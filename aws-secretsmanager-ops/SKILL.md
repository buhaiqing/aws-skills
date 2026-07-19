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
    accepts: ['compliance-scan', 'change-impact', 'self-heal']
    produces_facts: ['state', 'config']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---
# AWS Secrets Manager Ops Skill

## Common JSON Paths (Centralized)

```
# Create Secret:     .{ARN,Name,VersionId}
# Get Secret Value:  .{ARN,Name,SecretString,SecretBinary,VersionId}
# Put Secret Value:  .{ARN,Name,VersionId}
# Delete Secret:     .{ARN,Name,DeletionDate}
# Restore Secret:    .{ARN,Name}
# Rotate Secret:     .{ARN,Name,VersionId}
# Replicate Secret:  .{ARN,Name,ReplicationStatus}
```

## Trigger & Scope

### SHOULD Use When
- User requests secret creation, rotation, or deletion
- User needs to retrieve secret values
- User asks about Secrets Manager
- User needs to configure automatic rotation
- User mentions "secret", "credential", "password", "API key"
- User needs cross-account secret access

### SHOULD NOT Use When
- Parameter Store operations → delegate to: `aws-ssm-ops`
- KMS key operations → delegate to: `aws-kms-ops`

### Delegation
- KMS → `aws-kms-ops` (encryption key)
- Lambda → `aws-lambda-ops` (rotation function)
- IAM → `aws-iam-ops` (access policies)

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
Confirm: Type DELETE {{user.SecretName}} to proceed.
```

## Related Skills

- `aws-kms-ops` — Encryption key management
- `aws-lambda-ops` — Rotation function
- `aws-iam-ops` — Access policies

## Token Efficiency

All 6 TE rules applied (see `aws-skill-generator` SKILL.md §Token Efficiency Requirements). Key points:
- TE-1: No hardcoded secret types/limits — use `list-secrets` / `describe-secret`
- TE-2: Inline comments only in boto3 code (no docstrings)
- TE-3: Compact error tables throughout
- TE-4: JSON paths centralized in `## Common JSON Paths` block above
- TE-5: YAML anchors in `assets/example-config.yaml` where applicable
- TE-6: Flows only in SKILL.md (no duplicate in references/)

## Quality Gate (GCL)

> Phase 1 GCL rollout (2026-06-04, required). Every execution of
> `aws-secretsmanager-ops` MUST be wrapped by the Generator-Critic-Loop
> defined in `aws-skill-generator/references/gcl-spec.md`.

| Setting | Value |
|---|---|
| Class | `required` |
| `max_iterations` | `2` |
| Rubric | `references/rubric.md` (v1) |
| Prompts | `references/prompt-templates.md` (v1) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |

Destructive ops requiring `{{user.safety_confirm}}` in trace:

- `delete-secret` — IRREVERSIBLE after recovery window (30 days default). `--force-delete-without-recovery` is immediate — requires `confirm=FORCE_DELETE_SECRET <name>`
- `put-secret-value` — overwrites version; confirm with user

Relevant AWS rules from `gcl-spec.md` §8: A7 (region), A8 (SecretId echoed from `describe-secret` / `list-secrets`), **A9 (SecretString/Binary NEVER in trace — masked to `***<len>` only — this is the most critical rule for this skill)**, A10 (sts first command).

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
- [Integration Setup](../aws-skill-generator/references/integration.md)

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

