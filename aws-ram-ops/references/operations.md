# AWS RAM — Operations Detail

> Sourced from `aws-ram-ops/SKILL.md` §Execution Flow Pattern → §Operation: <name>.
> This file holds the per-operation Pre-flight → Execute → Validate → Recover blocks.
> SKILL.md keeps an `## Operations Index` table that links here.

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
