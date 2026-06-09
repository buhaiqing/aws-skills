# AWS CLI Usage — AWS Resource Access Manager (RAM)

## Common JSON Paths (Centralized)

```
# ResourceShare:   .resourceShare.{resourceShareArn,name,owningAccountId,allowExternalPrincipals,status,featureSet,creationTime}
# Association:     .resourceShareAssociations[].{resourceShareArn,associatedResource,principal,associationType,status,external}
# Invitation:      .resourceShareInvitations[].{resourceShareInvitationArn,resourceShareArn,name,senderAccountId,receiverAccountId,status}
# Permission:      .resourceSharePermission.{permissionArn,permissionName,permissionVersion,isAssociationDefault,status}
# Resource:        .resources[].{arn,type,resourceShareArn,resourceOwnerId,status}
# Principal:       .principals[].{id,arn,resourceShareArn,principalType}
# Policy:          .resourcePolicy.policy
```

## Command Map

| Goal | CLI Command |
|------|-------------|
| Create resource share | `aws ram create-resource-share` |
| List resource shares | `aws ram get-resource-shares` |
| Get resource share | `aws ram get-resource-shares --resource-share-arns <arn>` |
| Update resource share | `aws ram update-resource-share` |
| Delete resource share | `aws ram delete-resource-share` |
| Associate principals | `aws ram associate-resource-share` |
| Disassociate principals | `aws ram disassociate-resource-share` |
| Get associations | `aws ram get-resource-share-associations` |
| Accept invitation | `aws ram accept-resource-share-invitation` |
| Reject invitation | `aws ram reject-resource-share-invitation` |
| Get invitations | `aws ram get-resource-share-invitations` |
| List pending resources | `aws ram list-pending-invitation-resources` |
| List principals | `aws ram list-principals` |
| List resources | `aws ram list-resources` |
| Create permission | `aws ram create-permission` |
| List permissions | `aws ram list-permissions` |
| Get permission | `aws ram get-permission` |
| Associate permission | `aws ram associate-resource-share-permission` |
| Disassociate permission | `aws ram disassociate-resource-share-permission` |
| Replace permissions | `aws ram replace-permission-associations` |
| Delete permission | `aws ram delete-permission` |
| Delete permission version | `aws ram delete-permission-version` |
| Enable org sharing | `aws ram enable-sharing-with-aws-organization` |
| Get resource policy | `aws ram get-resource-policies` |
| List resource types | `aws ram list-resource-types` |
| Tag resource | `aws ram tag-resource` |
| Untag resource | `aws ram untag-resource` |

## Common Patterns

### Create and Share VPC Subnet
```bash
# Create resource share with subnet
aws ram create-resource-share \
  --name "shared-subnet-prod" \
  --resource-arns "arn:aws:ec2:us-east-1:123456789012:subnet/subnet-abc123" \
  --principals "222222222222" \
  --allow-external-principals \
  --region us-east-1 \
  --output json
```

### Accept Invitation and Verify
```bash
# Accept
aws ram accept-resource-share-invitation \
  --resource-share-invitation-arn "arn:aws:ram:us-east-1:111111111111:resource-share-invitation/abc-123" \
  --region us-east-1 \
  --output json

# Verify association
aws ram get-resource-share-associations \
  --association-type RESOURCE_SHARE \
  --resource-share-arns "arn:aws:ram:us-east-1:123456789012:resource-share/xyz-789" \
  --region us-east-1 \
  --output json
```

### List All Shared Resources in Account
```bash
aws ram list-resources \
  --region us-east-1 \
  --output json
```

### Enable Organization Sharing
```bash
aws ram enable-sharing-with-aws-organization \
  --region us-east-1 \
  --output json
```

## Retry Strategy

| Error Code | Retry? | Max Retries |
|------------|--------|-------------|
| InvalidParameter | No | 0 |
| MalformedArn | No | 0 |
| ServerException | Yes | 3 with exponential backoff |
| ThrottlingException | Yes | 3 with backoff |
| OperationNotPermittedException | No | HALT — check org settings |
| ResourceShareInvitationAlreadyRejectedException | No | HALT — invitation already rejected |
