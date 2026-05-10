# Core Concepts - AWS Lambda

Lambda service architecture, execution model, and operational concepts.

## What is AWS Lambda

**Definition**: Serverless compute service that runs code in response to events and automatically manages compute resources.

**Key Characteristics**:
- No server management required
- Automatic scaling (0 to thousands of concurrent executions)
- Pay-per-execution pricing (no charge when idle)
- Sub-second billing granularity
- Built-in high availability and fault tolerance

## Execution Environments

### MicroVM Architecture

Lambda uses Firecracker microVMs:
- Lightweight virtualization
- Fast startup (<125ms typical)
- Isolated execution per function
- Shared nothing architecture

### Cold vs Warm Starts

| State | Description | Latency | Duration |
|-------|-------------|---------|----------|
| Cold Start | New microVM initialization | 100ms-1s+ | First invocation after idle |
| Warm Start | Reuse existing environment | 1-10ms | Subsequent invocations |
| Provisioned | Pre-initialized environments | ~1ms | Paid concurrency |

**Cold Start Factors**:
- Runtime (Java > Node.js > Python > Go)
- Deployment package size (larger = slower)
- VPC attachment (+10-100ms)
- Layers count (+startup time per layer)
- Initialization code complexity

### Execution Lifecycle

1. **Initialization**: Download code, start runtime, run initialization code
2. **Invoke**: Execute handler function
3. **Post-invoke**: Handler returns, environment kept alive
4. **Shutdown**: After idle period (~5-15 min), environment destroyed

**Environment reuse** enables:
- Connection pooling
- Cache reuse across invocations
- Initialization optimization

## Runtimes

### Supported Runtimes

| Language | Runtime | Version | Notes |
|----------|---------|---------|-------|
| Python | python3.9 | 3.9.x | Stable |
| Python | python3.10 | 3.10.x | Active |
| Python | python3.11 | 3.11.x | Recommended |
| Python | python3.12 | 3.12.x | Latest |
| Node.js | nodejs18.x | 18.x | LTS |
| Node.js | nodejs20.x | 20.x | Recommended |
| Java | java11 | 11.x | LTS |
| Java | java17 | 17.x | LTS |
| Java | java21 | 21.x | Latest LTS |
| Go | go1.x | Custom | Native binary |
| .NET | dotnet6 | 6.x | LTS |
| .NET | dotnet8 | 8.x | Latest |
| Ruby | ruby3.2 | 3.2.x | Active |
| Custom | provided.al2 | Amazon Linux 2 | BYO runtime |
| Custom | provided.al2023 | Amazon Linux 2023 | Latest custom |

### Runtime Handler Patterns

**Python**:
```python
# Handler signature: def handler(event, context)
def lambda_handler(event, context):
    # event: Dict containing invocation payload
    # context: LambdaContext object
    
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'success'})
    }
```

**Node.js**:
```javascript
// Handler signature: exports.handler = async (event) => {}
exports.handler = async (event) => {
    // event: Object containing invocation payload
    
    return {
        statusCode: 200,
        body: JSON.stringify({message: 'success'})
    };
};
```

**Java**:
```java
// Handler interface: RequestHandler<I, O>
public class Handler implements RequestHandler<Map<String,Object>, String> {
    @Override
    public String handleRequest(Map<String,Object> event, Context context) {
        return "Success";
    }
}
```

**Go**:
```go
// Handler signature: func handler(ctx context.Context, event json.RawMessage) (interface{}, error)
func handler(ctx context.Context, event json.RawMessage) (interface{}, error) {
    return map[string]string{"status": "success"}, nil
}
```

## Deployment Packages

### Package Types

| Type | Size Limit | Upload Method | Notes |
|------|------------|---------------|-------|
| S3 zip | 50MB (direct), 250MB (via S3) | S3 bucket | Standard deployment |
| Container image | 10GB | ECR repository | Docker-based |
| Inline edit | ~3KB | Console edit | Small functions only |

### Package Structure

**Python**:
```
function.zip
├── lambda_function.py (handler)
├── requirements.txt (dependencies)
├── package/ (installed packages)
└── utils/
    └── helper.py
```

**Node.js**:
```
function.zip
├── index.js (handler)
├── package.json
├── package-lock.json
├── node_modules/ (dependencies)
└── lib/
    └── utils.js
```

## Lambda Layers

**Purpose**: Share code and dependencies across functions.

**Structure**:
- Maximum 5 layers per function
- Each layer: 50MB (zip), 250MB (unzipped)
- Layer content merged into `/opt` directory

**Layer Directory Layout**:
```
/opt/
├── python/        # Python packages
│   └── lib/
│       └── python3.x/
│           └── site-packages/
├── nodejs/        # Node.js modules
│   ├── node_modules/
│   └── package.json
├── java/          # Java libraries
│   └── lib/
├── bin/           # Executable binaries
└── lib/           # Shared libraries
```

**Use Cases**:
- Common dependencies (reduce package size)
- Custom runtime extensions
- Shared utility libraries
- Configuration files
- SDK updates without code changes

## Versions and Aliases

### Versioning

- **$LATEST**: Mutable, reflects current code/configuration
- **Version N**: Immutable snapshot (1, 2, 3, ...)
- Each version has unique ARN: `arn:aws:lambda:region:account:function:name:N`

**Version Behavior**:
- Publishing creates immutable copy
- Code and configuration frozen
- Cannot modify published version
- Must publish new version for changes

### Aliases

**Purpose**: Named pointer to specific version or routing config.

**ARN Format**: `arn:aws:lambda:region:account:function:name:alias-name`

**Routing Configuration** (Canary deployments):
```yaml
Alias: prod
Primary Version: 10 (90% traffic)
Secondary Version: 11 (10% traffic)
```

**Alias Patterns**:
- `dev` → $LATEST
- `staging` → version N
- `prod` → version M (with routing for canary)

## Event Sources

### Invocation Types

| Type | Use Case | Response | Retry Behavior |
|------|----------|----------|----------------|
| RequestResponse | Sync invocation | Returns result | No automatic retry |
| Event | Async invocation | Status 202 | Retry 2x on failure |
| DryRun | Validate only | No execution | N/A |

### Event Source Types

**API Gateway** (Sync):
- REST API (proxy integration)
- HTTP API (payload format v1/v2)
- WebSocket API ($connect, $disconnect, $default)

**SQS** (Poll-based):
- Batch size: 1-10 messages
- Batch window: 0-300 seconds
- Visibility timeout: function timeout × 6
- ReportBatchItemFailures for partial failure

**SNS** (Push):
- Single message per invocation
- No batching
- Dead letter queue on failure

**DynamoDB Streams** (Poll-based):
- Batch size: 1-100 records
- Starting position: LATEST | TRIM_HORIZON
- Parallelization factor: 1-10
- On-failure: bisect on error

**Kinesis Streams** (Poll-based):
- Batch size: 1-100 records
- Starting position: LATEST | TRIM_HORIZON | AT_TIMESTAMP
- Parallelization factor: 1-10
- On-failure: bisect on error

**EventBridge** (Push):
- Rule-based trigger
- Schedule expressions (cron/rate)
- Pattern matching

**S3** (Async):
- ObjectCreated, ObjectRemoved events
- Object level events (PUT, POST, COPY)
- Batch operations support

**CloudWatch Logs** (Subscription):
- Log stream filtering
- Real-time log processing
- Subscription filter patterns

**MSK (Kafka)** (Poll-based):
- Self-managed Apache Kafka
- Amazon MSK clusters
- Topics configuration
- SASL/SCRAM authentication

## Function Configuration

### Memory and Timeout

| Parameter | Range | Default | Impact |
|-----------|-------|---------|--------|
| MemorySize | 128-10240 MB | 128 MB | CPU scales with memory |
| Timeout | 1-900 sec | 3 sec | Max execution duration |

**Memory-CPU Relationship**:
- 128MB = 1 vCPU credit
- 1769MB = 1 full vCPU
- Higher memory = more CPU power
- Network bandwidth scales with memory

### Environment Variables

- Key-value pairs (string values)
- Maximum 4KB total
- Encrypted at rest (AWS managed KMS)
- Can use custom KMS key
- Accessible via runtime API

**Best Practices**:
- Secrets: Use Secrets Manager/Parameter Store
- Configuration: Environment variables
- Sensitive data: Never log or return

### VPC Configuration

**Enables**:
- Access to private resources (RDS, EC2)
- Private subnet connectivity
- Security group rules

**Requirements**:
- VPC ID
- Subnet IDs (minimum 2 for HA)
- Security Group IDs
- ENI management (AWS managed)

**Impact**:
- Cold start penalty (+10-100ms)
- ENI creation latency
- Must have sufficient ENI quota

### Execution Role

**Required Permissions**:
- Basic execution: `AWSLambdaBasicExecutionRole`
- VPC access: `AWSLambdaVPCAccessExecutionRole`
- S3 access: Custom policy for bucket
- DynamoDB: Custom policy for table

**Role Structure**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

## Concurrency

### Types

| Type | Description | Billing |
|------|-------------|---------|
| Reserved | Guaranteed capacity for function | No extra cost |
| Provisioned | Pre-initialized environments | $0.0004/GB-second + $0.015/hour |
| Unreserved | Shared pool (account limit) | Pay-per-use |

### Concurrency Limits

- **Account limit**: 1000 concurrent executions (soft), 10000 (hard)
- **Reserved**: Function-specific guarantee
- **Provisioned**: Eliminates cold start latency

### Scaling Behavior

**Invocation rate increase**:
1. Invoke arrives
2. If warm: execute immediately
3. If cold: initialize new environment
4. Scale until concurrency limit
5. Throttle if limit exceeded (429 error)

**Throttle handling**:
- Async: Retry 2x, then DLQ
- Sync: Return 429, client must retry
- Poll-based: Skip batch, retry later

## Quotas and Limits

### Function Quotas

| Resource | Limit | Notes |
|----------|-------|-------|
| Deployment package (zip) | 50MB direct upload | 250MB via S3 |
| Unzipped deployment size | 250MB | Includes layers |
| Total code storage | 75GB | All functions + layers |
| Concurrent executions | 1000 (soft) | Account-wide |
| Function timeout | 900 sec | Maximum |
| Function memory | 10240 MB | Maximum |
| Environment variables | 4KB | Total size |
| Layers per function | 5 | Maximum |
| Layer size | 50MB zip | 250MB unzipped |
| Event source mappings | Per function | No documented limit |

### Invocation Quotas

| Quota | Limit | Notes |
|-------|-------|-------|
| Invoke payload | 6MB (sync) | 256KB (async) |
| Invocation rate | Unlimited | Within concurrency |
| Log event size | 256KB per event | CloudWatch |

### Throttle Response

```json
{
  "statusCode": 429,
  "error": "ThrottlingException",
  "message": "Rate Exceeded"
}
```

## Pricing Model

### Compute Pricing

**Request pricing**: $0.20 per 1M requests
**Duration pricing**: $0.00001667 per GB-second

**Example calculation**:
```
Memory: 512MB (0.5GB)
Duration: 100ms (0.1 seconds)
Requests: 1M

Cost = 1M × $0.20 + 1M × 0.5GB × 0.1sec × $0.00001667
     = $0.20 + $0.0008335
     = $0.2008335
```

### Provisioned Concurrency Pricing

- **Duration**: $0.0004 per GB-second (provisioned)
- **Management**: $0.015 per hour per concurrency unit

### Free Tier

- 1M requests per month
- 400,000 GB-seconds per month
- Always free tier (does not expire)

## Security

### Encryption

- **At rest**: AWS managed KMS (default)
- **Custom KMS**: Customer managed key
- **Environment variables**: Encrypted
- **Code**: Encrypted in S3/Lambda storage

### Network Security

- **Public endpoints**: Default (no VPC)
- **Private access**: VPC configuration
- **Security groups**: Control outbound access
- **NAT Gateway**: Required for VPC public access

### IAM Integration

- **Execution role**: Function identity
- **Resource policy**: Cross-account invoke
- **Principal-based**: API Gateway, EventBridge

## Monitoring

### CloudWatch Metrics

| Metric | Unit | Meaning |
|--------|------|---------|
| Invocations | Count | Total invocations |
| Duration | Milliseconds | Execution time |
| Errors | Count | Function errors |
| Throttles | Count | 429 responses |
| ConcurrentExecutions | Count | Active executions |
| UnreservedConcurrentExecutions | Count | Unreserved pool usage |

### CloudWatch Logs

- **Log group**: `/aws/lambda/{function-name}`
- **Log stream**: Per execution environment
- **Retention**: Configurable (1 day - never expire)
- **Structured logging**: JSON format recommended

### X-Ray Integration

- **Trace sampling**: 1 request per second + 5% additional
- **Service map**: Visualize downstream calls
- **Segments**: Per-service timing
- **Annotations**: Custom metadata

### Lambda Insights

- Enhanced monitoring extension
- CPU, memory, network metrics
- Function-level insights
- No code changes required