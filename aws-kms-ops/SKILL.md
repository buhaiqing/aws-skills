---
name: aws-kms-ops
description: >-
  Use when the user needs to create, manage, or rotate AWS KMS encryption keys;
  encrypt and decrypt data using AWS-managed keys; configure key policies,
  grants, or aliases; enable automatic key rotation; schedule or cancel key
  deletion; implement envelope encryption with data keys; perform encryption
  health audits across AWS services; diagnose key issues with root cause
  analysis; enable self-healing for key compliance; or integrate SSE-KMS with
  other AWS services. Keywords: KMS, encryption key, data key, CMK, envelope
  encryption, key rotation, key policy, grant, alias, key health audit,
  encryption compliance.
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to KMS and CloudWatch endpoints.
metadata:
  author: aws
  version: "2.1.0"
  last_updated: "2026-06-04"
  runtime: Harness AI Agent
  type: base
  provides:
  - list-keys
  cli_applicability: dual-path
  gcl:
    enabled: true
    class: required
    max_iter: 2
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: true
  destructive_ops_require_confirm: true
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_DEFAULT_REGION
    - AWS_SESSION_TOKEN
    - AWS_PROFILE
    - AWS_ACCOUNT_ID
  orchestrator_aware: true
  orchestrator_compat: ">=0.10"
  delegate:
    accepts: ['compliance-scan', 'change-impact']
    produces_facts: ['state', 'event']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---
# AWS KMS Operations Skill

Use for KMS keys, aliases, rotation, grants, encryption/decryption, imported material, custom key stores, policy review, and compliance. Detailed CLI/SDK patterns remain in references.

## Common JSON Paths

Keys: .Keys[].{KeyId,KeyArn,KeyState,KeyUsage,KeySpec}
Key: .{KeyId,Arn,KeyState,KeyManager,KeyUsage,KeySpec,Enabled,KeyRotationEnabled}
Aliases: .Aliases[].{AliasName,TargetKeyId}
Grants: .Grants[].{GrantId,KeyId,GranteePrincipal,Operations}

## Trigger & Scope

### SHOULD Use When
KMS keys/aliases, rotation, grants, encrypt/decrypt, key policy, imported material, custom key stores, or encryption audits.

### SHOULD NOT Use When
Secrets Manager secret lifecycle → `aws-secretsmanager-ops`; IAM users/policies → `aws-iam-ops`; S3 encryption config → `aws-s3-ops`.

## Variable Convention

| Placeholder | Source | Use |
|---|---|---|
| `{{env.AWS_*}}` | Runtime env | Never ask; fail closed if unset |
| `{{user.key_id}}`, `{{user.alias_name}}`, `{{user.grant_id}}` | User input | Key/grant identity |
| `{{user.pending_window_days}}`, `{{user.ciphertext}}` | User input | Deletion/encryption payload |
| `{{output.*}}` | API response | Reuse key ARN/state/grant IDs |

## Execution Flow

Every operation follows **Pre-flight → Execute → Validate → Recover**. Run STS first; verify key state, aliases, grants, policy principals, encryption context, dependent resources, and region. Use CLI `--output json`, then boto3 after 3 CLI failures. Read back key/grant state; recover with bounded retries and halt on disabled/pending-deletion or ambiguous key IDs. Never log plaintext, `Plaintext`, `CiphertextBlob`, passwords, or key material.

## Operations and Safety

| Operation | Pre-flight / validation | Confirmation |
|---|---|---|
| Create/alias/rotate key | Validate usage/spec/policy and aliases | — |
| Encrypt/decrypt/data key | Verify context and destination; mask output | Token for side-effecting use |
| Disable key | Show dependent resources and outage impact | Human confirmation |
| Schedule key deletion | Inspect grants/dependencies; pending window ≥7 days | `PERMANENTLY DELETE <key-id>` |
| Delete imported material/custom key store | Verify key type, enabled CMKs, and recovery impossibility | Resource-bound confirmation |
| Update key policy/grants | Diff principals/operations; reject wildcard broadening | Human/public-access confirmation |

AUTO_HEAL may rotate or report compliance, never schedule deletion, disable a key, or widen policy.

## Quality Gate (GCL)

Required GCL, `max_iter=2`, rubric `references/rubric.md`, prompts `references/prompt-templates.md`; persist traces under `./audit-results/`. Apply A4 (deletion window), A7–A10, and plaintext masking; Safety=0 aborts.

## Token Efficiency

TE-1…TE-6 apply; query live key/grant state, keep SDK examples comment-only, centralize JSON paths above, use asset anchors, and keep flows single-sourced.

## Reference Files

[aws-cli-usage.md](references/aws-cli-usage.md) · [boto3-sdk-usage.md](references/boto3-sdk-usage.md) · [core-concepts.md](references/core-concepts.md) · [troubleshooting.md](references/troubleshooting.md) · [rubric.md](references/rubric.md) · [prompt-templates.md](references/prompt-templates.md)

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md): parse `aiops_delegate`; deduplicate writes by `idempotency_key` for 24h; require `confirmation_token` for destructive/key-policy actions; `MANUAL` never writes, `AI_ASSIST` writes only with token, `AUTO_HEAL` permits rotation/compliance only; propagate `trace_id` as `User-Agent: aiops-orchestrator/<trace_id>` and always emit `aiops_context` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).

