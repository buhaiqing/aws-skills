# Troubleshooting - AWS Lambda

Lambda error codes, failure patterns, and resolution strategies.

## API Error Codes

| Error Code | Cause | Resolution |
|-----------|-------|-----------|
| ResourceNotFoundException | Function/layer/source not found | Verify name, region, and ARN |
| InvalidParameterValueException | Invalid runtime, timeout, or handler | Validate parameters against constraints |
| ResourceConflictException | Concurrent update conflict | Retry with exponential backoff |
| CodeStorageExceededException | Account code storage limit hit | Delete unused functions/versions/layers |
| PolicySizeLimitExceededException | Resource policy exceeds 20KB | Simplify policy; use multiple statements |
| ThrottlingException | Concurrency limit or rate exceeded | Retry with backoff; increase concurrency limits |
| ServiceException | AWS internal error | Retry with backoff (max 3) |
| RequestTooLargeException | Payload > 6MB (sync) or 256KB (async) | Reduce payload; use S3 for large data |
| InvalidSecurityGroupIDException | Invalid VPC security group | Verify security group exists and is in correct VPC |
| EC2AccessDeniedException | Lambda lacks EC2 Describe/ENI perms | Add ec2:DescribeNetworkInterfaces to execution role |
| EC2ThrottledException | VPC ENI creation rate exceeded | Reduce concurrent function setup; spread across subnets |
| ResourceNotReadyException | VPC/VPC endpoint not ready | Wait for resource to complete; retry |

## Invocation Errors

| Symptom | Cause | Fix |
|---------|-------|-----|
| Timeout > max configured | Function execution too long | Increase timeout; optimize code |
| Memory limit exceeded | Function uses > allocated memory | Increase memory; optimize memory usage |
| FunctionError in response | Runtime exception in handler | Check function logs; fix code error |
| StatusCode 403 | Invoke permission missing | Add lambda:InvokeFunction to resource policy |
| 502 Bad Gateway (API GW) | Function returns invalid response | Format response as API Gateway expected shape |
| 503 (async) | Function in Failed/Inactive state | Investigate Init failure; redeploy |

## Common Failure Patterns

### Cold Start Latency
- **Cause**: Large deployment package, VPC, Java/.NET runtime
- **Fix**: Use provisioned concurrency; minimize package; switch to Go/Python

### Init Failure / State = Failed
- **Cause**: Runtime download error, handler import fails, out of memory in init
- **Fix**: Check CloudWatch Logs for init errors; test locally; reduce init code

### Throttling Errors
- **Cause**: Account concurrent execution limit reached; function reserved concurrency = 0
- **Fix**: Increase reserved concurrency; request quota increase; implement retry with backoff

### Event Source Mapping Not Working
- **Cause**: IAM permissions missing; source not accessible; batch configuration wrong
- **Fix**: Verify execution role includes source service permissions; check source ARN

### VPC Function Timeout / Connection Failure
- **Cause**: No route to internet/NAT; no VPC endpoint; security group blocks outbound
- **Fix**: Add NAT gateway for internet; add VPC endpoints for AWS services; allow all outbound traffic in SG

## Diagnostic Steps

```bash
# Check function state
aws lambda get-function --function-name {{user.function_name}} --query 'Configuration.State'
# Check last 10 invocations (CloudWatch Logs)
aws logs filter-log-events --log-group-name "/aws/lambda/{{user.function_name}}" --limit 10
# Check reserved concurrency
aws lambda get-function-concurrency --function-name {{user.function_name}}
# Check event source mapping state
aws lambda list-event-source-mappings --function-name {{user.function_name}}
# Test invocation (sync)
aws lambda invoke --function-name {{user.function_name}} --payload '{"test": true}' response.json
```

## Recovery Procedures

| Situation | Action |
|-----------|--------|
| Function stuck in Failed state | Update code/configuration to retry; if persists, delete & recreate |
| Log group missing | Check function was invoked at least once; verify CloudWatch permissions |
| Quota limit hit | Request quota increase via Service Quotas console |
| Provisioned concurrency not ready | Wait up to 30 min; verify function is Active |
| VPC function needs internet | Add NAT Gateway + routes; or use VPC endpoints |