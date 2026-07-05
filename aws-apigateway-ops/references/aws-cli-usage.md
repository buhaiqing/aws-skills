# AWS CLI Usage — API Gateway (REST)

> **Pre-condition**: `aws sts get-caller-identity` before any command.

## Common JSON Paths
- REST API: `.id`, `.name`, `.endpointConfiguration.types[]`
- Resource: `.items[?path=='/'].id`, `.items[].{id,path,parentId}`
- Method: `.httpMethod`, `.authorizationType`
- Deployment: `.id`, `.createdDate`
- Stage: `.stageName`, `.deploymentId`

## Commands

```bash
# REST API lifecycle
aws apigateway create-rest-api --name "{{user.api_name}}" --endpoint-configuration types=REGIONAL --output json
aws apigateway get-rest-api --rest-api-id "{{user.rest_api_id}}" --output json
aws apigateway get-rest-apis --output json
aws apigateway delete-rest-api --rest-api-id "{{user.rest_api_id}}" --output json

# Resources
aws apigateway get-resources --rest-api-id "{{user.rest_api_id}}" --output json
aws apigateway create-resource --rest-api-id "{{user.rest_api_id}}" --parent-id "{{user.parent_id}}" --path-part "{{user.resource_path}}" --output json
aws apigateway delete-resource --rest-api-id "{{user.rest_api_id}}" --resource-id "{{user.resource_id}}" --output json

# Methods
aws apigateway put-method --rest-api-id "{{user.rest_api_id}}" --resource-id "{{user.resource_id}}" --http-method GET --authorization-type NONE --output json
aws apigateway delete-method --rest-api-id "{{user.rest_api_id}}" --resource-id "{{user.resource_id}}" --http-method GET --output json

# Integrations
aws apigateway put-integration --rest-api-id "{{user.rest_api_id}}" --resource-id "{{user.resource_id}}" --http-method GET --type AWS_PROXY --integration-http-method POST --uri "arn:aws:apigateway:{{env.AWS_DEFAULT_REGION}}:lambda:path/2015-03-31/functions/{{user.lambda_arn}}/invocations" --output json
aws apigateway get-integration --rest-api-id "{{user.rest_api_id}}" --resource-id "{{user.resource_id}}" --http-method GET --output json

# Deployments & Stages
aws apigateway create-deployment --rest-api-id "{{user.rest_api_id}}" --stage-name "{{user.stage_name}}" --output json
aws apigateway get-deployment --rest-api-id "{{user.rest_api_id}}" --deployment-id "{{user.deployment_id}}" --output json
aws apigateway get-stages --rest-api-id "{{user.rest_api_id}}" --output json
aws apigateway update-stage --rest-api-id "{{user.rest_api_id}}" --stage-name "{{user.stage_name}}" --patch-operations op=replace,path=/variables/logLevel,value=INFO --output json
aws apigateway delete-stage --rest-api-id "{{user.rest_api_id}}" --stage-name "{{user.stage_name}}" --output json

# API Keys
aws apigateway create-api-key --name "{{user.key_name}}" --enabled --output json
aws apigateway get-api-keys --output json
aws apigateway delete-api-key --api-key "{{user.api_key_id}}" --output json

# Custom Domains
aws apigateway create-domain-name --domain-name "{{user.domain_name}}" --certificate-arn "{{user.cert_arn}}" --endpoint-configuration types=REGIONAL --output json
aws apigateway get-domain-names --output json
aws apigateway delete-domain-name --domain-name "{{user.domain_name}}" --output json
```