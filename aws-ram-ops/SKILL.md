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
  version: "1.2.0"
  last_updated: "2026-06-26"
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
    - AWS_SESSION_TOKEN
    - AWS_DEFAULT_REGION
    - AWS_PROFILE
  cross_skill_deps:
    - aws-iam-ops         # Consumer-account IAM after RAM resource visibility
    - aws-ec2-ops         # VPC Subnet / Security Group sharing
    - aws-rds-ops         # DB Cluster sharing
    - aws-aurora-ops      # Aurora cluster ARN lookup + consumer validation
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
- **Multi-account / app-team accounts**: share subnets, SGs, Aurora/RDS clusters to application management accounts
- **Authorization**: associate/disassociate/replace RAM **permissions** (read-only vs read-write) on a share
- **Onboarding**: new app account accepts invitation; audit `list-resources` / `list-principals` for a principal
- Keywords: ram, resource-share, cross-account, sharing, permission, invitation, principal, app account, OU share

### SHOULD NOT Use When
- **Creating AWS accounts** or Organizations member accounts → outside RAM; complete account provisioning first, then use this skill to share resources
- IAM roles/policies **inside** consumer accounts (e.g. `ec2:RunInstances` after subnet is shared) → delegate to: `aws-iam-ops`
- VPC/Subnet/Security Group operations → delegate to: `aws-vpc-ops`
- EC2 instances in shared VPC → delegate to: `aws-ec2-ops`
- RDS cluster sharing details → delegate to: `aws-rds-ops`
- Standalone resource tagging → use `aws resourcegroupstaggingapi` CLI directly

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SESSION_TOKEN}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{env.AWS_PROFILE}}` | Runtime env | Use named profile over explicit keys |
| `{{user.region}}` | User input | Ask once; reuse |
| `{{user.share_name}}` | User input | Resource share name |
| `{{user.resource_arns}}` | User input | Resource ARNs to share |
| `{{user.principal_arns}}` | User input | Principal ARNs or account IDs |
| `{{user.permission_arn}}` | User input | RAM permission ARN |
| `{{user.invitation_arn}}` | User input | Resource share invitation ARN |
| `{{user.share_arn}}` | User input | Resource share ARN |
| `{{user.permission_name}}` | User input | Custom RAM permission name |
| `{{user.resource_type}}` | User input | e.g. `ec2:Subnet`, `rds:Cluster` — use `list-resource-types` |
| `{{user.policy_template}}` | User input | JSON policy template for `create-permission` |
| `{{user.ou_arn}}` | User input | Organizations OU ARN as principal |
| `{{output.resourceShareArn}}` | Last API response | Parse: `.resourceShare.resourceShareArn` |
| `{{output.invitationArn}}` | Last API response | Parse: `.resourceShareInvitation.resourceShareInvitationArn` |

## Config File Placeholders

`assets/example-config.yaml` uses `{{env.*}}` for environment values and `{{user.*}}` for resource-specific values:

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_DEFAULT_REGION}}` | `.env` or runtime env | Substitute before use |
| `{{env.AWS_ACCOUNT_ID}}` | `.env` or runtime env | Substitute before use |
| `{{user.share_name}}` | User input | Ask once; substitute |
| `{{user.resource_arns}}` | User input | Ask once; substitute |

Before using `example-config.yaml`:
1. Load `.env` from project root (if present)
2. Substitute `{{env.*}}` placeholders with loaded values
3. Collect `{{user.*}}` values from user input
4. Use rendered config for CLI/SDK commands

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Pre-flight │ → │   Execute   │ → │   Validate  │ → │   Recover   │
│   Checks    │    │ CLI/SDK     │    │   Polling   │    │  On Error   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Common Pre-flight Steps (all ops)

#### Step 1: Check CLI
```bash
aws --version
```
Log: `[OK] AWS CLI v2.x.x detected` or `[FAIL] AWS CLI not found. Install: pip install awscli`

#### Step 2: Load & Verify Credentials
```bash
aws sts get-caller-identity --output json
```
Log format:
```
[SKILL] Loading AWS credentials...
[OK]   AWS_DEFAULT_REGION={{env.AWS_DEFAULT_REGION}} (from env)
[OK]   AWS_ACCESS_KEY_ID=**** (masked)
[OK]   Credential verification passed
[OK]   Identity: arn:aws:iam::{{env.AWS_ACCOUNT_ID}}:user/xxx
```
On failure:
```
[FAIL] AWS credential verification failed.
AWS Error: <exact error message>
Action: See references/troubleshooting.md for diagnosis.
```

| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `aws --version` | Install AWS CLI v2 |
| Credentials | `aws sts get-caller-identity` | HALT; log precise error; guide to troubleshooting.md |
| Region valid | `aws ram list-resource-types --region {{user.region}}` | Suggest valid region |

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

#### Execute — boto3 (Fallback)
```python
response = client.create_resource_share(
    name='{{user.share_name}}',
    resourceArns=['{{user.resource_arns}}'],
    principals=['{{user.principal_arns}}'],
    allowExternalPrincipals=True
)
share_arn = response['resourceShare']['resourceShareArn']
```
See `references/boto3-sdk-usage.md` for full patterns.

### Operation: Associate Resource Share

#### Execute — CLI (Primary)
```bash
aws ram associate-resource-share \
  --resource-share-arn "{{user.share_arn}}" \
  --principals "{{user.principal_arns}}" \
  --resource-arns "{{user.resource_arns}}" \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
client.associate_resource_share(
    resourceShareArn='{{user.share_arn}}',
    principals=['{{user.principal_arns}}'],
    resourceArns=['{{user.resource_arns}}']
)
```
See `references/boto3-sdk-usage.md` for full patterns.

#### Validate
`aws ram get-resource-share-associations --association-type PRINCIPAL --resource-share-arns {{user.share_arn}}` → check status is `ASSOCIATED`.

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameter | Fix args; retry once |
| MalformedArn | HALT — verify ARN format |
| ThrottlingException | Backoff; retry 3x |
| ServerException | Retry 3x; HALT |

### Operation: Disassociate Resource Share

#### Execute — CLI (Primary)
```bash
aws ram disassociate-resource-share \
  --resource-share-arn "{{user.share_arn}}" \
  --principals "{{user.principal_arns}}" \
  --resource-arns "{{user.resource_arns}}" \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
client.disassociate_resource_share(
    resourceShareArn='{{user.share_arn}}',
    principals=['{{user.principal_arns}}'],
    resourceArns=['{{user.resource_arns}}']
)
```
See `references/boto3-sdk-usage.md` for full patterns.

#### Validate
`aws ram get-resource-share-associations --association-type PRINCIPAL --resource-share-arns {{user.share_arn}}` → confirm principal(s) no longer associated (status `DISASSOCIATED` or absent).

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameter | Fix args; retry once |
| MalformedArn | HALT — verify ARN format |
| ThrottlingException | Backoff; retry 3x |
| ServerException | Retry 3x; HALT |

### Operation: Accept Resource Share Invitation

#### Execute — CLI (Primary)
```bash
aws ram accept-resource-share-invitation \
  --resource-share-invitation-arn "{{user.invitation_arn}}" \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
response = client.accept_resource_share_invitation(
    resourceShareInvitationArn='{{user.invitation_arn}}'
)
```
See `references/boto3-sdk-usage.md` for full patterns.

#### Validate
`aws ram get-resource-share-invitations --resource-share-invitation-arns {{user.invitation_arn}}` → check status is `ACCEPTED`.

#### Recover
| Error | Action |
|-------|--------|
| MalformedArn | HALT — verify ARN format |
| InvalidParameter | Fix args; retry once |
| ThrottlingException | Backoff; retry 3x |
| ServerException | Retry 3x; HALT |

### Operation: Reject Resource Share Invitation
**Safety Gate**: `confirm=REJECT_INVITATION {{user.invitation_arn}}`

#### Execute — CLI (Primary)
```bash
aws ram reject-resource-share-invitation \
  --resource-share-invitation-arn "{{user.invitation_arn}}" \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
client.reject_resource_share_invitation(
    resourceShareInvitationArn='{{user.invitation_arn}}'
)
```
See `references/boto3-sdk-usage.md` for full patterns.

#### Validate
`aws ram get-resource-share-invitations --resource-share-invitation-arns {{user.invitation_arn}}` → check status is `REJECTED`.

#### Recover
| Error | Action |
|-------|--------|
| ResourceShareInvitationAlreadyRejectedException | HALT — already rejected |
| InvalidParameter | Fix args; retry once |
| ThrottlingException | Backoff; retry 3x |
| ServerException | Retry 3x; HALT |

### Operation: Update Resource Share

#### Execute — CLI (Primary)
```bash
aws ram update-resource-share \
  --resource-share-arn "{{user.share_arn}}" \
  --name "{{user.share_name}}" \
  --allow-external-principals \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
response = client.update_resource_share(
    resourceShareArn='{{user.share_arn}}',
    name='{{user.share_name}}',
    allowExternalPrincipals=True
)
```
See `references/boto3-sdk-usage.md` for full patterns.

#### Validate
`aws ram get-resource-shares --resource-share-arns {{user.share_arn}}` → confirm name and `allowExternalPrincipals` match expected values.

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameter | Fix args; retry once |
| MalformedArn | HALT — verify ARN format |
| ThrottlingException | Backoff; retry 3x |
| ServerException | Retry 3x; HALT |

### Operation: Enable Sharing with AWS Organization

#### Execute — CLI (Primary)
```bash
aws ram enable-sharing-with-aws-organization \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
client.enable_sharing_with_aws_organization()
```
See `references/boto3-sdk-usage.md` for full patterns.

#### Validate
Verify with `aws organizations describe-organization` → confirm `FeatureSet` includes `ALL`.

#### Recover
| Error | Action |
|-------|--------|
| OperationNotPermittedException | HALT — caller must be management account or delegated admin |
| ThrottlingException | Backoff; retry 3x |
| ServerException | Retry 3x; HALT |

### Operation: Create Permission

#### Execute — CLI (Primary)
```bash
aws ram create-permission \
  --name "{{user.permission_name}}" \
  --resource-type "{{user.resource_type}}" \
  --policy-template "{{user.policy_template}}" \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
response = client.create_permission(
    name='{{user.permission_name}}',
    resourceType='{{user.resource_type}}',
    policyTemplate='{{user.policy_template}}'
)
```
See `references/boto3-sdk-usage.md` for full patterns.

#### Validate
`aws ram get-permission --permission-arn {{output.permissionArn}}` → confirm `permissionVersion` and `status`.

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameter | Fix policy template or resource type; retry once |
| MalformedArn | HALT — verify ARN format |
| ThrottlingException | Backoff; retry 3x |
| ServerException | Retry 3x; HALT |

### Operation: Associate Resource Share Permission

#### Execute — CLI (Primary)
```bash
aws ram associate-resource-share-permission \
  --resource-share-arn "{{user.share_arn}}" \
  --permission-arn "{{user.permission_arn}}" \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
client.associate_resource_share_permission(
    resourceShareArn='{{user.share_arn}}',
    permissionArn='{{user.permission_arn}}'
)
```
See `references/boto3-sdk-usage.md` for full patterns.

#### Validate
`aws ram get-permission --permission-arn {{user.permission_arn}}` + `aws ram get-resource-share-associations --resource-share-arns {{user.share_arn}}` → confirm permission is associated.

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameter | Fix ARNs; retry once |
| MalformedArn | HALT — verify ARN format |
| ThrottlingException | Backoff; retry 3x |
| ServerException | Retry 3x; HALT |

### Operation: Delete Resource Share
**Safety Gate**: `confirm=DELETE_RESOURCE_SHARE {{user.share_arn}}`

#### Execute — CLI (Primary)
```bash
aws ram delete-resource-share \
  --resource-share-arn "{{user.share_arn}}" \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
try:
    client.delete_resource_share(resourceShareArn='{{user.share_arn}}')
except ClientError as e:
    if e.response['Error']['Code'] == 'ResourceNotFoundException':
        print("Resource share not found (may already be deleted)")
```
See `references/boto3-sdk-usage.md` for full patterns.

#### Validate
`aws ram get-resource-shares --resource-share-arns {{user.share_arn}}` → status changes to `DELETED` or resource not found.

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameter | Fix ARN; retry once |
| MalformedArn | HALT — verify ARN format |
| ThrottlingException | Backoff; retry 3x |
| ServerException | Retry 3x; HALT |

### Operation: Delete Permission
**Safety Gate**: `confirm=DELETE_PERMISSION {{user.permission_arn}}`

#### Execute — CLI (Primary)
```bash
aws ram delete-permission \
  --permission-arn "{{user.permission_arn}}" \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
client.delete_permission(permissionArn='{{user.permission_arn}}')
```
See `references/boto3-sdk-usage.md` for full patterns.

#### Validate
`aws ram list-permissions` → permission no longer listed, or `aws ram get-permission --permission-arn {{user.permission_arn}}` returns `ResourceNotFoundException`.

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameter | Fix ARN; retry once |
| MalformedArn | HALT — verify ARN format |
| ThrottlingException | Backoff; retry 3x |
| ServerException | Retry 3x; HALT |

### Operation: Delete Permission Version
**Safety Gate**: `confirm=DELETE_PERMISSION_VERSION {{user.permission_arn}} {{user.permission_version}}`

#### Execute — CLI (Primary)
```bash
aws ram delete-permission-version \
  --permission-arn "{{user.permission_arn}}" \
  --version {{user.permission_version}} \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
client.delete_permission_version(
    permissionArn='{{user.permission_arn}}',
    version={{user.permission_version}}
)
```
See `references/boto3-sdk-usage.md` for full patterns.

#### Validate
`aws ram get-permission --permission-arn {{user.permission_arn}}` → confirm specified version is no longer listed.

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameter | Fix version; retry once |
| MalformedArn | HALT — verify ARN format |
| ResourceNotFoundException | HALT — permission or version not found |
| ThrottlingException | Backoff; retry 3x |
| ServerException | Retry 3x; HALT |

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

## Token Efficiency

All 6 TE rules applied (see `aws-skill-generator` SKILL.md §Token Efficiency Requirements). Key points:
- TE-1: No hardcoded resource type lists — use `list-resource-types` / `list-resources`
- TE-2: Inline comments only in boto3 code (no docstrings)
- TE-3: Compact error tables throughout
- TE-4: JSON paths centralized in `## Common JSON Paths` block above
- TE-5: YAML anchors in `assets/example-config.yaml` where applicable
- TE-6: Flows only in SKILL.md (no duplicate in references/)

## Reference Files

- [Prompt Examples](references/prompt-examples.md) — multi-account app sharing & authorization scenarios
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
