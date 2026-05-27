# Troubleshooting — IAM

## Common Error Codes

| Error | Agent Action |
|-------|-------------|
| EntityAlreadyExists (409) | HALT; use different name |
| NoSuchEntity (404) | HALT; verify name/ARN |
| InvalidInput (400) | Fix naming; retry once |
| LimitExceeded (400) | HALT; request quota increase |
| MalformedPolicyDocument (400) | Validate JSON structure |
| DeleteConflict (409) | Remove attached entities first |
| ThrottlingException (429) | Backoff; retry 3x |
| ServiceFailure (500) | Retry 3x; HALT if persists |

## Diagnostic Order

1. **Verify credentials**: `aws sts get-caller-identity`
2. **Verify entity exists**: `aws iam get-user/get-role/get-group`
3. **Check permissions**: Caller must have `iam:*` or specific actions
4. **Check dependencies**: Attached policies, access keys, group memberships
5. **Verify eventual consistency**: Wait for propagation

## Common Issues

### Entity Already Exists

| Symptom | Cause | Resolution |
|---------|-------|------------|
| EntityAlreadyExists | User/role/group with same name | Use different name or path |
| Cannot create | Name reused from deleted entity | IAM may retain deleted entity for recovery period |

### NoSuchEntity

| Symptom | Cause | Resolution |
|---------|-------|------------|
| NoSuchEntity | Wrong name | Verify exact name (case-sensitive) |
| NoSuchEntity after create | Eventual consistency | Wait 10-30 seconds; retry get |
| NoSuchEntity for policy | Wrong policy ARN | Use full ARN including account ID |

### DeleteConflict

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Cannot delete user | Has access keys | Delete access keys first |
| Cannot delete user | Attached policies | Detach policies first |
| Cannot delete user | In groups | Remove from groups first |
| Cannot delete role | Attached policies | Detach policies first |
| Cannot delete role | Instance profiles | Remove from instance profiles |

### MalformedPolicyDocument

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Invalid JSON | Syntax error | Validate JSON with `jq` |
| Missing Version | Policy structure wrong | Add `"Version": "2012-10-17"` |
| Invalid Action | Action not valid for service | Check AWS service actions documentation |
| Invalid Resource | ARN format wrong | Use valid ARN pattern |

### LimitExceeded

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Users limit | 5000 users reached | Request quota increase via Service Quotas |
| Groups limit | 300 groups reached | Request quota increase |
| Access keys per user | 2 keys already | Delete one before creating new |

### Eventual Consistency Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Policy not effective | Not propagated | Wait 30-60 seconds |
| Cannot assume role | Role not visible to service | Verify trust policy; wait |
| User not in group | Membership not propagated | Wait; retry get-group |

## Permissions Required

| Action | Minimum IAM Permissions |
|--------|-------------------------|
| Create user | `iam:CreateUser` |
| Get user | `iam:GetUser` |
| List users | `iam:ListUsers` |
| Delete user | `iam:DeleteUser` + cleanup permissions |
| Create role | `iam:CreateRole` |
| Attach policy | `iam:AttachRolePolicy` or `iam:AttachUserPolicy` |
| Create policy | `iam:CreatePolicy` |
| Create access key | `iam:CreateAccessKey` |
| Delete access key | `iam:DeleteAccessKey` |

## Cleanup Sequence (Delete User)

```
1. Detach managed policies: detach-user-policy for each
2. Delete inline policies: delete-user-policy for each
3. Delete access keys: delete-access-key for each
4. Remove from groups: remove-user-from-group for each
5. Delete user: delete-user
```

## Cleanup Sequence (Delete Role)

```
1. Detach managed policies: detach-role-policy for each
2. Delete inline policies: delete-role-policy for each
3. Remove from instance profiles: remove-role-from-instance-profile for each
4. Delete instance profiles (optional): delete-instance-profile
5. Delete role: delete-role
```

## Policy Validation

```bash
# Validate policy JSON
cat policy.json | jq .

# Check policy syntax
aws iam simulate-custom-policy \
  --policy-input-list file://policy.json \
  --action-names s3:GetObject \
  --resource-arns arn:aws:s3:::bucket/* \
  --output json
```

## Recovery Actions

| Error | Max Retries | Action |
|-------|-------------|--------|
| 5xx ServiceFailure | 3 | Backoff 2s, 4s, 8s; HALT after 3 |
| 429 ThrottlingException | 3 | Exponential backoff |
| 400 InvalidInput | 1 | Fix; retry once |
| 409 EntityAlreadyExists | 0 | HALT; use different name |
| 409 DeleteConflict | 0 | HALT; clean dependencies first |
| 404 NoSuchEntity | 0 | HALT; verify name |

## IAM Access Analyzer

Check for public/external access:
```bash
aws accessanalyzer list-analyzers --output json
aws accessanalyzer list-findings --analyzer-arn ANALYZER_ARN --output json
```