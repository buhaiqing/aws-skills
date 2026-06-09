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
  version: "1.0.0"
  last_updated: "2026-06-10"
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
    - AWS_PROFILE
  cross_skill_deps:
    - aws-iam-ops         # RAM service-linked role / IAM policies for shared resources
    - aws-ec2-ops         # VPC Subnet / Security Group sharing
    - aws-rds-ops         # DB Cluster sharing
    - aws-vpc-ops         # VPC and network resource sharing
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
- User mentions "RAM", "resource share", "resource sharing", "cross-account share"
- Task involves CRUD on **resource shares**, **permissions**, or **principals**
- Task involves **accepting/rejecting** resource share invitations
- Task involves **enabling Organizations sharing** or **disassociating** resources
- Keywords: ram, resource-share, cross-account, sharing, permission, invitation, principal

### SHOULD NOT Use When
- IAM roles/policies for shared resources → delegate to: `aws-iam-ops`
- VPC/Subnet/Security Group operations → delegate to: `aws-vpc-ops`
- EC2 instances in shared VPC → delegate to: `aws-ec2-ops`
- RDS cluster sharing details → delegate to: `aws-rds-ops`
- Standalone resource tagging → use `aws resourcegroupstaggingapi` CLI directly

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{env.AWS_PROFILE}}` | Runtime env | Use named profile over explicit keys |
| `{{user.region}}` | User input | Ask once; reuse |
| `{{user.share_name}}` | User input | Resource share name |
| `{{user.resource_arns}}` | User input | Resource ARNs to share |
| `{{user.principal_arns}}` | User input | Principal ARNs or account IDs |
| `{{user.permission_arn}}` | User input | RAM permission ARN |
| `{{user.invitation_arn}}` | User input | Resource share invitation ARN |
| `{{user.share_arn}}` | User input | Resource share ARN |
| `{{output.resourceShareArn}}` | Last API response | Parse: `.resourceShare.resourceShareArn` |
| `{{output.invitationArn}}` | Last API response | Parse: `.resourceShareInvitation.resourceShareInvitationArn` |

## Execution Flow Pattern

Every operation: **Pre-flight** → **Execute** (CLI, boto3 fallback) → **Validate** → **Recover**.

### Common Pre-flight Steps (all ops)

```bash
aws --version && aws sts get-caller-identity --output json
```
Log: `[OK] AWS CLI v2.x` and `[OK] Identity: arn:aws:iam::...`.

### Operation: Create Resource Share

#### Execute — CLI (Primary)
```bash
aws ram create-resource-share \
  --name "{{user.share_name}}" \
  --resource-arns "{{user.resource_arns}}" \
  --principals "{{user.principal_arns}}" \
  --allow-external-principals \
  --region "{{user.region}}" \
  --output json
```

#### Validate
`aws ram get-resource-shares --resource-share-arns {{output.resourceShareArn}}` → check status is `ACTIVE`.

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameter | Fix args; retry once |
| ServerException | Retry 3x; HALT |
| ThrottlingException | Backoff; retry 3x |
| MalformedArn | HALT — verify ARN format |

### Operation: Associate Resource Share

```bash
aws ram associate-resource-share \
  --resource-share-arn "{{user.share_arn}}" \
  --principals "{{user.principal_arns}}" \
  --resource-arns "{{user.resource_arns}}" \
  --region "{{user.region}}" \
  --output json
```
Validate: `get-resource-share-associations --association-type PRINCIPAL`.

### Operation: Disassociate Resource Share

```bash
aws ram disassociate-resource-share \
  --resource-share-arn "{{user.share_arn}}" \
  --principals "{{user.principal_arns}}" \
  --resource-arns "{{user.resource_arns}}" \
  --region "{{user.region}}" \
  --output json
```

### Operation: Accept Resource Share Invitation

```bash
aws ram accept-resource-share-invitation \
  --resource-share-invitation-arn "{{user.invitation_arn}}" \
  --region "{{user.region}}" \
  --output json
```
Validate: `get-resource-share-invitations` → status is `ACCEPTED`.

### Operation: Reject Resource Share Invitation
**Safety Gate**: `confirm=REJECT_INVITATION {{user.invitation_arn}}`

```bash
aws ram reject-resource-share-invitation \
  --resource-share-invitation-arn "{{user.invitation_arn}}" \
  --region "{{user.region}}" \
  --output json
```

### Operation: Update Resource Share

```bash
aws ram update-resource-share \
  --resource-share-arn "{{user.share_arn}}" \
  --name "{{user.share_name}}" \
  --allow-external-principals \
  --region "{{user.region}}" \
  --output json
```

### Operation: Enable Sharing with AWS Organization

```bash
aws ram enable-sharing-with-aws-organization \
  --region "{{user.region}}" \
  --output json
```

### Operation: Create Permission

```bash
aws ram create-permission \
  --name "{{user.permission_name}}" \
  --resource-type "{{user.resource_type}}" \
  --policy-template "{{user.policy_template}}" \
  --region "{{user.region}}" \
  --output json
```

### Operation: Delete Resource Share
**Safety Gate**: `confirm=DELETE_RESOURCE_SHARE {{user.share_arn}}`

```bash
aws ram delete-resource-share \
  --resource-share-arn "{{user.share_arn}}" \
  --region "{{user.region}}" \
  --output json
```
Validate: `get-resource-shares` → status changes to `DELETED` or resource not found.

### Operation: Delete Permission
**Safety Gate**: `confirm=DELETE_PERMISSION {{user.permission_arn}}`

```bash
aws ram delete-permission \
  --permission-arn "{{user.permission_arn}}" \
  --region "{{user.region}}" \
  --output json
```

### Operation: Delete Permission Version
**Safety Gate**: `confirm=DELETE_PERMISSION_VERSION {{user.permission_arn}} {{user.permission_version}}`

```bash
aws ram delete-permission-version \
  --permission-arn "{{user.permission_arn}}" \
  --version {{user.permission_version}} \
  --region "{{user.region}}" \
  --output json
```

## Safety Gates

### Delete Resource Share
```
BEFORE delete-resource-share:
1. Display: "Deleting resource share {{user.share_arn}} — all associated principals will lose access to shared resources"
2. Ask: "Type 'DELETE_RESOURCE_SHARE {{user.share_arn}}' to confirm"
3. Pre-flight: list all associated principals and resources
```

### Delete Permission
```
BEFORE delete-permission:
1. Display: "Deleting permission {{user.permission_arn}} — all resource shares using this permission will be affected"
2. Ask: "Type 'DELETE_PERMISSION {{user.permission_arn}}' to confirm"
3. Pre-flight: list all resource shares associated with this permission
```

### Delete Permission Version
```
BEFORE delete-permission-version:
1. Display: "Deleting permission version {{user.permission_version}} for {{user.permission_arn}}"
2. Ask: "Type 'DELETE_PERMISSION_VERSION {{user.permission_arn}} {{user.permission_version}}' to confirm"
```

### Reject Resource Share Invitation
```
BEFORE reject-resource-share-invitation:
1. Display: "Rejecting invitation {{user.invitation_arn}} — you will not have access to the shared resources"
2. Ask: "Type 'REJECT_INVITATION {{user.invitation_arn}}' to confirm"
```

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [GCL Rubric](references/rubric.md)
- [GCL Prompt Templates](references/prompt-templates.md)

## Quality Gate (GCL)

> Phase 1 GCL rollout (2026-06-10, required). Every execution of
> `aws-ram-ops` MUST be wrapped by the Generator-Critic-Loop defined in
> `aws-skill-generator/references/gcl-spec.md`.

| Setting | Value |
|---|---|
| Class | `required` |
| `max_iterations` | `2` |
| Rubric | `references/rubric.md` (v1) |

| Operation | GCL | Notes |
|---|---|---|
| `delete-resource-share` | required | `confirm=DELETE_RESOURCE_SHARE <arn>` — breaks dependent accounts |
| `delete-permission` | required | `confirm=DELETE_PERMISSION <arn>` — affects all associated shares |
| `delete-permission-version` | required | `confirm=DELETE_PERMISSION_VERSION <arn> <version>` |
| `reject-resource-share-invitation` | required | `confirm=REJECT_INVITATION <arn>` |
