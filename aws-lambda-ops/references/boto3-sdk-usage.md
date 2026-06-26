# boto3 SDK Usage - Lambda Operations

Python SDK patterns for AWS Lambda operations with error handling.

## Client Initialization
```python
import boto3
from botocore.exceptions import ClientError
lambda_client = boto3.client('lambda', region_name='{{env.AWS_DEFAULT_REGION}}')
# Credentials from env: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN
```

## Helper
```python
def handle_lambda_error(error):
    code = error.response['Error']['Code']
    recovery = {
        'InvalidParameterValueException': 'fix_params',
        'ResourceNotFoundException': 'halt',
        'ResourceConflictException': 'retry',
        'CodeStorageExceededException': 'halt',
        'ThrottlingException': 'retry',
        'ServiceException': 'retry',
    }
    return recovery.get(code, 'halt')
```

## Function Operations

### Create Function
```python
def create_function(name, runtime, role_arn, handler, s3_bucket, s3_key, timeout=30, memory=256, env_vars=None):
    kwargs = {'FunctionName': name, 'Runtime': runtime, 'Role': role_arn, 'Handler': handler,
              'Code': {'S3Bucket': s3_bucket, 'S3Key': s3_key}, 'Timeout': timeout, 'MemorySize': memory, 'Publish': True}
    if env_vars: kwargs['Environment'] = {'Variables': env_vars}
    try:
        r = lambda_client.create_function(**kwargs)
        return {'arn': r['FunctionArn'], 'state': r['State'], 'version': r['Version']}
    except ClientError as e: raise
```

### Update Function Code
```python
def update_function_code(name, s3_bucket=None, s3_key=None, zip_path=None, publish=True):
    kwargs = {'FunctionName': name, 'Publish': publish}
    if s3_bucket and s3_key: kwargs.update({'S3Bucket': s3_bucket, 'S3Key': s3_key})
    elif zip_path:
        with open(zip_path, 'rb') as f: kwargs['ZipFile'] = f.read()
    try:
        r = lambda_client.update_function_code(**kwargs)
        return {'arn': r['FunctionArn'], 'state': r['State'], 'version': r['Version']}
    except ClientError as e: raise
```

### Update Function Configuration
```python
def update_function_config(name, **kwargs):
    params = {'FunctionName': name}
    for k in ('runtime', 'handler', 'timeout', 'memory_size', 'role_arn', 'description'):
        if kwargs.get(k): params[k.replace('_', ' ').title().replace(' ', '')] = kwargs[k]
    if 'environment' in kwargs: params['Environment'] = {'Variables': kwargs['environment']}
    try: return lambda_client.update_function_configuration(**params)
    except ClientError as e: raise
```

### Invoke Function
```python
import json, base64
def invoke_function(name, payload, inv_type='RequestResponse', qualifier=None):
    kwargs = {'FunctionName': name, 'InvocationType': inv_type, 'Payload': json.dumps(payload)}
    if qualifier: kwargs['Qualifier'] = qualifier
    try:
        r = lambda_client.invoke(**kwargs)
        result = {'status_code': r['StatusCode'], 'version': r.get('ExecutedVersion')}
        if inv_type == 'RequestResponse' and 'Payload' in r:
            result['payload'] = json.loads(r['Payload'].read())
        if 'LogResult' in r: result['logs'] = base64.b64decode(r['LogResult']).decode()
        if 'FunctionError' in r: result['error'] = r['FunctionError']
        return result
    except ClientError as e: raise
```

### List Functions (paginated)
```python
def list_functions(max_items=100):
    funcs, paginator = [], lambda_client.get_paginator('list_functions')
    for page in paginator.paginate():
        for f in page['Functions']:
            funcs.append({'name': f['FunctionName'], 'arn': f['FunctionArn'], 'runtime': f.get('Runtime')})
            if len(funcs) >= max_items: return funcs[:max_items]
    return funcs
```

### Delete Function
```python
def delete_function(name):
    try: lambda_client.delete_function(FunctionName=name); return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException': raise ValueError(f"Function not found: {name}")
        raise
```

## Layer Operations
```python
def publish_layer_version(name, s3_bucket=None, s3_key=None, zip_path=None, runtimes=None):
    content = {}
    if s3_bucket and s3_key: content = {'S3Bucket': s3_bucket, 'S3Key': s3_key}
    elif zip_path:
        with open(zip_path, 'rb') as f: content = {'ZipFile': f.read()}
    try:
        r = lambda_client.publish_layer_version(LayerName=name, Content=content,
                                                 CompatibleRuntimes=runtimes or [])
        return {'layer_arn': r['LayerArn'], 'version': r['Version']}
    except ClientError as e: raise

def list_layers():
    layers, paginator = [], lambda_client.get_paginator('list_layers')
    for page in paginator.paginate():
        for l in page['Layers']: layers.append({'name': l['LayerName'], 'arn': l['LayerArn']})
    return layers
```

## Event Source Mapping
```python
def create_event_source_mapping(name, source_arn, batch_size=10, enabled=True, start_pos=None):
    kwargs = {'FunctionName': name, 'EventSourceArn': source_arn, 'BatchSize': batch_size, 'Enabled': enabled}
    if start_pos: kwargs['StartingPosition'] = start_pos
    try:
        r = lambda_client.create_event_source_mapping(**kwargs)
        return {'uuid': r['UUID'], 'state': r['State']}
    except ClientError as e: raise
```

## Version & Alias
```python
def publish_version(name, description=None):
    kwargs = {'FunctionName': name}
    if description: kwargs['Description'] = description
    try: return lambda_client.publish_version(**kwargs)
    except ClientError as e: raise

def create_alias(name, alias, version, routing=None):
    kwargs = {'FunctionName': name, 'Name': alias, 'FunctionVersion': version}
    if routing: kwargs['RoutingConfig'] = routing
    try: return lambda_client.create_alias(**kwargs)
    except ClientError as e: raise
```

## Waiters
```python
waiter = lambda_client.get_waiter('function_active')
waiter.wait(FunctionName='my-function', WaiterConfig={'Delay': 5, 'MaxAttempts': 60})
```

## Concurrency
```python
def set_reserved_concurrency(name, count):
    return lambda_client.put_function_concurrency(FunctionName=name, ReservedConcurrentExecutions=count)

def set_provisioned_concurrency(name, qualifier, count):
    return lambda_client.put_provisioned_concurrency_config(
        FunctionName=name, Qualifier=qualifier, ProvisionedConcurrentExecutions=count)
```

## Logging
```python
import boto3
logs_client = boto3.client('logs')
def get_function_logs(name, start_time, limit=100):
    try:
        r = logs_client.get_log_events(logGroupName=f'/aws/lambda/{name}', startTime=start_time, limit=limit)
        return r['events']
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException': return []
        raise
```