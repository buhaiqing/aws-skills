---
name: aws-lambda-ops
description: >-
  Use when the user needs to create, deploy, configure, or manage AWS Lambda
  serverless functions; work with Lambda layers, versions, and aliases; set up
  event source mappings with SQS, SNS, DynamoDB, or Kinesis; configure function
  settings like memory, timeout, runtime, and environment variables; invoke
  functions synchronously or asynchronously; configure provisioned concurrency
  or dead-letter queues for error handling; or troubleshoot Lambda invocation
  errors, even if they don't say "Lambda" and instead say "deploy a serverless
  function", "set up an event-driven function", "configure a Lambda function",
  "manage function layers", or "create an event source mapping for AWS".
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to Lambda endpoints.
metadata:
  author: aws
  version: "1.0.0"
  last_updated: "2026-05-15"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_DEFAULT_REGION
    - AWS_SESSION_TOKEN
---
# AWS Lambda Ops Skill

AWS Lambda serverless compute operations skill for AI Agent automation.

## Common JSON Paths (Centralized)

```
# Create Function:   .FunctionArn
# Update Code:       .{FunctionArn,State,Version}
# Update Config:     .{FunctionArn,Timeout,MemorySize,Runtime}
# Invoke:            .StatusCode  (200=sync, 202=async)
# List Functions:    .Functions[].{FunctionName,FunctionArn,Runtime}
# Create ESM:        .UUID
# Publish Layer:     .LayerVersionArn
# Get Function:      .Configuration.{FunctionArn,State,LastModified}
```

## Trigger & Scope

### SHOULD Use When
- User requests Lambda function create/update/delete/invoke
- Layer management operations (publish, list, attach)
- Event source mapping configuration (SQS, SNS, DynamoDB, Kinesis)
- Alias and version management
- Function configuration changes (memory, timeout, runtime, handler)
- Lambda deployment or rollback scenarios
- Troubleshooting Lambda invocation failures

### SHOULD NOT Use When
- API Gateway configuration → delegate to: `aws-apigateway-ops`
- DynamoDB table operations → delegate to: `aws-dynamodb-ops`
- SQS queue management → delegate to: `aws-sqs-ops`
- SNS topic operations → delegate to: `aws-sns-ops`
- IAM role creation → delegate to: `aws-iam-ops` (only handles execution role attachment)
- VPC configuration → delegate to: `aws-vpc-ops` (Lambda only consumes VPC settings)

### Delegation
| Condition | Skill |
|-----------|-------|
| Event source needs source service (SQS/SNS/DynamoDB) | Delegate to respective skill for source setup |
| IAM execution role needed | Request from `aws-iam-ops`, attach in Lambda skill |

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | MUST be set; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | MUST be set; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Optional; default per skill |
| `{{env.AWS_SESSION_TOKEN}}` | Runtime env | Required for STS temp creds |
| `{{user.function_name}}` | User input | Ask once; validate format |
| `{{user.runtime}}` | User input | Ask once; validate supported runtime |
| `{{user.handler}}` | User input | Ask once; format: module.handler |
| `{{user.code_location}}` | User input | S3 bucket/key or local zip path |
| `{{user.execution_role_arn}}` | User input | Must be valid IAM role ARN |

**Never** ask for AWS credentials. **Never** hardcode secrets.

## Flow Pattern

```
Pre-flight → Execute → Validate → Recover
```

**Pre-flight**: `aws --version` + `aws sts get-caller-identity`. Verify function count < account limit, code size < 75MB (zipped). For event source mapping, verify source resource exists.

**CLI (primary)**: `aws lambda [command] --region {{r.region}} --output json` — see [references/aws-cli-usage.md](references/aws-cli-usage.md).

**boto3 (fallback)**: After 3 CLI failures, switch to SDK — see [references/boto3-sdk-usage.md](references/boto3-sdk-usage.md).

**Validate**: Wait for State=Active (create) or Successful (update) — max 300s. Invocation: StatusCode=200 (sync) or 202 (async). Event source: State=Enabled.

**Common Recovery**:
| Error | Action |
|-------|--------|
| InvalidParameterValue (400) | Fix args; retry once |
| ResourceNotFoundException | HALT; verify resource exists |
| CodeStorageExceededException | HALT; clean unused versions/layers |
| ThrottlingException (429) | Backoff, retry 3x |
| ServiceException (5xx) | Retry 3x; HALT |

## Safety Gates

### Destructive Operations
```
⚠️ DESTRUCTIVE: {{operation}} will permanently remove {{user.function_name}}.
All versions, aliases, and event source mappings will be deleted.
Proceed? [yes/no]:
```

| Action | Gate Required |
|--------|---------------|
| delete-function | Human confirmation |
| delete-event-source-mapping | Human confirmation |
| delete-layer-version | Human confirmation |

## Execution Examples

### Create Function
```bash
aws lambda create-function \
  --function-name {{user.function_name}} --runtime {{user.runtime}} \
  --role {{user.execution_role_arn}} --handler {{user.handler}} \
  --code S3Bucket={{user.s3_bucket}},S3Key={{user.s3_key}} \
  --timeout {{user.timeout}} --memory-size {{user.memory_size}}
```

### Update Function Code
```bash
aws lambda update-function-code \
  --function-name {{user.function_name}} \
  --s3-bucket {{user.s3_bucket}} --s3-key {{user.s3_key}} --publish
```

### Invoke Function
```bash
aws lambda invoke --function-name {{user.function_name}} \
  --invocation-type RequestResponse --payload '{{user.payload}}' response.json
# Async: --invocation-type Event
```

### Create Event Source Mapping
```bash
aws lambda create-event-source-mapping \
  --function-name {{user.function_name}} --event-source-arn {{user.source_arn}} \
  --batch-size {{user.batch_size}} --maximum-batching-window-in-seconds {{user.batch_window}}
```

### Publish Layer Version
```bash
aws lambda publish-layer-version \
  --layer-name {{user.layer_name}} --description "{{user.layer_desc}}" \
  --content S3Bucket={{user.s3_bucket}},S3Key={{user.s3_key}} \
  --compatible-runtimes {{user.runtime1}} {{user.runtime2}}
```

## Validation Criteria

| Operation | Success Indicator | JSON Path |
|-----------|-------------------|-----------|
| create-function | State = Active | `.State` |
| update-function-code | State = Successful | `.State` |
| invoke (sync) | StatusCode = 200 | `.StatusCode` |
| invoke (async) | StatusCode = 202 | `.StatusCode` |
| create-event-source-mapping | State = Enabled | `.State` |
| publish-version | Version number returned | `.Version` |

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](../aws-skill-generator/references/integration.md)