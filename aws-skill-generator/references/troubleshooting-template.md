# Troubleshooting Template (AWS Services)

Use this template when creating `references/troubleshooting.md` for a new AWS service skill.

## Common Error Codes Template

```markdown
## Common API Error Codes

| Error Code | HTTP | Meaning | Agent Action |
|------------|------|---------|--------------|
| InvalidParameter | 400 | Request validation failed | Fix args per AWS API docs |
| InvalidParameterValue | 400 | Specific field invalid | Check allowed values |
| MissingParameter | 400 | Required field omitted | Add missing parameter |
| AccessDenied | 403 | IAM permission insufficient | HALT; user updates IAM policy |
| UnauthorizedOperation | 403 | Operation not permitted | HALT; check IAM permissions |
| ResourceNotFound | 404 | Resource does not exist | Verify resource ID/ARN |
| QuotaExceeded | 400/402 | Service limit reached | HALT; user requests quota increase |
| ServiceQuotaExceededException | 400 | Service quota limit | HALT; request increase |
| ThrottlingException | 429 | Rate limit exceeded | Retry with exponential backoff |
| RequestLimitExceeded | 429 | Too many requests | Backoff; reduce request rate |
| InternalError | 500 | AWS service error | Retry 3x; HALT with correlation ID |
| ServiceUnavailable | 503 | Service temporarily down | Retry 3x; HALT |
| InsufficientCapacity | 500 | AWS capacity unavailable | Retry later or different region |
```

## Diagnostic Order Template

```markdown
## Diagnostic Order (General)

1. **Verify credentials**: `aws sts get-caller-identity`
2. **Verify region**: Check `AWS_DEFAULT_REGION` or pass `--region`
3. **Describe resource by ID**: Get current state and configuration
4. **List related resources**: Check dependencies and associations
5. **Check CloudTrail**: For audit trail of API calls
6. **Check service-specific metrics**: CloudWatch dashboards
```

## Service-Specific Troubleshooting Sections

### Section 1: Credential Issues

```markdown
## Credential Issues

| Symptom | Diagnosis | Resolution |
|---------|-----------|------------|
| "Unable to locate credentials" | No credentials configured | Configure via env vars or ~/.aws/ |
| "AccessDenied" | Missing IAM permission | Add required policy to IAM role/user |
| "Token refresh required" | SSO session expired | Run `aws sso login` |
| "SignatureDoesNotMatch" | Wrong secret key or clock skew | Verify credentials; sync clock |
```

### Section 2: Resource State Issues

```markdown
## Resource State Issues

| State | Problem | Resolution |
|-------|---------|------------|
| stuck in "creating" | Backend provisioning issue | Check CloudTrail; contact AWS support |
| stuck in "stopping" | Hypervisor issue | Force stop (may require AWS support) |
| unexpected state transition | Configuration conflict | Review logs; check dependencies |
```

### Section 3: Performance Issues

```markdown
## Performance Issues

| Symptom | Possible Cause | Resolution |
|---------|----------------|------------|
| Slow API response | Regional endpoint issue | Try different region or endpoint |
| Timeout on large operations | Request size exceeds limit | Break into smaller batches |
| High latency | Network/routing issue | Check VPC endpoints, region proximity |
```

### Section 4: Dependency Issues

```markdown
## Dependency Issues

| Error | Missing Dependency | Resolution |
|-------|-------------------|------------|
| "VPC not found" | VPC ID invalid | Verify VPC exists in correct region |
| "Subnet not found" | Subnet ID or AZ mismatch | Check subnet in same region/AZ |
| "SecurityGroup not found" | SG ID invalid | Verify SG exists |
| "Invalid IAM role" | Role ARN or policy issue | Verify role exists and has trust policy |
```

## Example Troubleshooting Entry Format

```markdown
### Issue: Instance fails to start

**Symptoms**:
- EC2 instance stuck in "pending" state
- Error message: "InsufficientInstanceCapacity"

**Diagnosis Steps**:
1. Check instance type availability: `aws ec2 describe-instance-type-offerings`
2. Check current capacity in region: `aws ec2 describe-instance-types`
3. Verify region has sufficient capacity

**Resolution Options**:
- Option A: Use different instance type
- Option B: Try different Availability Zone
- Option C: Try different region
- Option D: Wait and retry (capacity fluctuates)
```

## CloudWatch Logs Integration

```markdown
## CloudWatch Logs for Debugging

### Check recent API errors
```bash
aws logs filter-log-events \
  --log-group-name aws/[service]/errors \
  --start-time $(date -u -d '-1 hour' +%s)000 \
  --output json
```

### Metric-based troubleshooting
```bash
aws cloudwatch get-metric-data \
  --namespace AWS/[Service] \
  --metric-name ErrorCount \
  --output json
```
```

## Support Escalation Criteria

```markdown
## When to Contact AWS Support

| Scenario | Severity | Action |
|----------|----------|--------|
| Production outage affecting users | Critical | Immediate support ticket |
| Data loss or corruption | Critical | Immediate support ticket |
| Security breach indicator | Critical | Immediate support + security review |
| Persistent 5xx errors after retries | High | Support ticket with correlation IDs |
| Unexpected quota limit behavior | Medium | Quota increase request |
| Feature request or clarification | Low | AWS forums or documentation feedback |
```