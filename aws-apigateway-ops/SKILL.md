---
name: aws-apigateway-ops
description: >-
  Use when operating AWS API Gateway resources via AWS CLI or boto3 SDK;
  user mentions API Gateway, REST API, HTTP API, API endpoint, or stage.
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to AWS endpoints.
metadata:
  author: aws
  version: "1.0.0"
  last_updated: "2026-07-06"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_SESSION_TOKEN
    - AWS_DEFAULT_REGION
    - AWS_PROFILE
  gcl:
    enabled: true
    class: required
    max_iter: 2
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: false
  cross_skill_deps:
    - aws-iam-ops
    - aws-lambda-ops
    - aws-kms-ops
    - aws-vpc-ops            # VPC links and networking
    - aws-cloudwatch-ops     # API Gateway metrics and alarms
    - aws-cloudfront-ops     # CloudFront + API GW edge integration
  orchestrator_aware: true
  orchestrator_compat: ">=0.1.0"
  delegate:
    accepts: ["health-check", "rca"]
    produces_facts: ["state", "metric", "event"]
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true
---

# AWS API Gateway Operations Skill

## Overview

AWS API Gateway is a fully managed service for creating, publishing, and securing REST and HTTP APIs. This skill covers **API creation, resource/method configuration, deployment to stages, and API lifecycle management** with Lambda proxy integration.

## Trigger & Scope

### SHOULD Use When
- User mentions "API Gateway", "REST API", "HTTP API", "endpoint", "stage"
- Task involves CRUD on **API Gateway resources** (REST API, resource, method, deployment, stage)
- Keywords: apigateway, rest-api, http-api, stage, deployment, usage-plan

### SHOULD NOT Use When
- Lambda function CRUD → delegate to: `aws-lambda-ops`
- Lambda integration setup → delegate to: `aws-lambda-ops` (function alias/arn)
- ELB/ALB as API entry → delegate to: `aws-elb-ops`
- CloudFront distribution → delegate to: `aws-cloudfront-ops`
- Route53 custom domain DNS → delegate to: `aws-route53-ops`

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default; allow override |
| `{{user.api_name}}` | User input | REST API name |
| `{{user.api_id}}` | User input or last output | API ID from `get-rest-apis` |
| `{{user.stage_name}}` | User input | Stage name (e.g., prod, dev) |
| `{{user.resource_path}}` | User input | Resource path (e.g., /users) |
| `{{user.lambda_arn}}` | User input | Lambda function ARN for proxy |
| `{{output.api_id}}` | Last API response | `.id` from created API |
| `{{output.deployment_id}}` | Last API response | `.id` from `create-deployment` |
| `{{output.resource_id}}` | Last API response | `.id` from `create-resource` |
| `{{output.root_resource_id}}` | Last API response | `.items[?path=='/'].id` |

## Execution Flow Pattern

**Pre-flight → Execute → Validate → Recover**

### Operation: Create REST API

#### Pre-flight

| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `aws --version` | Install AWS CLI v2 |
| Credentials | `aws sts get-caller-identity` | HALT; log error |
| API name unique | `aws apigateway get-rest-apis` | Warn if similar name exists |

#### Execute — CLI
```bash
aws apigateway create-rest-api \
  --name "{{user.api_name}}" \
  --description "Managed by AIOps" \
  --endpoint-configuration types=REGIONAL \
  --output json
```
Save `{{output.api_id}}` from `.id`.

#### Execute — boto3
```python
client = boto3.client('apigateway', region_name='{{env.AWS_DEFAULT_REGION}}')
resp = client.create_rest_api(
    name='{{user.api_name}}',
    endpointConfiguration={'types': ['REGIONAL']}
)
```

#### Validate
```bash
aws apigateway get-rest-api --rest-api-id "{{user.api_id}}" \
  --query "{Name:name,Endpoint:endpointConfiguration.types[0]}"
```

### Operation: Create Resource + Method (Lambda Proxy)

#### Pre-flight
- REST API must exist (`{{user.api_id}}`)
- Lambda function ARN must be provided
- Get root resource ID

```bash
aws apigateway get-resources --rest-api-id "{{user.api_id}}" \
  --query "items[?path=='/'].id" --output text
```

#### Execute — Create Resource
```bash
aws apigateway create-resource \
  --rest-api-id "{{user.api_id}}" \
  --parent-id "{{output.root_resource_id}}" \
  --path-part "{{user.resource_path}}" \
  --output json
```
Save `{{output.resource_id}}` from `.id`.

#### Execute — Create Method (ANY)
```bash
aws apigateway put-method \
  --rest-api-id "{{user.api_id}}" \
  --resource-id "{{output.resource_id}}" \
  --http-method ANY \
  --authorization-type NONE \
  --output json
```

#### Execute — Put Integration (Lambda Proxy)
```bash
aws apigateway put-integration \
  --rest-api-id "{{user.api_id}}" \
  --resource-id "{{output.resource_id}}" \
  --http-method ANY \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri "arn:aws:apigateway:{{env.AWS_DEFAULT_REGION}}:lambda:path/2015-03-31/functions/{{user.lambda_arn}}/invocations" \
  --output json
```

#### Execute — PUT Method Response + Integration Response
```bash
aws apigateway put-method-response \
  --rest-api-id "{{user.api_id}}" \
  --resource-id "{{output.resource_id}}" \
  --http-method ANY \
  --status-code 200

aws apigateway put-integration-response \
  --rest-api-id "{{user.api_id}}" \
  --resource-id "{{output.resource_id}}" \
  --http-method ANY \
  --status-code 200 \
  --selection-pattern ""
```

#### Validate
```bash
aws apigateway get-method --rest-api-id "{{user.api_id}}" \
  --resource-id "{{output.resource_id}}" \
  --http-method ANY \
  --query "{Auth:authorizationType,Integration:methodIntegration.type}"
```

### Operation: Deploy API

#### Execute — CLI
```bash
aws apigateway create-deployment \
  --rest-api-id "{{user.api_id}}" \
  --stage-name "{{user.stage_name}}" \
  --description "Deploy by AIOps" \
  --output json
```

#### Validate
```bash
aws apigateway get-stage \
  --rest-api-id "{{user.api_id}}" \
  --stage-name "{{user.stage_name}}" \
  --query "{Deploy:deploymentId,Status:cacheClusterStatus,Url:{\"invoke URL\":\"https://{{user.api_id}}.execute-api.{{env.AWS_DEFAULT_REGION}}.amazonaws.com/{{user.stage_name}}\"}}"
```

### Operation: Delete Stage

**Safety Gate**: Confirm before deleting a stage in production.

```bash
# Pre-flight: check if stage has active deployments
aws apigateway get-stage --rest-api-id "{{user.api_id}}" \
  --stage-name "{{user.stage_name}}" \
  --query "{Deploy:deploymentId,Cache:cacheClusterEnabled}"
```

```text
[WARN] Deleting stage '{{user.stage_name}}' will make the API endpoint unreachable.
Type 'DELETE_STAGE {{user.stage_name}}' to confirm.
```

```bash
aws apigateway delete-stage \
  --rest-api-id "{{user.api_id}}" \
  --stage-name "{{user.stage_name}}"
```

### Operation: Delete REST API

**Safety Gate**: MUST obtain explicit user confirmation. Deleting removes all resources, methods, deployments, and stages.

```bash
# Pre-flight: check existing stages
aws apigateway get-stages --rest-api-id "{{user.api_id}}" \
  --query "item[].stageName"
```

```text
[WARN] Deleting REST API '{{user.api_name}}' ({{user.api_id}}) is IRREVERSIBLE.
All resources, methods, stages, and deployments will be permanently removed.
Type 'DELETE_API {{user.api_id}}' to confirm.
```

```bash
aws apigateway delete-rest-api --rest-api-id "{{user.api_id}}"
```

## Recover

| Error | Action |
|-------|--------|
| `ConflictException` | Resource/method already exists; use update instead of create |
| `NotFoundException` | Verify REST API ID and resource ID exist |
| `LimitExceededException` | Delete unused APIs or request quota increase |
| `ThrottlingException` | Backoff and retry |
| `AccessDeniedException` | Check IAM permissions for apigateway actions |

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)

## Token Efficiency

All 6 TE rules applied. Key points:
- TE-1: No hardcoded endpoint types/limits — use `get-rest-apis` / `get-stages`
- TE-2: Inline comments only in boto3 code
- TE-3: Compact error tables
- TE-4: JSON paths declared inline
- TE-5: YAML anchors in `assets/example-config.yaml`
- TE-6: Flows only in SKILL.md

## Quality Gate (GCL)

| Setting | Value |
|---|---|
| Class | `required` |
| `max_iterations` | `2` |
| Rubric | `references/rubric.md` (v1) |
| Prompts | `references/prompt-templates.md` (v1) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |

Destructive ops requiring `{{user.safety_confirm}}`:
- `delete-rest-api` — IRREVERSIBLE; confirm `DELETE_API <id>`
- `delete-stage` — breaks endpoint; confirm `DELETE_STAGE <name>`

Relevant AWS rules: A7 (region), A8 (API ID echoed from describe), A10 (sts first).