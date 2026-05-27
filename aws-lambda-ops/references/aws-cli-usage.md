# AWS CLI Usage - Lambda Operations

Verified CLI commands for AWS Lambda operations.

## Common JSON Paths (Centralized)

```
# Create Function:   .FunctionArn
# Update Code:       .{FunctionArn,State,Version}
# Update Config:     .{FunctionArn,Timeout,MemorySize,Runtime}
# Invoke:            .StatusCode  (200=sync, 202=async)
# List Functions:    .Functions[].{FunctionName,FunctionArn,Runtime}
# Create ESM:        .UUID
# Publish Layer:     .LayerVersionArn
# Get Function:      .Configuration.{FunctionArn,State,LastModified}
```

## Function Operations

### Create Function
```bash
aws lambda create-function \
  --function-name {{user.function_name}} --runtime python3.11 \
  --role {{user.execution_role_arn}} --handler index.handler \
  --code S3Bucket=my-bucket,S3Key=function.zip \
  --description "Lambda function" --timeout 30 --memory-size 256 \
  --publish --environment Variables={KEY1=value1,KEY2=value2} \
  --tags Project=my-project,Environment=prod
```

### Update Function Code
```bash
# From S3
aws lambda update-function-code --function-name {{user.function_name}} \
  --s3-bucket {{user.s3_bucket}} --s3-key {{user.s3_key}} --publish

# From local zip
aws lambda update-function-code --function-name {{user.function_name}} \
  --zip-file fileb://function.zip --publish
```

### Update Function Configuration
```bash
aws lambda update-function-configuration --function-name {{user.function_name}} \
  --runtime python3.11 --handler index.new_handler --timeout 60 --memory-size 512
```

### Get Function Details
```bash
aws lambda get-function --function-name {{user.function_name}}
```

### List Functions
```bash
aws lambda list-functions
aws lambda list-functions --max-items 50 --starting-token {{next_token}}
```

### Delete Function
```bash
# ⚠️ DESTRUCTIVE — requires human confirmation
aws lambda delete-function --function-name {{user.function_name}}
```

### Invoke Function
```bash
# Synchronous
aws lambda invoke --function-name {{user.function_name}} \
  --invocation-type RequestResponse --payload '{"key": "value"}' \
  --cli-binary-format raw-in-base64-out response.json

# Asynchronous
aws lambda invoke --function-name {{user.function_name}} \
  --invocation-type Event --payload '{"key": "value"}' \
  --cli-binary-format raw-in-base64-out response.json
```

## Version and Alias Operations

### Publish Version
```bash
aws lambda publish-version --function-name {{user.function_name}} --description "v1.0"
```

### Create Alias
```bash
aws lambda create-alias --function-name {{user.function_name}} \
  --name {{user.alias_name}} --function-version {{user.version}}
```

### Update Alias
```bash
aws lambda update-alias --function-name {{user.function_name}} \
  --name {{user.alias_name}} --function-version {{user.new_version}}
```

### List Aliases / Versions
```bash
aws lambda list-aliases --function-name {{user.function_name}}
aws lambda list-versions-by-function --function-name {{user.function_name}}
```

## Layer Operations

### Publish Layer Version
```bash
aws lambda publish-layer-version --layer-name {{user.layer_name}} \
  --description "Layer description" \
  --content S3Bucket={{user.s3_bucket}},S3Key={{user.layer_key}} \
  --compatible-runtimes python3.11 python3.10

# From local zip
aws lambda publish-layer-version --layer-name {{user.layer_name}} \
  --content ZipFile=fileb://layer.zip --compatible-runtimes python3.11
```

### List/Get/Delete Layer
```bash
aws lambda list-layers
aws lambda list-layer-versions --layer-name {{user.layer_name}}
aws lambda get-layer-version --layer-name {{user.layer_name}} --version-number {{user.version}}
aws lambda delete-layer-version --layer-name {{user.layer_name}} --version-number {{user.version}}
```

### Attach Layer to Function
```bash
aws lambda update-function-configuration --function-name {{user.function_name}} \
  --layers arn:aws:lambda:region:account:layer:layer-name:1
```

## Event Source Mapping Operations

### Create Event Source Mapping
```bash
# SQS
aws lambda create-event-source-mapping --function-name {{user.function_name}} \
  --event-source-arn arn:aws:sqs:region:account:queue-name \
  --batch-size 10 --maximum-batching-window-in-seconds 5

# DynamoDB Stream
aws lambda create-event-source-mapping --function-name {{user.function_name}} \
  --event-source-arn arn:aws:dynamodb:region:account:table/name/stream/label \
  --batch-size 100 --starting-position LATEST

# Kinesis
aws lambda create-event-source-mapping --function-name {{user.function_name}} \
  --event-source-arn arn:aws:kinesis:region:account:stream/stream-name \
  --batch-size 100 --starting-position TRIM_HORIZON
```

### List/Get/Update/Delete ESM
```bash
aws lambda list-event-source-mappings --function-name {{user.function_name}}
aws lambda get-event-source-mapping --uuid {{user.mapping_uuid}}
aws lambda update-event-source-mapping --uuid {{user.mapping_uuid}} --batch-size 50
aws lambda delete-event-source-mapping --uuid {{user.mapping_uuid}}
```

## Concurrency Configuration
```bash
aws lambda put-function-concurrency --function-name {{user.function_name}} \
  --reserved-concurrent-executions 100

aws lambda put-provisioned-concurrency-config \
  --function-name {{user.function_name}} --qualifier {{user.alias_or_version}} \
  --provisioned-concurrent-executions 50
```

## VPC Configuration
```bash
aws lambda update-function-configuration --function-name {{user.function_name}} \
  --vpc-config SubnetIds=subnet-1,subnet-2,SecurityGroupIds=sg-1
```