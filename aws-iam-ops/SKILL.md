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
  last_updated: "2026-07-31"
  runtime: Harness AI Agent
  type: base
  provides:
  - access-analyzer-findings
  cli_applicability: dual-path
  gcl: {enabled: true, class: required, max_iter: 2, rubric_ref: references/rubric.md, prompts_ref: references/prompt-templates.md, pilot: true}
  destructive_ops_require_confirm: true
  environment: [AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION]
  cross_skill_deps:
    - aws-cloudtrail-ops
    - aws-kms-ops
  orchestrator_aware: true
  orchestrator_compat: ">=0.10"
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
user mentions IAM / Identity / Access Management / permissions; CRUD on users, groups, roles, policies; access-key / trust-policy / federated-access / SSO setup.

### SHOULD NOT Use When
EC2/S3 → `aws-ec2-ops` / `aws-s3-ops`; billing → Cost Explorer; security audit/compliance → specialized security skill (if exists).

## Variable Convention

| Placeholder | Source | Action |
|-------------|--------|--------|
| `{{env.AWS_*}}` | Runtime env | NEVER ask user; fail if unset; IAM is global (region = STS only) |
| `{{user.user_name}}` / `{{user.role_name}}` | User input | Ask once; reuse |
| `{{output.arn}}` | API response | Parse `.User.Arn` / `.Role.Arn` |

## Execution Flow Pattern

Every operation: **Pre-flight → Execute → Validate → Recover** (CLI primary, boto3 fallback after 3 failures). Per-operation detail in [references/operations.md](references/operations.md).

## Operations Index

| Operation | Detail |
|-----------|--------|
| Create User | [operations.md#create-user](references/operations.md#operation-create-user) |
| Create Role | [operations.md#create-role](references/operations.md#operation-create-role) |
| Attach Policy to Role | [operations.md#attach-policy-to-role](references/operations.md#operation-attach-policy-to-role) |
| Create Access Key (Sensitive) | [operations.md#create-access-key-sensitive](references/operations.md#operation-create-access-key-sensitive) |
| Delete User (Destructive) | [operations.md#delete-user-destructive](references/operations.md#operation-delete-user-destructive) |
| List Users | [operations.md#list-users](references/operations.md#operation-list-users) |
| Get Credential Report | [operations.md#get-credential-report](references/operations.md#operation-get-credential-report) |

## IAM Policy Types

See `aws-skill-generator/references/aws-cli-conventions.md` for the full taxonomy (Identity / Resource / AWS-Managed / Customer-Managed / Inline). For `put-user-policy` / `put-role-policy` (inline) prefer `attach-user-policy` / `attach-role-policy` (managed) unless one-off.

## Token Efficiency

All 6 TE rules applied (see `aws-skill-generator` SKILL.md). Per-operation detail in `references/operations.md` (TE-6); JSON paths in `## Common JSON Paths` (TE-4); no hardcoded policy ARNs (TE-1).

## Reference Files

[aws-cli-usage.md](references/aws-cli-usage.md) · [boto3-sdk-usage.md](references/boto3-sdk-usage.md) · [core-concepts.md](references/core-concepts.md) · [troubleshooting.md](references/troubleshooting.md) · [operations.md](references/operations.md) · [rubric.md](references/rubric.md) · [prompt-templates.md](references/prompt-templates.md) · [integration.md](../aws-skill-generator/references/integration.md)
## Quality Gate (GCL)

`required` · `max_iterations=2` · rubric `references/rubric.md` (v1) · per `aws-skill-generator/references/gcl-spec.md`. Destructive ops require `confirm=` tokens: `confirm=DELETE_USER`, `confirm=DELETE_ROLE`, `confirm=DETACH_POLICY`, `confirm=ATTACH_ADMIN`, `confirm=ATTACH_WILDCARD`, `confirm=TRUST_PUBLIC` — see [prompt-templates.md#confirmation-strings](references/prompt-templates.md#confirmation-strings).

AWS rules in force: **A9** `SecretAccessKey` masked (Safety=0 fail) · **A10** `aws sts get-caller-identity` first · **A8** resource id echoed from `get-*` lookup · **A7** `--region` matches `{{user.region}}` or `{{env.AWS_DEFAULT_REGION}}` (canonical: `us-east-1`). See `references/rubric.md` for IAM special cases (`*:*` policy guard, root-account key refusal, `Principal: *` trust policy guard, attached-policies pre-flight for `delete-user`).

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md). Recognise the `aiops_delegate:` block (`request_id`, `parent_intent`, `action_mode`, `decision_tier`, `scope.resource_ids`) and apply: (1) 24h `idempotency_key` dedup; (2) destructive ops require `confirmation_token` (else `aiops_context.status: "failed"`); (3) `decision_tier` rules: `MANUAL` = no writes, `AI_ASSIST` = recommend + token-gated, `AUTO_HEAL` = non-destructive writes OK; (4) propagate `trace_id` in `User-Agent: aiops-orchestrator/<trace_id>`; (5) always emit `aiops_context` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).

