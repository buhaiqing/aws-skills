# AWS CLI Usage - Step Functions

AWS CLI commands for Step Functions operations.

## State Machine Operations

### Create State Machine
```bash
aws stepfunctions create-state-machine \
  --name "{{user.StateMachineName}}" \
  --definition '{{user.Definition}}' \
  --role-arn "{{user.RoleArn}}" \
  --type STANDARD \
  --logging-configuration '{"level":"ALL","destinations":[{"arn":"{{user.LogGroupArn}}"}]}' \
  --output json
```

### Describe State Machine
```bash
aws stepfunctions describe-state-machine \
  --state-machine-arn "{{user.StateMachineArn}}" \
  --output json
```

### List State Machines
```bash
aws stepfunctions list-state-machines \
  --max-results 10 \
  --output json
```

### Update State Machine
```bash
aws stepfunctions update-state-machine \
  --state-machine-arn "{{user.StateMachineArn}}" \
  --definition '{{user.NewDefinition}}' \
  --role-arn "{{user.RoleArn}}" \
  --output json
```

### Delete State Machine
```bash
aws stepfunctions delete-state-machine \
  --state-machine-arn "{{user.StateMachineArn}}" \
  --output json
```

## Execution Operations

### Start Execution
```bash
aws stepfunctions start-execution \
  --state-machine-arn "{{user.StateMachineArn}}" \
  --name "{{user.ExecutionName}}" \
  --input '{{user.Input}}' \
  --output json
```

### Stop Execution
```bash
aws stepfunctions stop-execution \
  --execution-arn "{{user.ExecutionArn}}" \
  --output json
```

### Describe Execution
```bash
aws stepfunctions describe-execution \
  --execution-arn "{{user.ExecutionArn}}" \
  --output json
```

### List Executions
```bash
# Latest 10 executions
aws stepfunctions list-executions \
  --state-machine-arn "{{user.StateMachineArn}}" \
  --max-results 10 \
  --output json

# Filter by status
aws stepfunctions list-executions \
  --state-machine-arn "{{user.StateMachineArn}}" \
  --status-filter RUNNING \
  --output json
```

## Execution History

### Get Execution History
```bash
aws stepfunctions get-execution-history \
  --execution-arn "{{user.ExecutionArn}}" \
  --max-results 100 \
  --output json
```

### List Activities
```bash
aws stepfunctions list-activities \
  --max-results 10 \
  --output json
```

## Common Options

```bash
--state-machine-arn "{{user.ARN}}"     # State machine ARN
--definition '{{user.Definition}}'     # ASL definition (JSON)
--role-arn "{{user.RoleArn}}"          # IAM role ARN
--input '{{user.Input}}'               # Execution input (JSON)
--name "{{user.Name}}"                 # Execution name
```