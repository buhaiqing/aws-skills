# Troubleshooting — AWS Resource Access Manager (RAM)

## Common API Error Codes

| Error | HTTP | Meaning | Agent Action |
|-------|------|---------|--------------|
| InvalidParameter | 400 | Invalid parameter | Fix args per API docs |
| MalformedArn | 400 | Bad ARN format | Verify ARN syntax |
| ServerException | 500 | AWS service error | Retry 3x; HALT |
| ThrottlingException | 429 | Rate limit | Backoff; retry 3x |
| OperationNotPermittedException | 403 | Org/sharing config issue | Check Organizations settings |
| ResourceShareInvitationAlreadyRejectedException | 409 | Invitation rejected | HALT — already rejected |

## Diagnostic Order

1. **Check resource share**: `aws ram get-resource-shares --resource-share-arns <arn>`
2. **Check associations**: `aws ram get-resource-share-associations --resource-share-arns <arn>`
3. **Check invitations**: `aws ram get-resource-share-invitations`
4. **Check pending resources**: `aws ram list-pending-invitation-resources --resource-share-invitation-arn <arn>`
5. **Check org status**: `aws organizations describe-organization`
6. **Check CloudTrail**: `aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=CreateResourceShare`

## Common Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Share not appearing | Pending state | Wait for activation or accept invitation |
| Resource not accessible | Invitation not accepted | `accept-resource-share-invitation` |
| Cross-account share fails | External not allowed | `update-resource-share --allow-external-principals` |
| Org sharing not working | RAM not enabled | `enable-sharing-with-aws-organization` |
| Principal not found | Wrong account ID | Verify account ID and org membership |
| Permission denied | IAM missing ram:* | Add RAM permissions to IAM policy |
| Share stuck DELETING | Dependent associations | Disassociate all principals/resources first |
| Invitation expired | > 12 hours old | Request new share from owner |

## Organization Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Org sharing unavailable | Not org member | Verify account is in AWS Organizations |
| OU sharing fails | Wrong OU ID | Verify OU ID matches org structure |
| RAM not enabled | Trusted access missing | Enable via console or `enable-sharing-with-aws-organization` |

## Cross-Account Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Invitation not received | Wrong receiver ID | Verify receiver account ID |
| Resource not visible after accept | Propagation delay | Wait 1-2 minutes; recheck |
| Access denied after share | IAM policy missing | Add IAM permissions for shared resource type |
