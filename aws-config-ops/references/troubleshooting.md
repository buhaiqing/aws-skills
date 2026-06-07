# Troubleshooting — AWS Config

## Common API Error Codes

| Error | HTTP | Meaning | Agent Action |
|-------|------|---------|--------------|
| InvalidParameter | 400 | Invalid parameter | Fix args per API docs |
| NoSuchConfigRuleException | 400 | Rule does not exist | Verify rule name |
| NoSuchConfigurationRecorder | 400 | Recorder does not exist | Verify recorder name |
| NoSuchDeliveryChannel | 400 | Delivery channel does not exist | Verify channel name |
| MaxNumberOfConfigRulesExceeded | 400 | Rule quota reached | HALT; request increase |
| InsufficientPermissionsException | 400 | IAM role missing | Create service-linked role |
| ResourceNotFoundException | 404 | Resource not found | Verify resource name/ARN |
| ThrottlingException | 429 | Rate limit | Backoff; retry 3x |
| InternalError | 500 | AWS service error | Retry 3x; HALT |

## Diagnostic Order

1. **Describe recorder**: `aws configservice describe-configuration-recorders`
2. **Check recorder status**: `aws configservice describe-configuration-recorder-status`
3. **Describe delivery channel**: `aws configservice describe-delivery-channels`
4. **Describe rules**: `aws configservice describe-config-rules`
5. **Check rule evaluation status**: `aws configservice describe-config-rule-evaluation-status`
6. **Check CloudTrail**: `aws cloudtrail lookup-events`

## Common Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Recorder not recording | No service-linked role | Create `AWSServiceRoleForConfig` |
| Rules not evaluating | Recorder stopped | `start-configuration-recorder` |
| Delivery not working | S3 bucket missing | Create/pick valid S3 bucket |
| "No such delivery channel" | Not configured yet | `put-delivery-channel` first |
| Rule stuck INSUFFICIENT_DATA | No resources to evaluate | Wait for resource changes or trigger evaluation |
| Managed rule not found | Wrong identifier or region | Use `describe-config-rules` to list available |
| Aggregator not showing data | No authorized accounts | Authorize source accounts: `put-aggregation-authorization` |
| Conformance pack failed | Template validation error | Check YAML/JSON syntax; verify SSM URI |
| Max rules exceeded | Quota limit | Delete unused rules or request increase |

## Config Not Enabled

| Symptom | Resolution |
|---------|------------|
| "No recorder configured" | `put-configuration-recorder` + `put-delivery-channel` + `start-configuration-recorder` |
| "Config not enabled" | Enable via CLI: follow full setup sequence |
| AWS Config is not available in this region | Check regional availability list |

## Compliance Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Resources NON_COMPLIANT | Config drift detected | Remediate per rule annotation |
| Rule not evaluating recently | Evaluation schedule issue | `start-config-rules-evaluation` |
| Compliance results empty | No triggered evaluations | Trigger evaluation manually |
| Custom rule fails | Lambda function error | Check Lambda logs in CloudWatch |

## Dependency Issues

| Error | Resolution |
|-------|------------|
| S3 bucket not found | Verify bucket exists and has correct Config bucket policy |
| SNS topic not found | Verify topic exists and has Config subscription |
| Lambda function not found | Verify function ARN and region |
| Organization access not enabled | Enable Trusted Access in Organizations