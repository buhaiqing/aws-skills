# aws-lambda-ops

AWS Lambda serverless compute operations skill for AI Agent automation.

## Triggers

**SHOULD activate when**:
- User requests Lambda function create/update/delete/invoke
- Layer management operations (publish, list, attach)
- Event source mapping configuration (SQS, SNS, DynamoDB, Kinesis)
- Alias and version management
- Function configuration changes (memory, timeout, runtime, handler)
- Lambda deployment or rollback scenarios
- Troubleshooting Lambda invocation failures

**SHOULD-NOT activate when**:
- API Gateway configuration (→ aws-apigateway-ops)
- DynamoDB table operations (→ aws-dynamodb-ops)
- SQS queue management (→ aws-sqs-ops)
- SNS topic operations (→ aws-sns-ops)
- IAM role creation (→ aws-iam-ops) - only handles Lambda execution role attachment
- VPC configuration (→ aws-vpc-ops) - Lambda only consumes VPC settings

**Delegation**:
- Event source requires source service (SQS/SNS/DynamoDB) → delegate to respective skill for source setup
- IAM execution role needed → request from aws-iam-ops, attach in Lambda skill

## Scope

| Capability | Included | Boundary |
|------------|----------|----------|
| Function CRUD | Yes | create, update-code, update-config, delete |
| Function invocation | Yes | sync, async, event invocation |
| Layer management | Yes | publish, list, attach to function |
| Version & Alias | Yes | publish-version, create-alias, update-alias |
| Event source mappings | Yes | create, list, delete mappings |
| Function configuration | Yes | memory, timeout, runtime, environment variables |
| IAM execution role | Attach only | Role creation delegated to aws-iam-ops |
| VPC configuration | Attach only | Subnet/security group creation delegated |
| Dead Letter Queue | Configure only | SQS/SNS creation delegated |

## Variable Convention

| Placeholder | Source | Rule |
|-------------|--------|------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Environment | MUST be set; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Environment | MUST be set; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Environment | Optional; default per skill |
| `{{user.function_name}}` | User input | Ask once; validate format |
| `{{user.runtime}}` | User input | Ask once; validate supported runtime |
| `{{user.handler}}` | User input | Ask once; validate format (module.handler) |
| `{{user.code_location}}` | User input | S3 bucket/key or local zip path |
| `{{user.execution_role_arn}}` | User input | Must be valid IAM role ARN |

**Never** ask for AWS credentials. **Never** hardcode secrets.

## Flow Pattern

```
Pre-flight → Execute → Validate → Recover
```

### Pre-flight

**Step 1: Check CLI**
```bash
aws --version
```
Log: `[OK] AWS CLI v2.x.x detected` or `[FAIL] AWS CLI not found. Install: uv pip install awscli`

**Step 2: Load & Verify Credentials**
```bash
aws sts get-caller-identity --output json
```

Log format:
```
[SKILL] Loading AWS credentials...
[OK]   AWS_DEFAULT_REGION={{env.AWS_DEFAULT_REGION}} (from .env)
[OK]   AWS_ACCESS_KEY_ID=**** (from .env, masked)
[OK]   Credential verification passed
[OK]   Identity: arn:aws:iam::{{env.AWS_ACCOUNT_ID}}:user/xxx
```

On failure:
```
[FAIL] AWS credential verification failed.
AWS Error: <exact error message>
Action: See references/integration.md → Error Messages for diagnosis.
```

3. **CLI available**: `aws lambda help` returns valid output
4. **Region**: Use `{{env.AWS_DEFAULT_REGION}}` or default `us-east-1`
5. **Quota check**: Validate function count < account limit, code size < 75MB (zipped)
6. **Dependencies**: For event source mapping, verify source resource exists

### Execute

1. **Primary path**: AWS CLI `aws lambda [command] --output json`
2. **Fallback path**: boto3 SDK after 3 CLI failures

**Always** use `--output json` for machine-parseable results.

### Validate

1. **Poll until terminal**: Use `waiter` for function state (Active, Updated)
2. **Max wait**: 300 seconds for create/update operations
3. **Invocation validation**: Check response StatusCode (200 = success)
4. **Event source mapping**: Poll until state = Enabled/Disabled

### Recover

| Error Type | Recovery Action |
|------------|-----------------|
| InvalidParameterValue (400) | Fix args; retry once with corrected values |
| ResourceNotFoundException | HALT; verify resource exists before retry |
| CodeStorageExceededException | HALT; delete unused versions/layers |
| PolicySizeLimitExceededException | HALT; consolidate policies |
| ThrottlingException (429) | Exponential backoff; max 3 retries |
| ServiceException (5xx) | Retry 3x; then HALT |
| ProvisionedConcurrencyException | HALT; request quota increase |

## Safety Gates

### Destructive Operations

**Function deletion** requires explicit human confirmation:
```
⚠️ DESTRUCTIVE: delete-function will permanently remove {{user.function_name}}
This action cannot be undone. All versions, aliases, and event source mappings will be deleted.

Proceed? [yes/no]: {{user.confirmation}}
```

**Only proceed if** `{{user.confirmation}}` == `yes` (exact match, case-insensitive).

### Protected Actions

| Action | Gate Required |
|--------|---------------|
| delete-function | Human confirmation |
| delete-event-source-mapping | Human confirmation |
| delete-layer-version | Human confirmation |
| publish-version | Auto (creates immutable version) |

## Execution Examples

### Create Function

```
aws lambda create-function \
  --function-name {{user.function_name}} \
  --runtime {{user.runtime}} \
  --role {{user.execution_role_arn}} \
  --handler {{user.handler}} \
  --code S3Bucket={{user.s3_bucket}},S3Key={{user.s3_key}} \
  --timeout {{user.timeout}} \
  --memory-size {{user.memory_size}} \
  --output json
```

### Update Function Code

```
aws lambda update-function-code \
  --function-name {{user.function_name}} \
  --s3-bucket {{user.s3_bucket}} \
  --s3-key {{user.s3_key}} \
  --output json
```

### Invoke Function

```
aws lambda invoke \
  --function-name {{user.function_name}} \
  --invocation-type Event|RequestResponse \
  --payload '{{user.payload_json}}' \
  response.json \
  --output json
```

### Create Event Source Mapping

```
aws lambda create-event-source-mapping \
  --function-name {{user.function_name}} \
  --event-source-arn {{user.source_arn}} \
  --batch-size {{user.batch_size}} \
  --maximum-batching-window-in-seconds {{user.batch_window}} \
  --output json
```

### Publish Layer Version

```
aws lambda publish-layer-version \
  --layer-name {{user.layer_name}} \
  --description "{{user.layer_description}}" \
  --content S3Bucket={{user.s3_bucket}},S3Key={{user.s3_key}} \
  --compatible-runtimes {{user.runtime1}} {{user.runtime2}} \
  --output json
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
| create-alias | AliasArn returned | `.AliasArn` |

## Integration

See `references/integration.md` for:
- boto3 SDK patterns and error handling
- CLI JSON output paths verified with real runs
- Troubleshooting common Lambda errors
- Quota limits and pricing considerations