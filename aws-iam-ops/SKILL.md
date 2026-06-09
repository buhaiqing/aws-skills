---
name: aws-iam-ops
description: >-
  Use when the user needs to create, manage, or delete AWS IAM identities
  including users, groups, roles, and policies; configure access permissions
  and trust relationships; generate or rotate access keys; set up federated
  access or SSO; or attach/detach managed policies to AWS identities, even
  if they don't say "IAM" and instead say "set up user access in AWS", "create
  a service role for AWS", "configure AWS permissions", "grant cross-account
  access", or "attach policies to an IAM role".
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to IAM endpoints.
metadata:
  author: aws
  version: "1.1.0"
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
  orchestrator_aware: true
  orchestrator_compat: ">=0.1.0"
  delegate:
    accepts: ['compliance-scan', 'change-impact']
    produces_facts: ['state', 'event']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---

# AWS IAM Operations Skill

## Common JSON Paths (Centralized)

```
# Create:  .User.{UserId,Arn,CreateDate}  /  .Role.{RoleId,Arn,CreateDate}  /  .Group.{GroupId,Arn}
#          .Policy.{PolicyId,Arn}  /  .AccessKey.{AccessKeyId,SecretAccessKey,Status}
# Describe: .User / .Role / .Group / .Policy
# List:     .Users[]  /  .Roles[]  /  .Groups[]  /  .Policies[]  /  .AccessKeyMetadata[]
```

## Overview

AWS IAM (Identity and Access Management) securely controls access to AWS resources. Manage authentication (who can sign in) and authorization (what permissions they have). This skill is an **operational runbook** for IAM identity and policy operations.

## Trigger & Scope

### SHOULD Use When
- User mentions "IAM", "Identity", "Access Management", "permissions"
- Task involves **users, groups, roles, policies** (create, list, attach, delete)
- Keywords: user, group, role, policy, permission, trust-policy, access-key

### SHOULD NOT Use When
- EC2 instance ops → delegate to: `aws-ec2-ops`
- S3 bucket ops → delegate to: `aws-s3-ops`
- Billing → delegate to: `aws-cost-ops`
- Security audit/compliance → specialized security skill (if exists)

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | IAM is global; region for STS only |
| `{{user.user_name}}` | User input | Ask once; reuse |
| `{{user.role_name}}` | User input | Ask once; reuse |
| `{{output.arn}}` | Last API response | Parse: `.User.Arn` or `.Role.Arn` |

## Execution Flow Pattern

Every operation: **Pre-flight → Execute → Validate → Recover**

```
Pre-flight → Execute (CLI/SDK) → Validate → Recover (On Error)
```

### Operation: Create User

#### Pre-flight

**Step 1: Check CLI**
```bash
aws --version
```
Log: `[OK] AWS CLI v2.x.x detected` or `[FAIL] AWS CLI not found. Install: uv pip install awscli`

**Step 2: Load & Verify Credentials**
```bash
aws sts get-caller-identity --output json
```

Log format:
```
[SKILL] Loading AWS credentials...
[OK]   AWS_DEFAULT_REGION={{env.AWS_DEFAULT_REGION}} (from .env)
[OK]   AWS_ACCESS_KEY_ID=**** (from .env, masked)
[OK]   Credential verification passed
[OK]   Identity: arn:aws:iam::{{env.AWS_ACCOUNT_ID}}:user/xxx
```

On failure:
```
[FAIL] AWS credential verification failed.
AWS Error: <exact error message>
Action: See references/integration.md → Error Messages for diagnosis.
```

| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `aws --version` | Install AWS CLI v2 |
| Credentials | `aws sts get-caller-identity` | HALT; log precise error; guide user to integration.md |
| User name valid | Check naming rules | Suggest valid name |
| Path valid (optional) | Verify path format | Use default `/` |

#### Execute — CLI (Primary)
```bash
aws iam create-user \
  --user-name "{{user.user_name}}" \
  --path "{{user.path}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
import boto3
client = boto3.client('iam')
response = client.create_user(
    UserName='{{user.user_name}}',
    Path='{{user.path}}'
)
```

#### Validate
```bash
aws iam get-user --user-name "{{user.user_name}}" --output json
```

#### Recover
| Error | Action |
|-------|--------|
| EntityAlreadyExists | HALT; user already exists |
| InvalidInput | Fix name/path; retry once |
| Throttling (429) | Backoff, retry 3x |

### Operation: Create Role

#### Pre-flight
- Trust policy JSON must be provided
- Verify trust policy structure (Principal, Action, Condition)

#### Execute — CLI
```bash
aws iam create-role \
  --role-name "{{user.role_name}}" \
  --assume-role-policy-document file://trust-policy.json \
  --output json
```

#### Validate
```bash
aws iam get-role --role-name "{{user.role_name}}" --output json
```

### Operation: Attach Policy to Role

#### Execute — CLI
```bash
aws iam attach-role-policy \
  --role-name "{{user.role_name}}" \
  --policy-arn "{{user.policy_arn}}" \
  --output json
```

### Operation: Create Access Key (Sensitive)

**Safety Gate**: MUST warn user about credential handling.
> "Access Key will be generated. Store credentials securely—do NOT commit to code."

#### Execute — CLI
```bash
aws iam create-access-key --user-name "{{user.user_name}}" --output json
```

#### Present to User
| Field | JSON Path | Notes |
|-------|-----------|-------|
| AccessKeyId | `.AccessKey.AccessKeyId` | Public identifier |
| SecretAccessKey | `.AccessKey.SecretAccessKey` | **SHOW ONCE only; user must save immediately** |
| Status | `.AccessKey.Status` | Active/Inactive |

### Operation: Delete User (Destructive)

**Safety Gate**: MUST obtain explicit confirmation.
> "Delete user {{user.user_name}} and all associated access keys, policies? IRREVERSIBLE."

#### Pre-flight
- List attached policies
- List access keys
- List group memberships

#### Execute — CLI
```bash
# Detach policies first
aws iam list-attached-user-policies --user-name "{{user.user_name}}" --output json | jq -r '.AttachedPolicies[].PolicyArn' | xargs -I {} aws iam detach-user-policy --user-name "{{user.user_name}}" --policy-arn {}

# Delete access keys
aws iam list-access-keys --user-name "{{user.user_name}}" --output json | jq -r '.AccessKeyMetadata[].AccessKeyId' | xargs -I {} aws iam delete-access-key --user-name "{{user.user_name}}" --access-key-id {}

# Remove from groups
aws iam list-groups-for-user --user-name "{{user.user_name}}" --output json | jq -r '.Groups[].GroupName' | xargs -I {} aws iam remove-user-from-group --user-name "{{user.user_name}}" --group-name {}

# Delete user
aws iam delete-user --user-name "{{user.user_name}}" --output json
```

### Operation: List Users

#### Execute — CLI
```bash
aws iam list-users --output json
```

## IAM Policy Types

| Type | Description | Use Case |
|------|-------------|----------|
| Identity-based | Attach to user/group/role | Grant permissions to identities |
| Resource-based | Attach to resource (S3, Lambda) | Grant permissions to principals |
| Managed (AWS) | Pre-built by AWS | Common permissions (ReadOnly, Admin) |
| Managed (Customer) | Custom reusable policies | Organization-specific |
| Inline | Embedded in identity | One-off permissions |

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](../aws-skill-generator/references/integration.md)
## Quality Gate (GCL)

> This skill is the **Phase 1 GCL pilot** (2026-06-04, second rollout after
> `aws-ec2-ops`). Every execution of `aws-iam-ops` MUST be wrapped by the
> Generator-Critic-Loop defined in `aws-skill-generator/references/gcl-spec.md`.

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
(exact format `confirm=<OPERATION> <resource-name>`):

- `delete-user` (after detach-policies + delete-keys + remove-from-groups pre-flight)
- `delete-access-key`
- `delete-login-profile`
- `delete-signing-certificate`
- `delete-ssh-public-key`
- `delete-service-specific-credential`
- `detach-user-policy` / `detach-role-policy` / `detach-group-policy`
- `delete-role` (after detach-policies + delete-inline-policies pre-flight)
- `delete-policy` (after detach from all entities pre-flight)
- `delete-group` (after remove-users pre-flight)
- `delete-instance-profile` (after remove-roles pre-flight)
- `attach-user-policy` / `attach-role-policy` — when target policy contains
  `*:*` or `AdministratorAccess` (see Safety special cases)

Non-destructive operations (`list-*`, `get-*`, `create-user`, `create-role`
without `*:*` policy) still flow through GCL with `Safety` scored against
routine guard rules only.

### AWS-specific rules in force

This skill's rubric instantiates the repo-wide AWS rules from
`gcl-spec.md` §8. The ones most relevant to IAM:

- **A9** — `SecretAccessKey` MUST NOT appear anywhere in the trace
  (mask with `***` and key id suffix only). This is a **Safety=0 auto-fail**.
- **A10** — `aws sts get-caller-identity` MUST be the first command in trace
  to capture identity provenance
- **A8** — `UserName` / `RoleName` / `PolicyArn` in the request MUST be
  echoed back from a `get-*` lookup
- **A7** — `--region` must match `{{user.region}}` or `{{env.AWS_DEFAULT_REGION}}`
  (IAM is global; `--region us-east-1` is the canonical choice)

### See also

- `aws-skill-generator/references/gcl-spec.md` — full GCL specification
- `references/rubric.md` — this skill's 5-dimension rubric + IAM safety
  special cases (`*:*` policy guard, root-account key refusal, `Principal: *`
  trust policy guard, attached-policies pre-flight for `delete-user`)
- `references/prompt-templates.md` — Generator / Critic / Orchestrator
  skeletons
- Top-level `AGENTS.md` §11 — rollout index and Per-Skill Defaults

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

