# Lambda Function Field Mapping

**AWS API**: `lambda list-functions` -> `aws_lambda_function`

## Mapping Rules

| HCL Attribute | API JSON Path | Type | Required | Notes |
|---------------|---------------|------|----------|-------|
| `function_name` | `FunctionName` | string | Y | Block name derived from this |
| `runtime` | `Runtime` | string | Y | e.g. `python3.12` |
| `handler` | `Handler` | string | Y | e.g. `index.handler` |
| `role` | `Role` | string | Y | IAM role ARN |
| `memory_size` | `MemorySize` | int | N | Default 128 |
| `timeout` | `Timeout` | int | N | Default 3 |
| `vpc_config.subnet_ids` | `VpcConfig.SubnetIds` | list | N | VPC-attached only |
| `vpc_config.security_group_ids` | `VpcConfig.SecurityGroupIds` | list | N | VPC-attached only |

## Block Name

`{function_name_slug}` (e.g. `api_handler`)

## Stable Import ID

`{function_name}` (e.g. `api-handler`)

## Notes

- Function code (`S3Bucket`/`S3Key`) is NOT exported — requires separate deployment
- Environment variables masked (sensitive values)
- Layers deferred to Phase 2
