# AWS Step Functions Ops Skill

AWS Step Functions operational skill for AI Agent automation.

## Triggers

**SHOULD activate when:**
- User requests state machine creation or deletion
- User needs to start/stop executions
- User asks about Step Functions
- User mentions "state machine", "workflow", "execution"
- User needs to describe execution history
- User asks about error handling or retries

**SHOULD-NOT activate when:**
- Lambda operations only (use `aws-lambda-ops`)
- EventBridge rules (use `aws-eventbridge-ops`)
- Simple queue operations (use `aws-sqs-ops`)

**Delegation:**
- Lambda → `aws-lambda-ops` (Lambda functions)
- IAM → `aws-iam-ops` (Execution role)
- CloudWatch → `aws-cloudwatch-ops` (Metrics)

## Scope

| Operation | Supported | Safety Gate |
|-----------|-----------|-------------|
| Create State Machine | Yes | None |
| Delete State Machine | Yes | **Human confirmation** |
| Update State Machine | Yes | None |
| Start Execution | Yes | None |
| Stop Execution | Yes | None |
| Describe Execution | Yes | None |
| List Executions | Yes | None |

## Variable Convention

| Variable | Source | Example |
|----------|--------|---------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Environment | Never ask user |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Environment | Never ask user |
| `{{env.AWS_DEFAULT_REGION}}` | Environment | us-east-1 |
| `{{user.StateMachineArn}}` | User input | arn:aws:states:... |
| `{{user.ExecutionArn}}` | User input | arn:aws:states:... |
| `{{user.RoleArn}}` | User input | arn:aws:iam::...:role/... |

## Execution Flow

### Pre-flight
```
1. Check AWS CLI: aws --version
2. Validate credentials: aws sts get-caller-identity
3. Verify IAM role exists: aws iam get-role --role-name {{user.RoleName}}
4. Check state machine definition syntax
```

### Execute (Primary: CLI)
```
aws stepfunctions create-state-machine \
  --name "{{user.StateMachineName}}" \
  --definition '{{user.Definition}}' \
  --role-arn "{{user.RoleArn}}" \
  --type STANDARD \
  --output json
```

### Execute (Fallback: boto3)
```python
import boto3
sfn = boto3.client('stepfunctions')
response = sfn.create_state_machine(
    name='{{user.StateMachineName}}',
    definition='{{user.Definition}}',
    roleArn='{{user.RoleArn}}'
)
```

## Safety Gates

### Delete State Machine
```
BEFORE delete-state-machine:
1. Check for running executions
2. Stop active executions
3. Ask: "Type 'DELETE {{user.StateMachineName}}' to confirm"
```

## Output Convention

Key JSON paths:
- `.stateMachineArn` - ARN
- `.executionArn` - execution ARN
- `.status` - RUNNING/SUCCEEDED/FAILED
- `.output` - execution output
- `.startDate` - start timestamp

## Related Skills

- `aws-lambda-ops` - Lambda functions
- `aws-iam-ops` - IAM roles
- `aws-cloudwatch-ops` - Metrics

## Reference Files

- `references/aws-cli-usage.md`
- `references/boto3-sdk-usage.md`
- `references/core-concepts.md`
- `references/troubleshooting.md`
- `assets/example-config.yaml`