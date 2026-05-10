# Step Functions Troubleshooting

Common Step Functions error codes, recovery procedures.

## Error Code Reference

### StateMachineDoesNotExist
```
Error: State machine {{arn}} does not exist
```
**Resolution**: List state machines to verify ARN.

### ExecutionDoesNotExist
```
Error: Execution {{arn}} does not exist
```
**Resolution**: Check execution ARN format.

### InvalidDefinition
```
Error: Invalid ASL definition
```
**Common Issues:**
- Missing required fields
- Invalid JSON
- Syntax errors

**Resolution**:
```bash
# Validate definition format
# Use Step Functions console for validation
```

### ExecutionAlreadyExists
```
Error: Execution {{name}} already exists
```
**Cause**: Name must be unique.
**Resolution**: Use unique execution name with timestamp.

### ExecutionLimitExceeded
```
Error: Exceeded execution limit
```
**Cause**: Too many concurrent executions.
**Resolution**: Wait for executions to finish or request limit increase.

## Common Issues

### State Machine Failing
**Causes:**
- Lambda function error
- Missing IAM permissions
- Invalid input

**Resolution:**
```bash
# Check execution history
aws stepfunctions get-execution-history \
  --execution-arn {{execution_arn}}
```

### Lambda Timeout
**Causes:**
- Lambda timeout exceeded
- Missing heartbeat

**Resolution:**
```json
{
  "Task": {
    "Type": "Task",
    "Resource": "arn:aws:lambda:...",
    "TimeoutSeconds": 30,
    "HeartbeatSeconds": 10,
    "Retry": [{
      "ErrorEquals": ["States.Timeout"],
      "IntervalSeconds": 1,
      "MaxAttempts": 3,
      "BackoffRate": 2
    }]
  }
}
```

### Input/Output Mismatch
**Causes:**
- Wrong path references
- Missing parameters
- Invalid JSON

**Resolution:**
```json
{
  "StartAt": "ProcessData",
  "States": {
    "ProcessData": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...",
      "InputPath": "$.input",
      "ResultPath": "$.result",
      "Next": "End"
    }
  }
}
```

### Permissions Error
**Cause:** Missing IAM permissions.
**Resolution:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": "arn:aws:lambda:..."
    }
  ]
}
```

## Recovery Procedures

### Execution Recovery
```
1. Check execution history
2. Identify failed step
3. Fix Lambda function
4. Restart with same input
```

### State Machine Recovery
```
1. Verify definition syntax
2. Check IAM permissions
3. Update state machine
4. Start test execution
```

### Input Validation
```
1. Check input format
2. Validate JSON structure
3. Test with minimal input
```