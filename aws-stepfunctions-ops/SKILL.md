---
name: aws-stepfunctions-ops
description: >-
  Use this skill when managing AWS Step Functions resources, creating/deleting
  state machines, starting/stopping executions, describing execution history,
  or configuring error handling; even if the user doesn't explicitly mention
  "Step Functions" or "state machine" but needs workflow orchestration.
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials with Step
  Functions permissions.
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
---

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

```
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
