# Troubleshooting — AWS Config

## API Error Codes

| Error | HTTP | Meaning | Action |
|-------|------|---------|--------|
| InvalidParameter | 400 | Bad parameter value | Fix per API docs |
| InvalidParameterValue | 400 | Value out of range/fmt | Check constraint (e.g., retention 1–2557 days) |
| InvalidConfigurationRecorderName | 400 | Recorder name bad | Alphanumeric, hyphens, underscores only; 1–128 chars |
| NoSuchConfigRuleException | 400 | Rule does not exist | Verify name via `describe-config-rules` |
| NoSuchConfigurationRecorder | 400 | Recorder does not exist | Verify name via `describe-configuration-recorders` |
| NoSuchDeliveryChannel | 400 | Channel does not exist | Verify name via `describe-delivery-channels` |
| MaxNumberOfConfigRulesExceeded | 400 | Rule quota reached (default 200) | HALT; request quota increase |
| InsufficientPermissionsException | 400 | IAM role missing perms | Check service-linked role + IAM policy |
| ResourceNotFoundException | 404 | Resource not found | Verify ARN/name/region |
| ThrottlingException | 429 | Rate limit | Backoff; retry 3x |
| InternalError | 500 | AWS service error | Retry 3x; HALT if persists |
| LastDeliveryChannelDeleteFailed | 400 | Delivery in progress | Wait and retry |
| LimitExceeded | 400 | Quota exceeded | Delete unused or request increase |
| ConformancePackTemplateValidationException | 400 | Template invalid | Check YAML/JSON; verify SSM URI |
| NoSuchAggregator | 400 | Aggregator not found | Verify name via `describe-configuration-aggregators` |

## Diagnostic Order

1. `describe-configuration-recorders` + `describe-configuration-recorder-status` — recorder state
2. `describe-delivery-channels` — channel configured + S3/SNS valid
3. `describe-config-rules` — rules exist + ACTIVE state
4. `describe-config-rule-evaluation-status` — last evaluation times/errors
5. `get-compliance-details-by-config-rule --compliance-types NON_COMPLIANT` — non-compliant resources
6. `get-compliance-summary-by-config-rule` — quick overview counts
7. `describe-conformance-packs` — pack status
8. `describe-configuration-aggregators` — aggregator state
9. `aws cloudtrail lookup-events` — if Config not receiving API events

## Operational Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Recorder not recording | No SLR (`AWSServiceRoleForConfig`) | Create SLR via IAM |
| Recorder not recording | Delivery channel missing | Create delivery channel with valid S3 bucket |
| Rules not evaluating | Recorder stopped | `start-configuration-recorder` |
| Rules stuck INSUFFICIENT_DATA | No matching resources | Wait for changes or trigger manual evaluation |
| Delivery not reaching S3 | Bucket missing/bad policy | Verify bucket exists + Config bucket policy (put-object for config.amazonaws.com) |
| Delivery not reaching SNS | Topic missing/no subscription | Verify topic exists + active subscription |
| "No such delivery channel" | Not yet configured | `put-delivery-channel` first |
| Managed rule not found | Wrong identifier or region | Use `describe-config-rules` to list available; check region support |
| Aggregator empty | No authorized accounts | `put-aggregation-authorization` for source accounts |
| Conformance pack failed | Template validation error | Check YAML syntax; verify SSM URI accessible |
| Retention config rejected | Out of range | Must be 1–2557 days |
| Max rules exceeded | Quota limit reached | Delete unused rules or request increase |
| Custom rule fails | Lambda error | Check Lambda CloudWatch logs; verify function permissions |

## Config Not Enabled

| Symptom | Resolution |
|---------|------------|
| "No recorder configured" | Full setup: SLR → recorder → delivery channel → start recorder |
| "Config not enabled" | Run full setup sequence from SKILL.md |
| Config not available in region | Check regional availability; use supported region |

## Multi-Account/Region Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Aggregator shows no data | No org trusted access | Enable trusted access in AWS Organizations |
| Aggregator shows no data | No authorization for account | `put-aggregation-authorization` per account |
| Org rule fails | Not in management account | Run from management/organizational unit root |
| Cross-account rule fails | Missing SLR in member account | Create `AWSServiceRoleForConfig` in each member account |

## Compliance Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Resources NON_COMPLIANT | Real config drift | Remediate resource to match rule |
| Rule not evaluating recently | Evaluation schedule issue | `start-config-rules-evaluation` |
| Compliance results empty | No evaluations triggered | Trigger evaluation manually |
| Custom rule fails | Lambda invokation error | Check Lambda permissions + CloudWatch logs |
| NOT_APPLICABLE | Resource type mismatch | Check rule Scope.ComplianceResourceTypes |

## Dependency Issues

| Resource | Error | Resolution |
|----------|-------|------------|
| S3 bucket | Not found / no policy | Verify bucket exists + Config `PutObject` policy |
| SNS topic | Not found / no subscription | Verify topic + active Config subscription |
| Lambda | Not found / no invoke perms | Verify function ARN + `lambda:InvokeFunction` permission |
| IAM role | Not found / bad policy | Verify SLR exists + `config:Put*` permissions |
| Organizations | Trusted access disabled | Enable in Organizations console/CLI |
