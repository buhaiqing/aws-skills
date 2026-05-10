# boto3 SDK Usage - Lambda Operations

Python SDK patterns for AWS Lambda operations with error handling.

## Client Initialization

```python
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

# Standard client
lambda_client = boto3.client(
    'lambda',
    region_name='{{env.AWS_DEFAULT_REGION}}'
)

# Client with retry configuration
lambda_client = boto3.client(
    'lambda',
    region_name='{{env.AWS_DEFAULT_REGION}}',
    config=Config(
        retries={
            'max_attempts': 3,
            'mode': 'adaptive'
        }
    )
)

# Credentials from environment (automatic)
# AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN
```

## Function Operations

### Create Function

```python
def create_function(
    function_name: str,
    runtime: str,
    role_arn: str,
    handler: str,
    code_s3_bucket: str,
    code_s3_key: str,
    timeout: int = 30,
    memory_size: int = 256,
    environment: dict = None,
    description: str = None
) -> dict:
    """
    Create a new Lambda function.
    
    Args:
        function_name: Function name (must be unique in region)
        runtime: Runtime identifier (python3.11, nodejs20.x, etc.)
        role_arn: IAM execution role ARN
        handler: Handler function (module.handler)
        code_s3_bucket: S3 bucket containing deployment package
        code_s3_key: S3 key for deployment package
        timeout: Execution timeout in seconds (1-900)
        memory_size: Memory allocation in MB (128-10240)
        environment: Environment variables dict
        description: Function description
    
    Returns:
        Function creation response dict
    
    Raises:
        ClientError: Invalid parameters, quota exceeded, role not found
    """
    try:
        kwargs = {
            'FunctionName': function_name,
            'Runtime': runtime,
            'Role': role_arn,
            'Handler': handler,
            'Code': {
                'S3Bucket': code_s3_bucket,
                'S3Key': code_s3_key
            },
            'Timeout': timeout,
            'MemorySize': memory_size,
            'Publish': True
        }
        
        if environment:
            kwargs['Environment'] = {'Variables': environment}
        if description:
            kwargs['Description'] = description
            
        response = lambda_client.create_function(**kwargs)
        
        return {
            'function_arn': response['FunctionArn'],
            'state': response['State'],
            'version': response['Version'],
            'last_modified': response['LastModified']
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceNotFoundException':
            raise ValueError(f"IAM role not found: {role_arn}")
        elif error_code == 'InvalidParameterValueException':
            raise ValueError(f"Invalid parameter: {e.response['Error']['Message']}")
        elif error_code == 'CodeStorageExceededException':
            raise RuntimeError("Code storage limit exceeded")
        raise
```

### Update Function Code

```python
def update_function_code(
    function_name: str,
    s3_bucket: str = None,
    s3_key: str = None,
    zip_file_path: str = None,
    publish: bool = True
) -> dict:
    """
    Update Lambda function deployment package.
    
    Args:
        function_name: Target function name
        s3_bucket: S3 bucket for deployment package
        s3_key: S3 key for deployment package
        zip_file_path: Local zip file path (alternative to S3)
        publish: Publish new version after update
    
    Returns:
        Update response with state and version
    """
    try:
        kwargs = {
            'FunctionName': function_name,
            'Publish': publish
        }
        
        if s3_bucket and s3_key:
            kwargs['S3Bucket'] = s3_bucket
            kwargs['S3Key'] = s3_key
        elif zip_file_path:
            with open(zip_file_path, 'rb') as f:
                kwargs['ZipFile'] = f.read()
        else:
            raise ValueError("Must provide S3 location or zip file path")
        
        response = lambda_client.update_function_code(**kwargs)
        
        return {
            'function_arn': response['FunctionArn'],
            'state': response['State'],
            'version': response['Version'],
            'last_modified': response['LastModified']
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceNotFoundException':
            raise ValueError(f"Function not found: {function_name}")
        raise


def wait_for_function_update(function_name: str, timeout: int = 300) -> bool:
    """
    Wait for function update to complete (Successful state).
    
    Args:
        function_name: Function name to wait for
        timeout: Maximum wait time in seconds
    
    Returns:
        True if update successful, False if timeout
    """
    import time
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        response = lambda_client.get_function(FunctionName=function_name)
        state = response['Configuration']['State']
        
        if state == 'Active':
            return True
        elif state in ('Failed', 'Inactive'):
            return False
        
        time.sleep(5)
    
    return False
```

### Update Function Configuration

```python
def update_function_configuration(
    function_name: str,
    runtime: str = None,
    handler: str = None,
    timeout: int = None,
    memory_size: int = None,
    environment: dict = None,
    role_arn: str = None,
    layers: list = None,
    description: str = None
) -> dict:
    """
    Update Lambda function configuration settings.
    
    Args:
        function_name: Target function name
        runtime: New runtime (python3.11, nodejs20.x, etc.)
        handler: New handler function
        timeout: New timeout in seconds
        memory_size: New memory in MB
        environment: New environment variables
        role_arn: New execution role ARN
        layers: List of layer ARNs
        description: New description
    
    Returns:
        Updated configuration details
    """
    try:
        kwargs = {'FunctionName': function_name}
        
        optional_params = {
            'Runtime': runtime,
            'Handler': handler,
            'Timeout': timeout,
            'MemorySize': memory_size,
            'Role': role_arn,
            'Description': description
        }
        
        for param, value in optional_params.items():
            if value is not None:
                kwargs[param] = value
        
        if environment is not None:
            kwargs['Environment'] = {'Variables': environment}
        
        if layers is not None:
            kwargs['Layers'] = layers
        
        response = lambda_client.update_function_configuration(**kwargs)
        
        return {
            'function_arn': response['FunctionArn'],
            'runtime': response.get('Runtime'),
            'handler': response.get('Handler'),
            'timeout': response.get('Timeout'),
            'memory_size': response.get('MemorySize')
        }
        
    except ClientError as e:
        raise
```

### Invoke Function

```python
import base64
import json

def invoke_function(
    function_name: str,
    payload: dict,
    invocation_type: str = 'RequestResponse',
    qualifier: str = None
) -> dict:
    """
    Invoke Lambda function.
    
    Args:
        function_name: Function name or ARN
        payload: Input payload dict
        invocation_type: RequestResponse (sync) or Event (async)
        qualifier: Version or alias name
    
    Returns:
        Invocation response with status, result, and logs
    """
    try:
        kwargs = {
            'FunctionName': function_name,
            'InvocationType': invocation_type,
            'Payload': json.dumps(payload)
        }
        
        if qualifier:
            kwargs['Qualifier'] = qualifier
        
        response = lambda_client.invoke(**kwargs)
        
        status_code = response['StatusCode']
        
        result = {
            'status_code': status_code,
            'executed_version': response.get('ExecutedVersion'),
            'success': status_code == 200 if invocation_type == 'RequestResponse' else status_code == 202
        }
        
        # Decode response payload for synchronous invocation
        if invocation_type == 'RequestResponse' and 'Payload' in response:
            payload_stream = response['Payload']
            result['payload'] = json.loads(payload_stream.read())
        
        # Decode logs (base64 encoded)
        if 'LogResult' in response:
            result['logs'] = base64.b64decode(response['LogResult']).decode('utf-8')
        
        # Check for function error
        if 'FunctionError' in response:
            result['error'] = response['FunctionError']
        
        return result
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceNotFoundException':
            raise ValueError(f"Function not found: {function_name}")
        elif error_code == 'InvalidParameterValueException':
            raise ValueError(f"Invalid payload or parameters")
        raise


def invoke_async(function_name: str, payload: dict) -> str:
    """
    Invoke Lambda function asynchronously (fire and forget).
    
    Args:
        function_name: Function name
        payload: Input payload
    
    Returns:
        Request ID for tracking
    """
    response = invoke_function(
        function_name=function_name,
        payload=payload,
        invocation_type='Event'
    )
    
    if response['status_code'] == 202:
        return response.get('request_id')
    else:
        raise RuntimeError(f"Async invocation failed: {response}")
```

### List Functions with Pagination

```python
def list_functions(
    runtime_filter: str = None,
    max_items: int = 100
) -> list:
    """
    List Lambda functions with pagination.
    
    Args:
        runtime_filter: Filter by runtime (optional)
        max_items: Maximum items to return
    
    Returns:
        List of function details
    """
    functions = []
    paginator = lambda_client.get_paginator('list_functions')
    
    operation_parameters = {}
    if runtime_filter:
        operation_parameters['Runtime'] = runtime_filter
    
    for page in paginator.paginate(**operation_parameters):
        for func in page['Functions']:
            functions.append({
                'name': func['FunctionName'],
                'arn': func['FunctionArn'],
                'runtime': func.get('Runtime'),
                'handler': func.get('Handler'),
                'timeout': func.get('Timeout'),
                'memory_size': func.get('MemorySize'),
                'last_modified': func['LastModified'],
                'state': func.get('State', 'Active')
            })
        
        if len(functions) >= max_items:
            break
    
    return functions[:max_items]
```

### Delete Function

```python
def delete_function(function_name: str) -> bool:
    """
    Delete Lambda function.
    
    ⚠️ DESTRUCTIVE: Requires human confirmation before execution.
    
    Args:
        function_name: Function name to delete
    
    Returns:
        True if deletion successful
    
    Raises:
        ResourceNotFoundException: Function does not exist
    """
    try:
        lambda_client.delete_function(FunctionName=function_name)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            raise ValueError(f"Function not found: {function_name}")
        raise
```

## Layer Operations

### Publish Layer Version

```python
def publish_layer_version(
    layer_name: str,
    s3_bucket: str = None,
    s3_key: str = None,
    zip_file_path: str = None,
    description: str = None,
    compatible_runtimes: list = None,
    compatible_architectures: list = None,
    license_info: str = None
) -> dict:
    """
    Publish a new Lambda layer version.
    
    Args:
        layer_name: Layer name
        s3_bucket: S3 bucket for layer content
        s3_key: S3 key for layer content
        zip_file_path: Local zip file path
        description: Layer description
        compatible_runtimes: List of compatible runtimes
        compatible_architectures: List of architectures (x86_64, arm64)
        license_info: License information
    
    Returns:
        Layer version details
    """
    try:
        kwargs = {'LayerName': layer_name}
        
        if s3_bucket and s3_key:
            kwargs['Content'] = {
                'S3Bucket': s3_bucket,
                'S3Key': s3_key
            }
        elif zip_file_path:
            with open(zip_file_path, 'rb') as f:
                kwargs['Content'] = {'ZipFile': f.read()}
        else:
            raise ValueError("Must provide S3 location or zip file")
        
        if description:
            kwargs['Description'] = description
        if compatible_runtimes:
            kwargs['CompatibleRuntimes'] = compatible_runtimes
        if compatible_architectures:
            kwargs['CompatibleArchitectures'] = compatible_architectures
        if license_info:
            kwargs['LicenseInfo'] = license_info
        
        response = lambda_client.publish_layer_version(**kwargs)
        
        return {
            'layer_arn': response['LayerArn'],
            'layer_version_arn': response['LayerVersionArn'],
            'version': response['Version'],
            'compatible_runtimes': response.get('CompatibleRuntimes', [])
        }
        
    except ClientError as e:
        raise
```

### List Layers

```python
def list_layers() -> list:
    """List all Lambda layers in account."""
    layers = []
    paginator = lambda_client.get_paginator('list_layers')
    
    for page in paginator.paginate():
        for layer in page['Layers']:
            layers.append({
                'name': layer['LayerName'],
                'arn': layer['LayerArn'],
                'latest_version': layer.get('LatestMatchingVersion', {}).get('Version')
            })
    
    return layers
```

## Event Source Mapping Operations

### Create Event Source Mapping

```python
def create_event_source_mapping(
    function_name: str,
    event_source_arn: str,
    batch_size: int = 10,
    maximum_batching_window: int = 0,
    starting_position: str = None,
    enabled: bool = True
) -> dict:
    """
    Create event source mapping for Lambda function.
    
    Args:
        function_name: Lambda function name
        event_source_arn: Source ARN (SQS, DynamoDB stream, Kinesis)
        batch_size: Batch size for processing
        maximum_batching_window: Batch window in seconds
        starting_position: Stream position (LATEST, TRIM_HORIZON)
        enabled: Enable mapping immediately
    
    Returns:
        Mapping UUID and state
    """
    try:
        kwargs = {
            'FunctionName': function_name,
            'EventSourceArn': event_source_arn,
            'BatchSize': batch_size,
            'Enabled': enabled
        }
        
        if maximum_batching_window > 0:
            kwargs['MaximumBatchingWindowInSeconds'] = maximum_batching_window
        
        # Required for DynamoDB/Kinesis streams
        if starting_position:
            kwargs['StartingPosition'] = starting_position
        
        response = lambda_client.create_event_source_mapping(**kwargs)
        
        return {
            'uuid': response['UUID'],
            'state': response['State'],
            'batch_size': response['BatchSize'],
            'event_source_arn': response['EventSourceArn'],
            'function_arn': response['FunctionArn']
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceNotFoundException':
            raise ValueError(f"Function or event source not found")
        raise
```

### Wait for Event Source Mapping

```python
def wait_for_mapping_enabled(uuid: str, timeout: int = 120) -> bool:
    """
    Wait for event source mapping to reach Enabled state.
    
    Args:
        uuid: Event source mapping UUID
        timeout: Maximum wait time in seconds
    
    Returns:
        True if enabled, False if failed or timeout
    """
    import time
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        response = lambda_client.get_event_source_mapping(UUID=uuid)
        state = response['State']
        
        if state == 'Enabled':
            return True
        elif state in ('Disabled', 'Deleting'):
            return False
        
        time.sleep(5)
    
    return False
```

## Version and Alias Operations

### Publish Version

```python
def publish_version(function_name: str, description: str = None) -> dict:
    """Publish current function code as new version."""
    try:
        kwargs = {'FunctionName': function_name}
        if description:
            kwargs['Description'] = description
        
        response = lambda_client.publish_version(**kwargs)
        
        return {
            'version': response['Version'],
            'function_arn': response['FunctionArn'],
            'description': response.get('Description')
        }
    except ClientError as e:
        raise
```

### Create Alias

```python
def create_alias(
    function_name: str,
    alias_name: str,
    function_version: str,
    description: str = None,
    routing_config: dict = None
) -> dict:
    """
    Create Lambda alias pointing to version.
    
    Args:
        function_name: Function name
        alias_name: Alias name (e.g., 'prod', 'dev')
        function_version: Version number to point to
        description: Alias description
        routing_config: Weighted routing (for canary deployments)
    
    Returns:
        Alias ARN and configuration
    """
    try:
        kwargs = {
            'FunctionName': function_name,
            'Name': alias_name,
            'FunctionVersion': function_version
        }
        
        if description:
            kwargs['Description'] = description
        if routing_config:
            kwargs['RoutingConfig'] = routing_config
        
        response = lambda_client.create_alias(**kwargs)
        
        return {
            'alias_arn': response['AliasArn'],
            'function_version': response['FunctionVersion'],
            'description': response.get('Description')
        }
        
    except ClientError as e:
        raise
```

## Waiters

```python
# Lambda service waiters (botocore built-in)
waiter = lambda_client.get_waiter('function_exists')
waiter.wait(FunctionName='my-function')

waiter = lambda_client.get_waiter('function_updated')
waiter.wait(FunctionName='my-function')

waiter = lambda_client.get_waiter('function_active')
waiter.wait(FunctionName='my-function')

# Custom waiter configuration
waiter_config = {
    'Delay': 5,  # seconds between checks
    'MaxAttempts': 60  # maximum attempts (5 min total)
}
waiter.wait(FunctionName='my-function', WaiterConfig=waiter_config)
```

## Error Handling Patterns

```python
from botocore.exceptions import ClientError, WaiterError

def handle_lambda_error(error: ClientError) -> str:
    """
    Classify Lambda error and determine recovery action.
    
    Returns:
        Recovery action: 'retry', 'halt', 'fix_params'
    """
    error_code = error.response['Error']['Code']
    
    recovery_map = {
        'InvalidParameterValueException': 'fix_params',
        'ResourceNotFoundException': 'halt',
        'ResourceConflictException': 'retry',  # concurrent updates
        'CodeStorageExceededException': 'halt',
        'PolicySizeLimitExceededException': 'halt',
        'ThrottlingException': 'retry',
        'ServiceException': 'retry',
        'ProvisionedConcurrencyException': 'halt'
    }
    
    return recovery_map.get(error_code, 'halt')


def execute_with_retry(
    operation_func,
    max_retries: int = 3,
    retryable_errors: set = {'ThrottlingException', 'ServiceException', 'ResourceConflictException'}
) -> dict:
    """
    Execute Lambda operation with retry logic.
    
    Args:
        operation_func: Function to execute
        max_retries: Maximum retry attempts
        retryable_errors: Set of retryable error codes
    
    Returns:
        Operation result
    
    Raises:
        RuntimeError: After max retries exhausted
    """
    import time
    
    for attempt in range(max_retries + 1):
        try:
            return operation_func()
        except ClientError as e:
            error_code = e.response['Error']['Code']
            
            if error_code not in retryable_errors:
                raise
            
            if attempt == max_retries:
                raise RuntimeError(f"Max retries ({max_retries}) exhausted")
            
            # Exponential backoff
            delay = min(2 ** attempt, 30)
            time.sleep(delay)
    
    raise RuntimeError("Unexpected retry loop exit")
```

## Concurrency Configuration

```python
def set_reserved_concurrency(function_name: str, executions: int) -> dict:
    """Set reserved concurrency for function."""
    response = lambda_client.put_function_concurrency(
        FunctionName=function_name,
        ReservedConcurrentExecutions=executions
    )
    return response

def set_provisioned_concurrency(
    function_name: str,
    qualifier: str,
    executions: int
) -> dict:
    """Set provisioned concurrency for version/alias."""
    response = lambda_client.put_provisioned_concurrency_config(
        FunctionName=function_name,
        Qualifier=qualifier,
        ProvisionedConcurrentExecutions=executions
    )
    return response
```

## Logging Integration

```python
# Lambda logs are automatically sent to CloudWatch Logs
# Log group: /aws/lambda/{function-name}

import boto3

logs_client = boto3.client('logs')

def get_function_logs(function_name: str, start_time: int, limit: int = 100) -> list:
    """
    Retrieve Lambda function logs from CloudWatch.
    
    Args:
        function_name: Function name
        start_time: Unix timestamp (milliseconds)
        limit: Maximum log events
    
    Returns:
        List of log events
    """
    log_group = f'/aws/lambda/{function_name}'
    
    try:
        response = logs_client.get_log_events(
            logGroupName=log_group,
            startTime=start_time,
            limit=limit
        )
        return response['events']
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return []  # Log group not created yet
        raise
```