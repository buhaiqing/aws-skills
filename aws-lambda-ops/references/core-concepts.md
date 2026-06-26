# Core Concepts - AWS Lambda

Lambda service architecture, execution model, and operational concepts.

## What is AWS Lambda

Serverless compute service. No server management, automatic scaling (0 to thousands), pay-per-execution, sub-second billing, built-in HA.

## Execution Environment

Uses Firecracker microVMs. Cold start (new microVM): 100ms-1s+. Warm start (reuse): 1-10ms. Provisioned concurrency pre-initializes environments.

**Cold start factors**: Runtime (Java > Node.js > Python > Go), package size, VPC (+10-100ms), layers count, init code complexity.

**Lifecycle**: Initialize (download + start runtime + init code) → Invoke (execute handler) → Post-invoke (keep alive ~5-15 min) → Shutdown.

## Key Components

- **Function**: Code + configuration (runtime, handler, memory, timeout)
- **Layer**: Shared library/package (max 5 layers, 250MB unzipped total)
- **Version**: Immutable code snapshot; versions are publishable and referenceable
- **Alias**: Pointer to version, supports weighted routing (canary deployments)
- **Event Source Mapping**: Poll-based triggers (SQS, DynamoDB Streams, Kinesis)
- **Concurrency**: Reserved (guaranteed), Provisioned (pre-warmed), per-function limit

## Runtimes & Limits
```bash
# List supported runtimes
aws lambda list-functions --max-items 1 --query 'Functions[0].Runtime'
```

| Limit | Value |
|-------|-------|
| Memory | 128-10,240 MB |
| Timeout | 1-900 seconds |
| Package size (zipped) | 50 MB (direct), 250 MB (S3) |
| Deployment package (unzipped) | 250 MB incl. layers |
| /tmp storage | 512 MB - 10,240 MB |
| Concurrent executions | 1,000/region (soft) |

## Invocation Types

| Type | Use Case | Return |
|------|----------|--------|
| RequestResponse (sync) | API, manual call | StatusCode 200 |
| Event (async) | Background, fire-and-forget | StatusCode 202 |
| DryRun | Validate config | StatusCode 204 |

Async invocations retry twice for throttling/system errors, then DLQ.

## Event Sources

| Source | Trigger Type |
|--------|-------------|
| API Gateway | Synchronous HTTP |
| SQS | Poll-based event source mapping |
| SNS | Asynchronous push |
| S3 / S3 Event Notifications | Asynchronous push |
| DynamoDB Streams | Poll-based event source mapping |
| Kinesis | Poll-based event source mapping |
| EventBridge | Asynchronous scheduled/event rule |
| Step Functions | Synchronous task |

## Security

- **Execution role**: IAM role Lambda assumes at runtime
- **Resource policy**: Cross-account invoke permissions
- **VPC**: Functions can access VPC resources, adds latency
- **Secrets**: Use environment variables (encrypted at rest) or Secrets Manager — never hardcode

## Error Handling & Retries

| Error Type | Behavior |
|-----------|----------|
| 400 (InvalidParameter) | Immediate failure |
| 429 (Throttling) | SDK auto-retry (3 attempts, backoff) |
| 5xx (Service) | SDK auto-retry (3 attempts) |
| Async invocation failure | 2 auto-retries, then DLQ or SQS dead-letter |

## Monitoring

| Metric | Description | Alarm Threshold |
|--------|-------------|-----------------|
| Invocations | Function call count | N/A |
| Errors | Invocation failures | >0 for 1 min |
| Throttles | Rate-limited invocations | >0 for 5 min |
| Duration | Execution time (ms) | >80% of timeout |
| ConcurrentExecutions | Current concurrency | >80% of limit |

## Best Practices

- **Package**: Minimize deployment size; use layers for common deps
- **Initialization**: Cache DB connections, HTTP clients outside handler
- **Timeout**: Set just above expected max execution time
- **Memory**: Increase to improve CPU allocation (linearly correlated)
- **Monitoring**: Enable CloudWatch metrics + X-Ray tracing
- **Error handling**: Implement DLQ for async failures

## Pricing

- Per-request (first 1M free), per-GB-second, per-GB for provisioned concurrency
- No charge when idle
- Inter-region data transfer at standard rates