# Step Functions Core Concepts

AWS Step Functions architecture, components, and operational concepts.

## Service Overview

**AWS Step Functions** - Serverless orchestration for distributed applications.

**Key Benefits:**
- Visual workflows
- Error handling and retries
- Human approval
- Parallel execution
- Long-running workflows

## State Machine Types

### STANDARD
- **Max Duration**: 1 year
- **Max Executions**: 10,000/minute
- **Use case**: Long-running workflows, complex logic

### EXPRESS
- **Max Duration**: 5 minutes
- **Max Executions**: 100,000/minute
- **Use case**: High-throughput, short-running tasks

## State Types

### Task State
- **Lambda**: Invoke Lambda function
- **Glue**: Start Glue workflow
- **ECS**: Run ECS task
- **Step Functions**: Call another state machine

### Choice State
- **Conditionals**: if/else logic
- **Comparisons**: String, numeric, boolean

### Parallel State
- **Fan-out**: Execute branches in parallel
- **Wait for completion**: All branches must finish

### Map State
- **Dynamic**: Iterate over array
- **Dynamic concurrency**: Run iterations in parallel

### Wait State
- **Time**: Wait for fixed duration
- **Timestamp**: Wait until time

### Pass State
- **Transform input/output**

### Fail State
- **Terminate with error**

### Succeed State
- **Terminate successfully**

## Data Flow

### Input/Output
- **Input**: State machine execution input
- **State Input**: Each state receives input
- **Output**: State produces output
- **State Output**: Result passed to next state

### Path/Parameters
- **InputPath**: Filter input
- **Parameters**: Add/transform data
- **ResultPath**: Merge result
- **OutputPath**: Filter output

## Error Handling

### Retry
- **Error Names**: Custom/error types
- **BackoffRate**: Exponential backoff
- **MaxAttempts**: Max retries
- **IntervalSeconds**: Initial interval

### Catch
- **Error Equals**: Match errors
- **Next**: Transition state
- **ResultPath**: Store error

### Timeouts
- **TimeoutSeconds**: Max execution time
- **HeartbeatSeconds**: Lambda timeout
- **TimeoutSeconds**: Task timeout

## Execution Modes

### Start Execution
- **Synchronous**: Wait for completion
- **Asynchronous**: Return immediately

### ContinueAsNew
- **Start new execution**: Replace current execution
- **Use case**: Long-running loops

## Pricing

### STANDARD
- **State transitions**: $0.025 per 1,000
- **Execution**: $0.000025 per state transition

### EXPRESS
- **Execution start**: $0.00002
- **Memory duration**: $0.0000256 per GB-second

## Best Practices

### Design
- Use Task states for Lambda functions
- Use Choice states for conditionals
- Use Map for parallel processing
- Use Retry for error handling
- Use Catch for error recovery

### Performance
- Use EXPRESS for high-throughput
- Use Parallel/Fan-out for parallelism
- Use HeartbeatSeconds for Lambda
- Optimize state machine size

### Security
- Minimum IAM permissions
- Use environment variables
- Monitor with CloudWatch
- Enable X-Ray tracing