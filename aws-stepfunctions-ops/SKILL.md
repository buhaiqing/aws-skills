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

## Common JSON Paths (Centralized)

```
# Create SM:       .stateMachineArn
# Describe SM:     .{stateMachineArn,name,status,definition}
# List SMs:        .stateMachines[].{stateMachineArn,name,creationDate}
# Start Exec:      .executionArn
# Describe Exec:   .{executionArn,status,output,startDate}
# Stop Exec:       Empty (success)
# Get History:     .events[].{id,type,timestamp}
```

## Trigger & Scope

### SHOULD Use When
- User requests state machine creation or deletion
- User needs to start/stop executions
- User asks about Step Functions
- User mentions "state machine", "workflow", "execution"
- User needs to describe execution history
- User asks about error handling or retries

### SHOULD NOT Use When
- Lambda operations only → delegate to: `aws-lambda-ops`
- EventBridge rules → delegate to: `aws-eventbridge-ops`
- Simple queue operations → delegate to: `aws-sqs-ops`

### Delegation
- Lambda → `aws-lambda-ops` (Lambda functions)
- IAM → `aws-iam-ops` (Execution role)
- CloudWatch → `aws-cloudwatch-ops` (Metrics)

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use `us-east-1` if unset |
| `{{user.StateMachineName}}` | User input | Ask once; reuse |
| `{{user.StateMachineArn}}` | User input | Ask once; reuse |
| `{{user.ExecutionArn}}` | User input | Ask once; reuse |
| `{{user.RoleArn}}` | User input | Ask once; reuse |
| `{{user.Definition}}` | User input | ASL definition (JSON) |
| `{{output.ExecArn}}` | Last API response | Parse `.executionArn` |

## Execution Flow

**Pre-flight**: `aws --version` + `aws sts get-caller-identity`. Verify IAM role and check state machine definition syntax.

**CLI (primary)**: `aws stepfunctions [command] --output json` — see [references/aws-cli-usage.md](references/aws-cli-usage.md).

**boto3 (fallback)**: After 3 CLI failures, switch to SDK — see [references/boto3-sdk-usage.md](references/boto3-sdk-usage.md).

**Validate**: Use `describe-state-machine` or `describe-execution` to confirm.

**Common Recovery**:
| Error | Action |
|-------|--------|
| InvalidDefinition (400) | Fix ASL syntax; retry once |
| StateMachineDoesNotExist | Verify SM ARN |
| ExecutionDoesNotExist | Verify execution ARN |
| Throttling (429) | Backoff, retry 3x |
| InternalError (5xx) | Retry 3x; HALT |

## Safety Gates

### Delete State Machine
```
⚠️ Deleting state machine will remove all executions and history.
Before proceeding:
1. Check for running executions via `list-executions`
2. Stop active executions via `stop-execution`
3. Confirm: Type DELETE {{user.StateMachineName}} to proceed.
```

## Related Skills

- `aws-lambda-ops` - Lambda functions
- `aws-iam-ops` - IAM roles
- `aws-cloudwatch-ops` - Metrics

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](../aws-skill-generator/references/integration.md)