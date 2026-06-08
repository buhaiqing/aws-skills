# Security Hub Troubleshooting

Common Security Hub error codes, recovery procedures, and operational troubleshooting.

## Error Reference

### Access Errors
| Error | Resolution |
|-------|-----------|
| AccessDeniedException | HALT — add `securityhub:*` IAM permissions |
| InvalidAccessException | HALT — Security Hub not enabled in this region |

### Resource Errors
| Error | Resolution |
|-------|-----------|
| ResourceNotFoundException | HALT — verify ARN/ID spelling and region |
| InvalidInputException | HALT — fix request parameters (check JSON format) |

### Limit Errors
| Error | Resolution |
|-------|-----------|
| LimitExceededException | HALT — request quota increase or delete unused resources |
| ResourceConflictException | HALT — resource already exists or in conflicting state |

### Service Errors
| Error | Resolution |
|-------|-----------|
| InternalException | RETRY — AWS internal error, max 3 retries |
| ThrottlingException | Exponential backoff, max 3 retries |

## Throttling (429)
```python
import time, math
def exponential_backoff(attempt, base=0.5, max_delay=60):
    time.sleep(min(base * math.pow(2, attempt), max_delay))
```

## Finding Import Issues
**Finding rejected**: Check `UnprocessedFindings` in response.
Common causes:
- Invalid `SchemaVersion` — must be `2018-10-08`
- Missing required fields: `Id`, `ProductArn`, `AwsAccountId`, `Types`, `CreatedAt`, `UpdatedAt`, `Severity`, `Title`, `Description`
- `ProductArn` must match the product that is enabled for import

## Hub Not Enabled
```bash
aws securityhub describe-hub --region {{user.region}}
# If ResourceNotFoundException → enable first:
aws securityhub enable-security-hub --region {{user.region}}
```

## Standards Not Visible
```bash
# List available standards
aws securityhub describe-standards --region {{user.region}}
# Check enabled standards
aws securityhub get-enabled-standards --region {{user.region}}
```

## Controls Disabled Unexpectedly
```bash
# Check control status
aws securityhub describe-standards-controls \
  --standards-subscription-arn {{user.standards_subscription_arn}} \
  --region {{user.region}} \
  --query 'Controls[?ControlStatus==`DISABLED`].{Id:ControlId,Reason:DisabledReason}'
```

## Automation Rule Not Firing
- Verify rule status: `list-automation-rules` → `RuleStatus == ENABLED`
- Check criteria match actual finding fields
- Lower `RuleOrder` values are evaluated first — ensure no earlier rule conflicts
- Rules only apply to NEW findings, not retroactively

## Configuration Policy Issues
```bash
# Verify policy exists
aws securityhub get-configuration-policy --identifier {{user.policy_id}} --region {{user.region}}
# Check associations
aws securityhub list-configuration-policy-associations --region {{user.region}}
```

## Recovery Procedures
**Finding import failure**: Check `UnprocessedFindings` → fix field errors → retry batch.
**Hub disable failure**: Ensure no Organization-level enforcement; disable from admin account.
**Control update failure**: Verify standards subscription ARN is correct and enabled.
**Automation rule failure**: Check criteria JSON syntax; verify finding field names.
