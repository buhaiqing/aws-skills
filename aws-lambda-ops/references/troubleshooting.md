# Troubleshooting - AWS Lambda

Lambda error codes, failure patterns, and resolution strategies.

## Error Classification

### Error Types

| Category | Source | Recovery |
|----------|--------|----------|
| Configuration | Invalid parameters | Fix and retry |
| Resource | Missing dependencies | Create resource |
| Quota | Limits exceeded | Request increase or cleanup |
| Runtime | Code execution failure | Debug code |
| Service | AWS infrastructure | Retry or escalate |
| Permission | IAM/access issues | Fix permissions |

## API Error Codes

### ResourceNotFoundException

**Symptom**: `Function not found: arn:aws:lambda:region:account:function:name`

**Causes**:
- Function deleted
- Incorrect function name
- Wrong region
- ARN typo

**Resolution**:
```bash
# Verify function exists
aws lambda list-functions --query "Functions[?FunctionName=='my-function']" --output json

# Check specific function
aws lambda get-function --function-name my-function --output json
```

### InvalidParameterValueException

**Symptom**: `Invalid parameter value for parameter X`

**Common Causes**:
- Memory size outside 128-10240 range
- Timeout outside 1-900 range
- Invalid runtime identifier
- Invalid handler format (must be `module.handler`)
- S3 bucket/key not found
- IAM role does not exist or invalid ARN
- VPC subnet/security group not found

**Resolution**:
```bash
# Validate parameters before create
# Memory: 128-10240 MB
# Timeout: 1-900 seconds
# Handler: module_name.handler_function (no path separators)

# Verify S3 object
aws s3 ls s3://bucket/key

# Verify IAM role
aws iam get-role --role-name lambda-execution-role
```

### ResourceConflictException

**Symptom**: `The operation cannot be performed at this time. An update is in progress`

**Causes**:
- Concurrent update to same function
- Function state is Pending/InProgress
- Previous update still processing

**Resolution**:
```python
# Wait for update to complete
import boto3
lambda_client = boto3.client('lambda')

waiter = lambda_client.get_waiter('function_updated')
waiter.wait(FunctionName='my-function', WaiterConfig={'Delay': 5, 'MaxAttempts': 60})
```

### CodeStorageExceededException

**Symptom**: `Code storage limit exceeded`

**Causes**:
- Total code storage exceeds 75GB
- Too many function versions
- Too many layer versions

**Resolution**:
```bash
# List all versions
aws lambda list-versions-by-function --function-name my-function --output json

# Delete old versions (cannot delete $LATEST or latest numbered version)
aws lambda delete-function --function-name my-function:1

# List layers
aws lambda list-layers --output json

# Delete old layer versions
aws lambda delete-layer-version --layer-name my-layer --version-number 1

# Check storage usage
aws lambda get-account-settings --output json
# JSON path: .AccountLimit.TotalCodeSizeInMB
```

### PolicySizeLimitExceededException

**Symptom**: `The policy size limit is exceeded`

**Causes**:
- Too many statements in function policy
- Policy exceeds 20KB limit
- Multiple cross-account permissions

**Resolution**:
```bash
# Get current policy
aws lambda get-policy --function-name my-function --output json

# Remove policy statement
aws lambda remove-permission \
  --function-name my-function \
  --statement-id statement-id-to-remove

# Consolidate permissions using wildcard patterns
# Instead of multiple statements per account, use:
{
  "Effect": "Allow",
  "Principal": {"AWS": "arn:aws:iam::account-id:root"},
  "Action": "lambda:InvokeFunction",
  "Resource": "arn:aws:lambda:region:account:function:name"
}
```

### ThrottlingException

**Symptom**: `Rate exceeded`

**Causes**:
- Invocation rate exceeds concurrent execution limit
- Account-level throttle (1000 concurrent default)
- Reserved concurrency limit reached
- API rate limiting (read/write operations)

**Resolution**:
```python
# Check concurrent execution usage
import boto3
cloudwatch = boto3.client('cloudwatch')

response = cloudwatch.get_metric_statistics(
    Namespace='AWS/Lambda',
    MetricName='ConcurrentExecutions',
    Dimensions=[{'Name': 'FunctionName', 'Value': 'my-function'}],
    StartTime=...,
    EndTime=...,
    Period=60,
    Statistics=['Maximum']
)

# Request concurrency increase via AWS Support
# Or set reserved concurrency
aws lambda put-function-concurrency \
  --function-name my-function \
  --reserved-concurrent-executions 500

# Implement exponential backoff in client
import time
for attempt in range(3):
    try:
        response = lambda_client.invoke(...)
        break
    except ClientError as e:
        if e.response['Error']['Code'] == 'ThrottlingException':
            time.sleep(min(2 ** attempt, 30))
            continue
        raise
```

### ServiceException

**Symptom**: `Service exception`

**Causes**:
- AWS Lambda service issue
- Regional service degradation
- Internal error (5xx)

**Resolution**:
```yaml
# Retry with exponential backoff
# Max retries: 3
# Backoff: 1s, 2s, 4s

# Check AWS Service Health Dashboard
# https://health.aws.amazon.com/health/status

# If persistent, contact AWS Support
```

### ProvisionedConcurrencyException

**Symptom**: `Provisioned concurrency configuration failed`

**Causes**:
- Insufficient account quota
- Memory configuration change during provisioned setup
- Function in pending state

**Resolution**:
```bash
# Request provisioned concurrency quota increase via AWS Support
# Wait for function to be Active before setting provisioned concurrency

aws lambda get-function --function-name my-function --query "Configuration.State"
```

## Invocation Failures

### Function Timeout

**Symptom**: `Task timed out after X seconds`

**Causes**:
- Execution exceeds configured timeout
- Network latency (VPC functions)
- Database query timeout
- Large payload processing

**Resolution**:
```yaml
# Increase timeout (max 900s)
aws lambda update-function-configuration \
  --function-name my-function \
  --timeout 60

# Optimize code
- Use connection pooling
- Implement timeout handling in SDK calls
- Use async/non-blocking operations
- Reduce payload size
- Stream processing for large data

# For VPC functions, cold start adds latency
- Consider provisioned concurrency
- Initialize connections in handler global scope
```

### Memory Exceeded

**Symptom**: `Runtime exited without providing a reason` or `OOMKilled`

**Causes**:
- Process memory exceeds allocated memory
- Memory leak
- Large data structures in memory
- Unoptimized data processing

**Resolution**:
```yaml
# Increase memory (128-10240 MB)
aws lambda update-function-configuration \
  --function-name my-function \
  --memory-size 1024

# Monitor memory usage via CloudWatch Lambda Insights
# Metric: MemoryUtilization

# Code optimization
- Free unused objects
- Use generators/streaming
- Avoid loading entire datasets
- Check for memory leaks in long-running code
```

### Runtime Error

**Symptom**: Various runtime-specific errors

**Python Errors**:
```
Runtime.ExitError: Exit error: Runtime exited without providing a reason
ImportModuleError: Unable to import module 'handler'
```

**Node.js Errors**:
```
Runtime.UserCodeSyntaxError: Syntax error in module 'handler'
Runtime.ImportModuleError: Cannot find module 'dependency'
```

**Resolution**:
```yaml
# Check deployment package structure
- Handler file must be at root or in correct path
- Handler format: module.handler_function
- Dependencies must be included or in layers

# Verify dependencies
Python: pip install -t . package_name; zip deployment.zip *
Node.js: npm install; zip -r deployment.zip *

# Check runtime compatibility
- Use supported runtime version
- Verify layer runtime compatibility
```

### Permission Denied

**Symptom**: `AccessDenied` in function logs

**Causes**:
- Missing IAM permissions for downstream services
- Execution role lacks required permissions
- Resource-based policy missing
- VPC security group rules

**Resolution**:
```yaml
# Check execution role
aws iam get-role-policy --role-name lambda-role --policy-name policy-name

# Test role permissions with IAM Policy Simulator
# https://policysim.aws.amazon.com/

# Add missing permissions
aws iam put-role-policy \
  --role-name lambda-role \
  --policy-name s3-access \
  --policy-document file://policy.json

# For VPC, verify security group allows outbound
aws ec2 describe-security-groups --group-ids sg-12345
```

### Event Source Mapping Issues

**Symptom**: `NoRecordsProcessed` or mapping state `Disabled`

**Causes**:
- Event source configuration error
- IAM permission for event source missing
- Source resource does not exist
- Batch size too large

**Resolution**:
```bash
# Check mapping state
aws lambda get-event-source-mapping --uuid mapping-uuid

# Verify event source exists and has data
# SQS: aws sqs get-queue-attributes --queue-url url --attribute-names All
# DynamoDB: aws dynamodb describe-table --table-name table
# Kinesis: aws kinesis describe-stream --stream-name stream

# Verify function permissions for source type
# SQS: lambda:InvokeFunction on queue
# DynamoDB: dynamodb:DescribeStream, dynamodb:GetRecords, dynamodb:GetShardIterator
# Kinesis: kinesis:DescribeStream, kinesis:GetRecords, kinesis:GetShardIterator
```

## Deployment Issues

### S3 Bucket Access

**Symptom**: `Unable to get deployment package from S3`

**Causes**:
- S3 bucket does not exist
- S3 key does not exist
- No permission to read bucket
- Bucket in different region

**Resolution**:
```bash
# Verify bucket and object
aws s3 ls s3://bucket-name/path/to/package.zip

# Verify bucket region
aws s3 get-bucket-location --bucket bucket-name

# Ensure Lambda execution role has S3 read permission
{
  "Effect": "Allow",
  "Action": ["s3:GetObject"],
  "Resource": "arn:aws:s3:::bucket-name/path/to/package.zip"
}
```

### Code Validation Failure

**Symptom**: `Invalid deployment package`

**Causes**:
- Zip file corrupted
- Handler not found in package
- Unsupported runtime in package
- Package exceeds size limit

**Resolution**:
```yaml
# Verify zip structure
unzip -l deployment.zip

# Handler must match package structure
# Handler: index.handler → zip contains index.js with handler function
# Handler: lambda_function.lambda_handler → zip contains lambda_function.py

# Check package size
ls -lh deployment.zip
# Direct upload: < 50MB
# Via S3: < 250MB (zip), 250MB (unzipped)

# Rebuild package correctly
# Python: zip package.zip lambda_function.py package/
# Node.js: zip -r package.zip index.js node_modules/
```

### Circular Dependency

**Symptom**: `Circular dependency between resources`

**Causes**:
- Function references itself
- Layer depends on function
- IAM role depends on function policy

**Resolution**:
```yaml
# Ensure proper resource ordering in deployment
1. Create IAM role first
2. Create function with role
3. Create layers (independent of functions)
4. Attach layers to function

# Use explicit dependencies in CloudFormation/IAM
DependsOn: RoleName
```

## Performance Issues

### High Cold Start Latency

**Symptom**: First invocation takes >1 second

**Causes**:
- Large deployment package
- Many layers attached
- VPC configuration
- Java runtime (JVM initialization)
- Complex initialization code

**Resolution**:
```yaml
# Use provisioned concurrency for critical functions
aws lambda put-provisioned-concurrency-config \
  --function-name my-function \
  --qualifier prod \
  --provisioned-concurrent-executions 10

# Optimize deployment package
- Minimize dependencies
- Use layers for shared code
- Remove unused code
- Use compiled languages (Go, Rust)

# VPC optimization
- Minimize attached security groups
- Use AWS PrivateLink instead of NAT Gateway
- Consider Lambda-only VPC

# Initialization optimization
- Move initialization outside handler (global scope)
- Lazy load dependencies
- Cache connections
```

### High Execution Duration

**Symptom**: Duration exceeds expected time

**Causes**:
- Under-provisioned memory/CPU
- Network latency
- Database query optimization
- Synchronous downstream calls

**Resolution**:
```yaml
# Increase memory (more CPU)
aws lambda update-function-configuration \
  --function-name my-function \
  --memory-size 2048  # 2GB = 2 full vCPUs

# Profile function execution
- Use X-Ray tracing
- Log timing for operations
- Use Lambda Insights for CPU metrics

# Optimize downstream calls
- Use connection pooling
- Implement caching
- Use async operations
- Batch operations
```

## Monitoring and Debugging

### CloudWatch Logs Analysis

```bash
# View recent logs
aws logs get-log-events \
  --log-group-name /aws/lambda/my-function \
  --log-stream-name stream-name \
  --limit 100

# Search logs for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/my-function \
  --filter-pattern "ERROR" \
  --start-time 1704067200000
```

### X-Ray Tracing

```python
# Enable X-Ray in function
# Environment variable: AWS_XRAY_TRACING_ENABLED=true

# Or add to code
from aws_xray_sdk.core import xray_recorder
xray_recorder.begin_segment('my-operation')
# ... code ...
xray_recorder.end_segment()
```

### Dead Letter Queue Analysis

```bash
# Check DLQ for failed async invocations
aws sqs receive-message --queue-url dlq-url --max-number-of-messages 10

# DLQ message contains original event and error details
# Parse to understand failure cause
```

## Recovery Procedures

### From Throttling

```yaml
1. Identify throttle cause (concurrency limit)
2. Check CloudWatch ConcurrentExecutions metric
3. Implement client-side retry with exponential backoff
4. Request concurrency increase via AWS Support
5. Set reserved concurrency for critical functions
```

### From Memory Exceeded

```yaml
1. Increase memory allocation
2. Profile memory usage (Lambda Insights)
3. Optimize code (free objects, streaming)
4. Reduce payload size
5. Consider splitting into smaller functions
```

### From Timeout

```yaml
1. Increase timeout (max 900s)
2. Profile execution time (X-Ray)
3. Optimize slow operations
4. Implement timeout handling in code
5. Use async/event-driven architecture for long operations
```

### From Permission Error

```yaml
1. Identify required permissions (check error message)
2. Verify execution role
3. Add missing permissions
4. Verify resource-based policies
5. Test with Policy Simulator
```

## Health Check Commands

```bash
# Quick function health check
aws lambda get-function \
  --function-name my-function \
  --query "Configuration.{State:State,Runtime:Runtime,Handler:Handler,Timeout:Timeout,MemorySize:MemorySize}" \
  --output table

# Check invocation success rate (CloudWatch)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=my-function \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Sum \
  --output json

# Check throttles
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Throttles \
  --dimensions Name=FunctionName,Value=my-function \
  --start-time ... \
  --end-time ... \
  --period 3600 \
  --statistics Sum \
  --output json
```