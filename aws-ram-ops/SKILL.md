---
name: aws-ram-ops
description: >-
  Use when the user needs to manage AWS Resource Access Manager (RAM) resources
  — resource shares, permissions, principals, invitations, or cross-account
  resource sharing; user mentions "RAM", "resource share", "resource sharing",
  "cross-account share", "RAM permission", "share invitation", or "AWS RAM".
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to AWS RAM endpoints.
metadata:
  author: aws
  version: "1.3.0"
  last_updated: "2026-06-27"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  gcl: {enabled: true, class: required, max_iter: 2, rubric_ref: references/rubric.md, prompts_ref: references/prompt-templates.md, pilot: false}
  destructive_ops_require_confirm: true
  environment: [AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN, AWS_DEFAULT_REGION, AWS_PROFILE]
  cross_skill_deps: [aws-iam-ops, aws-ec2-ops, aws-rds-ops, aws-aurora-ops, aws-vpc-ops]
  orchestrator_aware: true
  orchestrator_compat: ">=0.10"
  delegate:
    accepts: ['compliance-scan', 'change-impact']
    produces_facts: ['config', 'state']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---

# AWS Resource Access Manager (RAM) Operations Skill

## Common JSON Paths (Centralized)

```
# ResourceShare: .resourceShare.{resourceShareArn,name,owningAccountId,allowExternalPrincipals,status,featureSet,creationTime,lastUpdatedTime}
# Association:   .resourceShareAssociation.{resourceShareArn,associatedResource,principal,associationType,status,external}
# Invitation:    .resourceShareInvitation.{resourceShareInvitationArn,resourceShareArn,name,senderAccountId,receiverAccountId,status,invitationTimestamp}
# Permission:    .resourceSharePermission.{permissionArn,permissionName,permissionVersion,isAssociationDefault,defaultVersion,status}
# Resource:      .resource.{arn,type,resourceShareArn,resourceOwnerId,status}
# Principal:     .principal.{id,arn,resourceShareArn,principalType,lastUpdatedTime}
```

## Overview

AWS RAM helps you securely share resources across AWS accounts or within an organization. This skill is an **operational runbook** with pre-flight → execute → validate → recover.

## Trigger & Scope

### SHOULD Use When
user mentions RAM/resource-share/cross-account/permission/invitation/OU-share; CRUD on shares/permissions/principals; accept/reject invitations; enable Organizations sharing; multi-account (subnets/SGs/Aurora/RDS shared to app accounts); onboarding or audit flows.

### SHOULD NOT Use When
(delegates) create AWS accounts → use account provisioning first; IAM inside consumer accounts → `aws-iam-ops`; VPC/subnet/SG ops → `aws-vpc-ops`; EC2 in shared VPC → `aws-ec2-ops`; RDS cluster sharing detail → `aws-rds-ops`; standalone resource tagging → `aws resourcegroupstaggingapi` CLI.

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_*}}` | Runtime env | NEVER ask user; fail if unset |
| `{{user.region}}` / `{{user.share_name}}` / `{{user.share_arn}}` / `{{user.resource_arns}}` / `{{user.principal_arns}}` / `{{user.permission_arn}}` / `{{user.permission_name}}` / `{{user.invitation_arn}}` / `{{user.resource_type}}` / `{{user.policy_template}}` / `{{user.ou_arn}}` | User input | Ask once; reuse |
| `{{output.resourceShareArn}}` / `{{output.invitationArn}}` | Last API response | Parse: `.resourceShare.resourceShareArn` / `.resourceShareInvitation.resourceShareInvitationArn` |

## Config File Placeholders

`assets/example-config.yaml` uses `{{env.AWS_DEFAULT_REGION}}` / `{{env.AWS_ACCOUNT_ID}}` (load from `.env` or runtime env) and `{{user.share_name}}` / `{{user.resource_arns}}` (ask once, substitute). Render order: load `.env` → substitute `{{env.*}}` → collect `{{user.*}}` → invoke CLI/SDK.

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**.
Per-operation detail (CLI + boto3 + Validate + Recover tables) lives in
[references/operations.md](references/operations.md).

## Operations Index

| Operation | Detail |
|-----------|--------|
| Create Resource Share | [operations.md#create-resource-share](references/operations.md#operation-create-resource-share) |
| Associate Resource Share | [operations.md#associate-resource-share](references/operations.md#operation-associate-resource-share) |
| Disassociate Resource Share | [operations.md#disassociate-resource-share](references/operations.md#operation-disassociate-resource-share) |
| Accept Resource Share Invitation | [operations.md#accept-resource-share-invitation](references/operations.md#operation-accept-resource-share-invitation) |
| Reject Resource Share Invitation | [operations.md#reject-resource-share-invitation](references/operations.md#operation-reject-resource-share-invitation) |
| Update Resource Share | [operations.md#update-resource-share](references/operations.md#operation-update-resource-share) |
| Enable Sharing with AWS Organization | [operations.md#enable-sharing-with-aws-organization](references/operations.md#operation-enable-sharing-with-aws-organization) |
| Create Permission | [operations.md#create-permission](references/operations.md#operation-create-permission) |
| Associate Resource Share Permission | [operations.md#associate-resource-share-permission](references/operations.md#operation-associate-resource-share-permission) |
| Delete Resource Share | [operations.md#delete-resource-share](references/operations.md#operation-delete-resource-share) |
| Delete Permission | [operations.md#delete-permission](references/operations.md#operation-delete-permission) |
| Delete Permission Version | [operations.md#delete-permission-version](references/operations.md#operation-delete-permission-version) |
## Safety Gates

All destructive ops require explicit human confirmation with the op-specific string:

| Op | Confirmation string |
|----|---------------------|
| `delete-resource-share` | `confirm=DELETE_RESOURCE_SHARE {{user.share_arn}}` |
| `delete-permission` | `confirm=DELETE_PERMISSION {{user.permission_arn}}` |
| `delete-permission-version` | `confirm=DELETE_PERMISSION_VERSION {{user.permission_arn}} {{user.permission_version}}` |
| `reject-resource-share-invitation` | `confirm=REJECT_INVITATION {{user.invitation_arn}}` |

Before each: display the impact (principals/shares that will lose access), then require the typed confirmation string.

## Token Efficiency

All 6 TE rules applied (see `aws-skill-generator` SKILL.md). Operations detail in `references/operations.md` (TE-6); JSON paths in `## Common JSON Paths` (TE-4); CLI commands preferred over hardcoded tables (TE-1).

## Reference Files

[prompt-examples.md](references/prompt-examples.md) · [integration.md](references/integration.md) · [aws-cli-usage.md](references/aws-cli-usage.md) · [boto3-sdk-usage.md](references/boto3-sdk-usage.md) · [core-concepts.md](references/core-concepts.md) · [troubleshooting.md](references/troubleshooting.md) · [operations.md](references/operations.md) · [rubric.md](references/rubric.md) · [prompt-templates.md](references/prompt-templates.md)

## Quality Gate (GCL)

`required` · `max_iterations=2` · rubric `references/rubric.md` (v1). Per `aws-skill-generator/references/gcl-spec.md`. Destructive ops (all 4 above) require their `confirm=...` string (see Safety Gates table) and wrap through the Generator-Critic-Loop.

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md). Recognise the `aiops_delegate:` block (`request_id`, `parent_intent`, `action_mode`, `decision_tier`, `scope.resource_ids`) and apply: (1) 24h `idempotency_key` dedup; (2) destructive ops require `confirmation_token` (else `aiops_context.status: "failed"`); (3) `decision_tier` rules: `MANUAL` = no writes, `AI_ASSIST` = recommend + token-gated, `AUTO_HEAL` = non-destructive writes OK; (4) propagate `trace_id` in `User-Agent: aiops-orchestrator/<trace_id>`; (5) always emit `aiops_context` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).

