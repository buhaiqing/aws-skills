# boto3 SDK Usage — API Gateway

```python
import boto3
apigw = boto3.client('apigateway', region_name='{{env.AWS_DEFAULT_REGION}}')

# Create REST API
resp = apigw.create_rest_api(
    name='{{user.api_name}}',
    description='{{user.api_description}}',
    endpointConfiguration={'types': ['REGIONAL']}
)
rest_api_id = resp['id']

# List/get APIs
apis = apigw.get_rest_apis()['items']
api = apigw.get_rest_api(restApiId=rest_api_id)

# Get root resource
resources = apigw.get_resources(restApiId=rest_api_id)['items']
root_id = next(r['id'] for r in resources if r['path'] == '/')

# Create resource
resp = apigw.create_resource(
    restApiId=rest_api_id, parentId=root_id, pathPart='{{user.path}}'
)
resource_id = resp['id']

# Create method
apigw.put_method(restApiId=rest_api_id, resourceId=resource_id, httpMethod='GET', authorizationType='NONE')

# Create Lambda proxy integration
apigw.put_integration(
    restApiId=rest_api_id, resourceId=resource_id, httpMethod='GET',
    type='AWS_PROXY', integrationHttpMethod='POST',
    uri=f"arn:aws:apigateway:{{env.AWS_DEFAULT_REGION}}:lambda:path/2015-03-31/functions/{{user.lambda_arn}}/invocations"
)

# Create deployment
resp = apigw.create_deployment(restApiId=rest_api_id, stageName='{{user.stage_name}}')
deployment_id = resp['id']

# List stages
stages = apigw.get_stages(restApiId=rest_api_id)['item']

# Update stage
apigw.update_stage(
    restApiId=rest_api_id, stageName='{{user.stage_name}}',
    patchOperations=[{'op': 'replace', 'path': '/description', 'value': 'Updated'}]
)

# Delete resource
apigw.delete_resource(restApiId=rest_api_id, resourceId=resource_id)

# Delete REST API
apigw.delete_rest_api(restApiId=rest_api_id)

# API Keys
key = apigw.create_api_key(name='{{user.key_name}}', enabled=True)['id']
apigw.get_api_keys()['items']
apigw.delete_api_key(apiKey=key)

# Custom domain names
apigw.create_domain_name(
    domainName='{{user.domain_name}}',
    certificateArn='{{user.cert_arn}}',
    endpointConfiguration={'types': ['REGIONAL']}
)
```