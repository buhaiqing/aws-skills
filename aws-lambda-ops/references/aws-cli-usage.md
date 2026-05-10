# AWS CLI Usage - Lambda Operations

Verified CLI commands for AWS Lambda operations with JSON output paths.

## CLI Setup

```bash
# Verify Lambda CLI availability
aws lambda help

# Set output format (always use JSON for automation)
aws configure set output json

# Default region handling
aws lambda list-functions --region {{env.AWS_DEFAULT_REGION}}
```

## Function Operations

### Create Function

```bash
aws lambda create-function \
  --function-name {{user.function_name}} \
  --runtime python3.11 \
  --role {{user.execution_role_arn}} \
  --handler index.handler \
  --code S3Bucket=my-bucket,S3Key=function.zip \
  --description "Lambda function description" \
  --timeout 30 \
  --memory-size 256 \
  --publish \
  --environment Variables={KEY1=value1,KEY2=value2} \
  --tags Project=my-project,Environment=prod \
  --output json
```

**JSON Paths**:
- Function ARN: `.FunctionArn`
- State: `.State` (Pending | Active | Inactive | Failed)
- Version: `.Version`
- Last Modified: `.LastModified`

### Update Function Code

```bash
# From S3
aws lambda update-function-code \
  --function-name {{user.function_name}} \
  --s3-bucket {{user.s3_bucket}} \
  --s3-key {{user.s3_key}} \
  --publish \
  --output json

# From local zip file
aws lambda update-function-code \
  --function-name {{user.function_name}} \
  --zip-file fileb://function.zip \
  --publish \
  --output json

# From inline (for small functions, Node.js only)
aws lambda update-function-code \
  --function-name {{user.function_name}} \
  --zip-file fileb://function.zip \
  --output json
```

**JSON Paths**:
- State: `.State` (Pending | InProgress | Successful | Failed)
- Version: `.Version`
- Last Modified: `.LastModified`

### Update Function Configuration

```bash
aws lambda update-function-configuration \
  --function-name {{user.function_name}} \
  --runtime python3.11 \
  --handler index.new_handler \
  --timeout 60 \
  --memory-size 512 \
  --description "Updated description" \
  --environment Variables={NEW_KEY=new_value} \
  --role {{user.new_role_arn}} \
  --output json
```

**JSON Paths**:
- FunctionArn: `.FunctionArn`
- Runtime: `.Runtime`
- Handler: `.Handler`
- Timeout: `.Timeout`
- MemorySize: `.MemorySize`

### Get Function Details

```bash
aws lambda get-function \
  --function-name {{user.function_name}} \
  --output json
```

**JSON Paths**:
- Configuration: `.Configuration`
- Code location: `.Code.Location`
- Tags: `.Tags`
- Concurrency: `.Concurrency`

### List Functions

```bash
# List all functions
aws lambda list-functions \
  --output json

# Filter by runtime
aws lambda list-functions \
  --runtime python3.11 \
  --output json

# Pagination
aws lambda list-functions \
  --max-items 50 \
  --starting-token {{next_token}} \
  --output json
```

**JSON Paths**:
- Functions list: `.Functions[]`
- Function name: `.Functions[].FunctionName`
- Function ARN: `.Functions[].FunctionArn`
- Runtime: `.Functions[].Runtime`
- Next token: `.NextToken`

### Delete Function

```bash
# ⚠️ DESTRUCTIVE - requires human confirmation
aws lambda delete-function \
  --function-name {{user.function_name}} \
  --output json
```

Returns empty response on success (204 No Content).

### Invoke Function

```bash
# Synchronous invocation (RequestResponse)
aws lambda invoke \
  --function-name {{user.function_name}} \
  --invocation-type RequestResponse \
  --payload '{"key": "value"}' \
  --cli-binary-format raw-in-base64-out \
  response.json \
  --output json

# Asynchronous invocation (Event)
aws lambda invoke \
  --function-name {{user.function_name}} \
  --invocation-type Event \
  --payload '{"key": "value"}' \
  --cli-binary-format raw-in-base64-out \
  response.json \
  --output json

# Dry run (validate payload only)
aws lambda invoke \
  --function-name {{user.function_name}} \
  --invocation-type DryRun \
  --payload '{"key": "value"}' \
  --cli-binary-format raw-in-base64-out \
  response.json \
  --output json
```

**JSON Paths** (in response file metadata):
- StatusCode: `.StatusCode` (200 = success, 202 = async accepted)
- ExecutedVersion: `.ExecutedVersion`
- LogResult (base64): `.LogResult`

## Version and Alias Operations

### Publish Version

```bash
aws lambda publish-version \
  --function-name {{user.function_name}} \
  --description "Version description" \
  --output json
```

**JSON Paths**:
- Version: `.Version`
- FunctionArn: `.FunctionArn`
- Description: `.Description`

### List Versions

```bash
aws lambda list-versions-by-function \
  --function-name {{user.function_name}} \
  --output json
```

**JSON Paths**:
- Versions: `.Versions[]`
- Version number: `.Versions[].Version`

### Create Alias

```bash
aws lambda create-alias \
  --function-name {{user.function_name}} \
  --name {{user.alias_name}} \
  --function-version {{user.version}} \
  --description "Alias description" \
  --output json

# Create alias with routing configuration (weighted aliases)
aws lambda create-alias \
  --function-name {{user.function_name}} \
  --name {{user.alias_name}} \
  --function-version {{user.version}} \
  --routing-config AdditionalVersionWeights={2=0.5} \
  --output json
```

**JSON Paths**:
- AliasArn: `.AliasArn`
- FunctionVersion: `.FunctionVersion`
- RoutingConfig: `.RoutingConfig`

### Update Alias

```bash
aws lambda update-alias \
  --function-name {{user.function_name}} \
  --name {{user.alias_name}} \
  --function-version {{user.new_version}} \
  --description "Updated alias description" \
  --output json
```

### List Aliases

```bash
aws lambda list-aliases \
  --function-name {{user.function_name}} \
  --output json
```

**JSON Paths**:
- Aliases: `.Aliases[]`
- AliasArn: `.Aliases[].AliasArn`

## Layer Operations

### Publish Layer Version

```bash
aws lambda publish-layer-version \
  --layer-name {{user.layer_name}} \
  --description "Layer description" \
  --content S3Bucket={{user.s3_bucket}},S3Key={{user.layer_key}} \
  --compatible-runtimes python3.11 python3.10 \
  --compatible-architectures x86_64 arm64 \
  --license-info "MIT" \
  --output json

# From local zip
aws lambda publish-layer-version \
  --layer-name {{user.layer_name}} \
  --content ZipFile=fileb://layer.zip \
  --compatible-runtimes python3.11 \
  --output json
```

**JSON Paths**:
- LayerArn: `.LayerArn`
- LayerVersionArn: `.LayerVersionArn`
- Version: `.Version`
- CompatibleRuntimes: `.CompatibleRuntimes`

### List Layers

```bash
aws lambda list-layers \
  --output json
```

**JSON Paths**:
- Layers: `.Layers[]`
- LayerName: `.Layers[].LayerName`
- LatestMatchingVersion: `.Layers[].LatestMatchingVersion`

### List Layer Versions

```bash
aws lambda list-layer-versions \
  --layer-name {{user.layer_name}} \
  --output json
```

### Get Layer Version

```bash
aws lambda get-layer-version \
  --layer-name {{user.layer_name}} \
  --version-number {{user.version}} \
  --output json
```

**JSON Paths**:
- Content location: `.Content.Location`
- CompatibleRuntimes: `.CompatibleRuntimes`

### Delete Layer Version

```bash
# ⚠️ DESTRUCTIVE - requires human confirmation
aws lambda delete-layer-version \
  --layer-name {{user.layer_name}} \
  --version-number {{user.version}} \
  --output json
```

### Attach Layer to Function

```bash
# Update function configuration with layers
aws lambda update-function-configuration \
  --function-name {{user.function_name}} \
  --layers arn:aws:lambda:region:account:layer:layer-name:1 \
  --output json

# Multiple layers
aws lambda update-function-configuration \
  --function-name {{user.function_name}} \
  --layers arn:aws:lambda:region:account:layer:layer1:1 \
            arn:aws:lambda:region:account:layer:layer2:2 \
  --output json
```

## Event Source Mapping Operations

### Create Event Source Mapping

```bash
# SQS event source
aws lambda create-event-source-mapping \
  --function-name {{user.function_name}} \
  --event-source-arn arn:aws:sqs:region:account:queue-name \
  --batch-size 10 \
  --maximum-batching-window-in-seconds 5 \
  --function-response-types ReportBatchItemFailures \
  --output json

# DynamoDB stream
aws lambda create-event-source-mapping \
  --function-name {{user.function_name}} \
  --event-source-arn arn:aws:dynamodb:region:account:table/name/stream/label \
  --batch-size 100 \
  --starting-position LATEST \
  --maximum-batching-window-in-seconds 0 \
  --output json

# Kinesis stream
aws lambda create-event-source-mapping \
  --function-name {{user.function_name}} \
  --event-source-arn arn:aws:kinesis:region:account:stream/stream-name \
  --batch-size 100 \
  --starting-position TRIM_HORIZON \
  --parallelization-factor 2 \
  --output json

# SNS (requires subscription, not direct mapping)
# Use aws sns subscribe with Lambda protocol

# MSK (Kafka)
aws lambda create-event-source-mapping \
  --function-name {{user.function_name}} \
  --event-source-arn arn:aws:kafka:region:account:cluster/cluster-name \
  --topics topic1 topic2 \
  --source-access-configuration Type=VPC_SECURITY_GROUP,URI=sg-12345 \
  --output json
```

**JSON Paths**:
- UUID: `.UUID`
- State: `.State` (Creating | Enabling | Enabled | Disabling | Disabled | Deleting)
- LastProcessingResult: `.LastProcessingResult`
- BatchSize: `.BatchSize`

### List Event Source Mappings

```bash
aws lambda list-event-source-mappings \
  --function-name {{user.function_name}} \
  --output json
```

### Get Event Source Mapping

```bash
aws lambda get-event-source-mapping \
  --uuid {{user.mapping_uuid}} \
  --output json
```

### Update Event Source Mapping

```bash
aws lambda update-event-source-mapping \
  --uuid {{user.mapping_uuid}} \
  --batch-size 50 \
  --maximum-batching-window-in-seconds 10 \
  --output json
```

### Delete Event Source Mapping

```bash
# ⚠️ DESTRUCTIVE - requires human confirmation
aws lambda delete-event-source-mapping \
  --uuid {{user.mapping_uuid}} \
  --output json
```

## Runtime Options

| Runtime | Version | Deprecation |
|---------|---------|-------------|
| python3.9 | 3.9.x | Active |
| python3.10 | 3.10.x | Active |
| python3.11 | 3.11.x | Active (recommended) |
| python3.12 | 3.12.x | Active |
| nodejs18.x | 18.x | Active |
| nodejs20.x | 20.x | Active (recommended) |
| java11 | 11.x | Active |
| java17 | 17.x | Active |
| java21 | 21.x | Active |
| go1.x | Custom | Active |
| dotnet6 | 6.x | Active |
| dotnet8 | 8.x | Active |
| ruby3.2 | 3.2.x | Active |
| provided.al2 | Custom | Active (AL2) |
| provided.al2023 | Custom | Active (AL2023) |

## Common Options Reference

### Timeout Range

`--timeout`: 1 to 900 seconds (15 minutes max)

### Memory Size Range

`--memory-size`: 128 to 10240 MB (10GB max)

### Concurrency Configuration

```bash
# Reserved concurrency
aws lambda put-function-concurrency \
  --function-name {{user.function_name}} \
  --reserved-concurrent-executions 100 \
  --output json

# Provisioned concurrency
aws lambda put-provisioned-concurrency-config \
  --function-name {{user.function_name}} \
  --qualifier {{user.alias_or_version}} \
  --provisioned-concurrent-executions 50 \
  --output json
```

## VPC Configuration

```bash
aws lambda update-function-configuration \
  --function-name {{user.function_name}} \
  --vpc-config SubnetIds=subnet-1,subnet-2,SecurityGroupIds=sg-1 \
  --output json
```

## Error Output Example

```json
{
  "Error": {
    "Code": "ResourceNotFoundException",
    "Message": "Function not found: arn:aws:lambda:region:account:function:my-function"
  },
  "ResponseMetadata": {
    "RequestId": "request-id",
    "HTTPStatusCode": 404
  }
}
```