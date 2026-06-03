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
  cli_applicability: dual-path
  gcl:
    enabled: true
    class: required
    max_iter: 2
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: true
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_DEFAULT_REGION
    - AWS_SESSION_TOKEN
    - AWS_PROFILE
    - AWS_ACCOUNT_ID
---
# AWS KMS Ops Skill

Operational runbook for AWS KMS — key lifecycle, encryption, grants, policies, and rotation.

## Common JSON Paths (Centralized)

```
# Create Key:      .KeyMetadata.{KeyId,KeyArn,KeyState}
# Describe Key:    .KeyMetadata.{KeyState,Enabled,KeyUsage,KeySpec,Description,CreationDate}
# List Keys:       .Keys[].{KeyId,KeyArn}
# Enable/Disable:  Empty (success)
# Schedule Delete: .{KeyId,DeletionDate}
# Encrypt:         .{CiphertextBlob,KeyId}
# Decrypt:         .{Plaintext,KeyId}
# Gen DataKey:     .{CiphertextBlob,Plaintext,KeyId}
# Create Alias:    Empty (success)
# Create Grant:    .{GrantToken,GrantId}
```

## Trigger & Scope

### SHOULD Use When
- User requests KMS key creation, rotation, or deletion
- User needs to enable/disable keys
- User asks about encryption key management
- User mentions "KMS", "encryption key", "data key", "CMK"
- User needs to configure key policies or grants
- User asks about automatic key rotation
- User needs to encrypt/decrypt data or generate data keys
- User mentions "SSE-KMS", "envelope encryption", "key hierarchy"

### SHOULD NOT Use When
- S3 bucket encryption → `aws-s3-ops`
- RDS encryption → `aws-rds-ops`
- EBS volume encryption → `aws-ec2-ops`
- Secrets Manager operations → `aws-secrets-manager-ops`

### Delegation
- IAM policy editing → `aws-iam-ops` (IAM policies for key access)
- S3 bucket ops → `aws-s3-ops` (bucket encryption config)
- RDS ops → `aws-rds-ops` (database encryption)
- CloudTrail ops → `aws-cloudtrail-ops` (trail encryption)

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default; allow override |
| `{{env.AWS_SESSION_TOKEN}}` | Runtime env | STS temp creds only |
| `{{env.AWS_PROFILE}}` | Runtime env | Overrides explicit keys |
| `{{env.AWS_ACCOUNT_ID}}` | Runtime env | Required for ARN construction |
| `{{u.region}}` | User input or env | Default `us-east-1` |
| `{{u.key_id}}` | User input | Key ID, ARN, or `alias/` prefix |
| `{{u.alias}}` | User input | Without `alias/` prefix |
| `{{u.desc}}` | User input | Description for key |
| `{{u.plaintext}}` | User input | Max 4KB for encrypt |
| `{{u.ciphertext}}` | User input | Base64 encoded ciphertext |
| `{{u.grantee}}` | User input | IAM role/user ARN |
| `{{o.*}}` | Last API response | Parse from JSON output |

## Config File Placeholders

`assets/example-config.yaml` uses `{{env.*}}` for environment values and `{{user.*}}` for resource-specific values:

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_DEFAULT_REGION}}` | `.env` or runtime env | Substitute before use |
| `{{env.AWS_ACCOUNT_ID}}` | `.env` or runtime env | Substitute before use |
| `{{user.AccountId}}` | User input | Ask once; substitute |

## FinOps Cost Awareness

| Cost Component | Price | Optimization Strategy |
|----------------|-------|----------------------|
| Customer managed keys | $1.00/key/month | Delete unused keys; use aliases instead of creating new keys |
| Symmetric API requests | $0.03/10,000 | Use data key caching; batch operations |
| Free tier | 20,000 requests/month | Monitor usage to stay within free tier |

### Cost Pre-flight
```bash
aws kms list-keys --region {{u.region}} --output json | jq '.Keys | length'
```
```
Keys(N): N keys = $N.00/month
Tip: Unused keys in Disabled state still incur monthly charge
```

### Cost Anomaly Detection
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/KMS \
  --metric-name ThrottledRequests \
  --statistics Sum --period 86400 \
  --start-time $(date -d '-30 days' -u +%Y-%m-%dT00:00:00Z) \
  --end-time $(date -u +%Y-%m-%dT00:00:00Z) \
  --region {{u.region}}
```

## Execution Flow

**Pre-flight**: `aws --version` + `aws sts get-caller-identity`. Verify region via `list-keys`, check quotas.

**CLI (primary)**: `aws kms [command] --region {{r.region}} --output json` — see [references/aws-cli-usage.md](references/aws-cli-usage.md).

**boto3 (fallback)**: After 3 CLI failures, switch to SDK — see [references/boto3-sdk-usage.md](references/boto3-sdk-usage.md).

**Validate**: Use `describe-key` to confirm state changes (Enabled/Disabled/PendingDeletion). Key operations are synchronous.

**Common Recovery**:
| Error | Action |
|-------|--------|
| AlreadyExistsException | HALT — key alias already exists |
| NotFoundException | HALT — key does not exist |
| DisabledException | FIX — enable key first |
| InvalidKeyState | HALT — key in invalid state |
| DependencyTimeoutException | RETRY max 3x |
| LimitExceededException | HALT — quota exceeded |
| Throttling (429) | Exponential backoff; max 3 retries |
| 5xx Internal | Retry 3x; then HALT |

## Safety Gates

### Key Deletion (CRITICAL)
```
⚠️ Deleting key {{u.key_id}} will PERMANENTLY destroy key material.
All data encrypted with this key will be UNRECOVERABLE.
Before proceeding:
1. List dependent services (S3, RDS, EBS, etc.)
2. Confirm backups exist with different keys
3. Use minimum 7-day pending window (default: 30 days)
Confirm: Type PERMANENTLY DELETE {{u.key_id}} to proceed.
```

### Key Disabling
```
⚠️ Disabling key will break encryption/decryption for dependent services.
List affected services first. Continue? (yes/no)
```

### Key Rotation
```
ℹ️ Rotation generates new key material. Old material preserved. Existing data remains usable.
```

## Operations

Every operation follows: **Pre-flight → Execute → Validate → Recover**

### OP: Create Key
`create-key` — Create symmetric or asymmetric encryption key.
```bash
aws kms create-key --description "{{u.desc}}" --key-usage ENCRYPT_DECRYPT --key-spec SYMMETRIC_DEFAULT
```
Pre-flight: Verify quota via `list-keys`. Validate: `describe-key` → KeyState=Enabled.

### OP: Rotate Key (Automatic)
`enable-key-rotation` — Enable annual automatic rotation for symmetric keys.
```bash
aws kms enable-key-rotation --key-id {{u.key_id}}
aws kms get-key-rotation-status --key-id {{u.key_id}}
```
Pre-flight: Verify key spec is SYMMETRIC_DEFAULT (asymmetric keys don't support auto-rotation).

### OP: Encrypt/Decrypt
`encrypt` / `decrypt` — Encrypt plaintext or decrypt ciphertext.
```bash
aws kms encrypt --key-id {{u.key_id}} --plaintext "{{u.plaintext}}" --encryption-context env=prod
aws kms decrypt --ciphertext-blob {{u.ciphertext}} --encryption-context env=prod
```
Pre-flight: Verify key is Enabled. **Note**: Encryption context must match exactly for decrypt.

### OP: Generate Data Key
`generate-data-key` — Create data key for envelope encryption.
```bash
aws kms generate-data-key --key-id {{u.key_id}} --key-spec AES_256
```
Returns: Plaintext key (use immediately, discard) + CiphertextBlob (store with encrypted data).

### OP: Diagnose Key Issue (RCA)
Systematic diagnosis when key operations fail.
```bash
# 1. Check key state
aws kms describe-key --key-id {{u.key_id}} --query "KeyMetadata.{State:KeyState,Enabled:Enabled}"
# 2. Check IAM permissions
aws iam simulate-principal-policy --policy-source-arn {{u.principal_arn}} --action-names kms:Decrypt --resource-arns arn:aws:kms:{{u.region}}:{{env.AWS_ACCOUNT_ID}}:key/{{u.key_id}}
# 3. Check CloudTrail for recent errors
aws cloudtrail lookup-events --lookup-attributes AttributeKey=ResourceName,AttributeValue={{u.key_id}} --start-time $(date -d '-24 hours' -u +%Y-%m-%dT%H:%M:%SZ)
```
**RCA Decision Matrix:**
| Symptom | Key State | Decision | SLA |
|---------|-----------|----------|-----|
| Decrypt fails | Disabled | [AUTO_HEAL] enable-key | P0 |
| Decrypt fails | PendingDeletion | [AUTO_HEAL] cancel-key-deletion | P0 |
| Access denied | Enabled | [MANUAL] Review IAM/Key Policy | P2 |
| Throttling | Enabled | [AI_ASSIST] Implement caching | P2 |
| Unused key (90d+) | Enabled | [AI_ASSIST] Review/delete idle key | P3 |
| Missing Env tags | Enabled | [AI_ASSIST] Apply standard tags | P3 |
| Orphaned aliases | N/A | [AI_ASSIST] Clean up stale alias | P3 |
| Grant count near limit | Enabled | [AI_ASSIST] Audit retired grants | P3 |
| Key description empty | Enabled | [AI_ASSIST] Document key purpose | P3 |

### OP: Rotation Compliance Scan
Scan all keys for rotation compliance.
```bash
for key_id in $(aws kms list-keys --query "Keys[].KeyId" --output text); do
  rotation=$(aws kms get-key-rotation-status --key-id $key_id --query "KeyRotationEnabled" --output text)
  spec=$(aws kms describe-key --key-id $key_id --query "KeyMetadata.KeySpec" --output text)
  [ "$rotation" = "False" ] && [ "$spec" = "SYMMETRIC_DEFAULT" ] && echo "WARN: $key_id rotation disabled"
done
```
Decision: [AUTO_HEAL] Enable rotation for symmetric keys in production.

### OP: Schedule Key Deletion (Destructive)
**Safety Gate**: Explicit confirmation required (see Safety Gates above).
```bash
aws kms schedule-key-deletion --key-id {{u.key_id}} --pending-window-in-days 30
```
Pre-flight: Identify dependent services. Validate: `describe-key` → DeletionDate set.

## Cross-Cutting Scenarios

### Encryption Health Audit (Cross-Skill)
Cross-service encryption compliance check.
```
Trigger: "帮我做一次全账户加密健康巡检"
Trigger: "Run comprehensive encryption audit"
```
Execution chain:
```
aws-kms-ops → Key rotation compliance, key states, grant audit
    ↓
aws-s3-ops  → Check SSE-KMS encryption on buckets
aws-rds-ops → Verify storage encryption enabled
aws-ec2-ops → Check EBS volume encryption
aws-lambda-ops → Verify environment variable encryption
```
Output: Compliance report with [AUTO_HEAL] / [AI_ASSIST] / [MANUAL] actions.

### Key Recovery Flow
```
1. Identify error type from CloudTrail/CLI error
2. Check key state with describe-key
3. For Disabled → [AUTO_HEAL] enable-key
4. For PendingDeletion → [AUTO_HEAL] cancel-key-deletion
5. For AccessDenied → [MANUAL] Review policies
6. For Throttling → [AI_ASSIST] Implement caching
7. Max 3 retries for transient errors
8. HALT for quota/permanent errors
```

### Security Monitoring
| Check | Method | Alert Threshold | Decision |
|-------|--------|-----------------|----------|
| Key disabled | CloudTrail: DisableKey | Any unexpected disable | [AUTO_HEAL] |
| Key deletion scheduled | CloudTrail: ScheduleKeyDeletion | Any unplanned deletion | [AUTO_HEAL] |
| Key policy changed | CloudTrail: PutKeyPolicy | Broad permission grant | [MANUAL] |
| API throttling | CloudWatch: ThrottledRequests | >1000/hour | [AI_ASSIST] |
| Unused keys | CloudTrail: No Decrypt in 90d | Zero usage | [AI_ASSIST] |

## Decision Types

| Type | Label | Meaning | Example |
|------|-------|---------|---------|
| Manual | `[MANUAL]` | AI identifies issue; human decides action | Key policy changes |
| AI Assist | `[AI_ASSIST]` | AI recommends; human confirms | Enable rotation on prod keys |
| Auto Heal | `[AUTO_HEAL]` | AI executes automatically | Re-enable accidentally disabled key |

### Auto-Heal Boundary Conditions
Auto-heal **downgrades** to AI_ASSIST or MANUAL when:
| Condition | Downgrade | Reason |
|-----------|-----------|--------|
| Data deletion involved | `[MANUAL]` | Irreversible |
| Cross-account operation | `[MANUAL]` | Authorization complexity |
| First-time error pattern | `[AI_ASSIST]` | No historical reference |
| Auto-heal failed 2x | `[MANUAL]` | Prevent cascade failure |

## Related Skills

- `aws-iam-ops` - IAM policies for key access control
- `aws-s3-ops` - S3 SSE-KMS encryption
- `aws-rds-ops` - RDS storage encryption
- `aws-ec2-ops` - EBS volume encryption
- `aws-cloudtrail-ops` - Trail encryption
- `aws-lambda-ops` - Lambda env var encryption
- `aws-secrets-manager-ops` - Secrets encryption

## Reference Files

- [Prompt Examples](references/prompt-examples.md) — Concrete user prompts for KMS operations
- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](../aws-skill-generator/references/integration.md)
## Quality Gate (GCL)

> This skill is the **Phase 1 GCL pilot** (2026-06-04, third rollout after
> `aws-ec2-ops` and `aws-iam-ops`). Every execution of `aws-kms-ops` MUST
> be wrapped by the Generator-Critic-Loop defined in
> `aws-skill-generator/references/gcl-spec.md`.

| Setting | Value | Source |
|---|---|---|
| Class | `required` | `gcl-spec.md` §10 (pilot) |
| `max_iterations` | `2` | `gcl-spec.md` §10 (Phase 1 default) |
| Rubric | `references/rubric.md` (v1) | this skill |
| Prompts | `references/prompt-templates.md` (v1) | this skill |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | `gcl-spec.md` §6 |

### Per-operation gating

The Orchestrator applies GCL on every execution. The following operations
are **destructive** and require `{{user.safety_confirm}}` in the trace
(exact format `confirm=<OPERATION> <resource-id>`):

- `schedule-key-deletion` — **IRREVERSIBLE**; user must type
  `PERMANENTLY DELETE <key-id-or-arn>` to proceed (per Safety Gate above)
- `cancel-key-deletion` — recovers a key in `PendingDeletion` state; high
  blast radius, confirm
- `disable-key` — can be auto-healed later; still requires confirmation
  when triggered by an explicit user request (not by [AUTO_HEAL])
- `delete-imported-key-material` — for asymmetric CMKs with imported
  material; cannot be recovered after delete
- `delete-custom-key-store` — destroys the entire custom key store
- `put-key-policy` — when the new policy widens permissions (added
  `Allow` statements or removed `Deny`); treat as destructive
- `revoke-grant` — when the grant is the only path for a dependent
  service; pre-flight required
- `retire-grant` — same as revoke for active grants

Non-destructive operations (`create-key`, `create-alias`, `enable-key`,
`enable-key-rotation`, `encrypt`, `decrypt`, `generate-data-key`,
`describe-key`, `list-keys`, `list-grants`, `list-aliases`) still flow
through GCL with `Safety` scored against routine guard rules only.

### AWS-specific rules in force

This skill's rubric instantiates the repo-wide AWS rules from
`gcl-spec.md` §8. The ones most relevant to KMS:

- **A4** — `schedule-key-deletion` with `--pending-window-in-days < 7`
  → **Safety = 0 → ABORT**. AWS enforces the floor; rubric demands
  user-confirmed intent before the call is even attempted.
- **A9** — `Plaintext` (from `decrypt` / `generate-data-key`),
  `CiphertextBlob` values, or any value of `{{env.AWS_SECRET_ACCESS_KEY}}`
  MUST NOT appear in the trace. Mask to `***<len>` only.
- **A10** — `aws sts get-caller-identity` MUST be the first command in
  trace to capture identity provenance.
- **A7** — `--region` must match `{{user.region}}` or
  `{{env.AWS_DEFAULT_REGION}}`. KMS keys are regional; cross-region
  alias is not allowed.
- **A8** — `KeyId` / `Alias` / `GrantId` in the request MUST be echoed
  from a `describe-key` / `list-aliases` / `list-grants` lookup.

### See also

- `aws-skill-generator/references/gcl-spec.md` — full GCL specification
- `references/rubric.md` — this skill's 5-dimension rubric + KMS safety
  special cases (irreversible `schedule-key-deletion`, plaintext
  never logged, custom key store destruction, widening `put-key-policy`)
- `references/prompt-templates.md` — Generator / Critic / Orchestrator
  skeletons
- Top-level `AGENTS.md` §11 — rollout index and Per-Skill Defaults
