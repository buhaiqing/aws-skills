# boto3 SDK Usage - DynamoDB

Python boto3 patterns for DynamoDB operations.

## Client Initialization

```python
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

# Standard client
dynamodb = boto3.client('dynamodb', region_name='{{env.AWS_DEFAULT_REGION}}')

# With retry configuration
config = Config(
    retries={
        'max_attempts': 10,
        'mode': 'adaptive'
    }
)
dynamodb = boto3.client('dynamodb', region_name='{{env.AWS_DEFAULT_REGION}}', config=config)

# Resource interface (higher-level, DynamoDB-specific types)
dynamodb_resource = boto3.resource('dynamodb', region_name='{{env.AWS_DEFAULT_REGION}}')
```

## Table Operations

### Create Table
```python
def create_table(
    table_name: str,
    partition_key: str,
    partition_key_type: str = 'S',
    sort_key: str = None,
    sort_key_type: str = None,
    rcu: int = 5,
    wcu: int = 5,
    billing_mode: str = 'PROVISIONED'
):
    # Provisioned or on-demand based on billing_mode
    try:
        attribute_definitions = [
            {'AttributeName': partition_key, 'AttributeType': partition_key_type}
        ]
        key_schema = [
            {'AttributeName': partition_key, 'KeyType': 'HASH'}
        ]

        if sort_key:
            attribute_definitions.append(
                {'AttributeName': sort_key, 'AttributeType': sort_key_type}
            )
            key_schema.append(
                {'AttributeName': sort_key, 'KeyType': 'RANGE'}
            )

        params = {
            'TableName': table_name,
            'AttributeDefinitions': attribute_definitions,
            'KeySchema': key_schema
        }

        if billing_mode == 'PROVISIONED':
            params['BillingMode'] = 'PROVISIONED'
            params['ProvisionedThroughput'] = {
                'ReadCapacityUnits': rcu,
                'WriteCapacityUnits': wcu
            }
        else:
            params['BillingMode'] = 'PAY_PER_REQUEST'

        response = dynamodb.create_table(**params)
        return response['TableDescription']

    except ClientError as e:
        handle_dynamodb_error(e)
```

### Describe Table
```python
def describe_table(table_name: str) -> dict:
    # Returns full Table description dict
    try:
        response = dynamodb.describe_table(TableName=table_name)
        return response['Table']
    except ClientError as e:
        handle_dynamodb_error(e)

def get_table_status(table_name: str) -> str:
    # Returns TableStatus string (CREATING/ACTIVE/UPDATING/DELETING)
    table = describe_table(table_name)
    return table['TableStatus']

def get_table_capacity(table_name: str) -> tuple:
    # Returns (rcu, wcu) or None for on-demand
    table = describe_table(table_name)
    billing_mode = table.get('BillingModeSummary', {}).get('BillingMode', 'PROVISIONED')
    if billing_mode == 'PAY_PER_REQUEST':
        return None
    throughput = table['ProvisionedThroughput']
    return (throughput['ReadCapacityUnits'], throughput['WriteCapacityUnits'])
```

### Update Table Capacity
```python
def update_table_capacity(table_name: str, rcu: int, wcu: int) -> dict:
    # Update provisioned throughput
    try:
        response = dynamodb.update_table(
            TableName=table_name,
            ProvisionedThroughput={
                'ReadCapacityUnits': rcu,
                'WriteCapacityUnits': wcu
            }
        )
        return response['TableDescription']
    except ClientError as e:
        handle_dynamodb_error(e)

def switch_to_on_demand(table_name: str) -> dict:
    # Switch table to PAY_PER_REQUEST billing mode
    try:
        response = dynamodb.update_table(
            TableName=table_name,
            BillingMode='PAY_PER_REQUEST'
        )
        return response['TableDescription']
    except ClientError as e:
        handle_dynamodb_error(e)
```

### Delete Table
```python
def delete_table(table_name: str) -> dict:
    # SAFETY: All data permanently lost. Requires confirmation token.
    try:
        response = dynamodb.delete_table(TableName=table_name)
        return response['TableDescription']
    except ClientError as e:
        handle_dynamodb_error(e)
```

## Item Operations

### Put Item
```python
def put_item(table_name: str, item: dict, condition_expression: str = None) -> dict:
    # item = {'id': {'S': 'user123'}, 'name': {'S': 'John'}}
    # condition_expression e.g. 'attribute_not_exists(id)'
    try:
        params = {'TableName': table_name, 'Item': item}
        if condition_expression:
            params['ConditionExpression'] = condition_expression
        response = dynamodb.put_item(**params)
        return response
    except ClientError as e:
        handle_dynamodb_error(e)
```

### Get Item
```python
def get_item(table_name: str, key: dict, consistent_read: bool = False) -> dict:
    # key = {'id': {'S': 'user123'}}; consistent_read=True for strong consistency
    try:
        response = dynamodb.get_item(
            TableName=table_name,
            Key=key,
            ConsistentRead=consistent_read
        )
        return response.get('Item')
    except ClientError as e:
        handle_dynamodb_error(e)
```

### Update Item
```python
def update_item(
    table_name: str,
    key: dict,
    update_expression: str,
    attribute_values: dict,
    return_values: str = 'NONE'
):
    # update_expression: SET/REMOVE/ADD/DELETE expressions
    # return_values: NONE/ALL_OLD/UPDATED_OLD/ALL_NEW/UPDATED_NEW
    try:
        response = dynamodb.update_item(
            TableName=table_name,
            Key=key,
            UpdateExpression=update_expression,
            ExpressionAttributeValues=attribute_values,
            ReturnValues=return_values
        )
        return response.get('Attributes')
    except ClientError as e:
        handle_dynamodb_error(e)
```

### Delete Item
```python
def delete_item(table_name: str, key: dict, return_values: str = 'NONE') -> dict:
    # return_values='ALL_OLD' returns the deleted item
    try:
        response = dynamodb.delete_item(
            TableName=table_name,
            Key=key,
            ReturnValues=return_values
        )
        return response.get('Attributes')
    except ClientError as e:
        handle_dynamodb_error(e)
```

## Query Operations

### Query
```python
def query_table(
    table_name: str,
    key_condition_expression: str,
    attribute_values: dict,
    consistent_read: bool = False,
    limit: int = None,
    scan_forward: bool = True
):
    # key_condition_expression: partition key required, e.g. 'user_id = :uid'
    # consistent_read: default False (eventual); True for strong consistency
    # scan_forward: True=ascending, False=descending sort order
    try:
        params = {
            'TableName': table_name,
            'KeyConditionExpression': key_condition_expression,
            'ExpressionAttributeValues': attribute_values,
            'ConsistentRead': consistent_read,
            'ScanIndexForward': scan_forward
        }
        if limit:
            params['Limit'] = limit
        response = dynamodb.query(**params)
        return response
    except ClientError as e:
        handle_dynamodb_error(e)

def query_all_items(table_name: str, key_condition: str, values: dict) -> list:
    # Paginated query — returns all matching items
    items = []
    last_key = None
    while True:
        params = {
            'TableName': table_name,
            'KeyConditionExpression': key_condition,
            'ExpressionAttributeValues': values
        }
        if last_key:
            params['ExclusiveStartKey'] = last_key
        response = dynamodb.query(**params)
        items.extend(response['Items'])
        last_key = response.get('LastEvaluatedKey')
        if not last_key:
            break
    return items
```

## Scan Operations

### Scan
```python
def scan_table(
    table_name: str,
    filter_expression: str = None,
    attribute_values: dict = None,
    limit: int = None,
    projection_expression: str = None
):
    # filter_expression: client-side filter after query
    # projection_expression: attribute names to return
    try:
        params = {'TableName': table_name}
        if filter_expression:
            params['FilterExpression'] = filter_expression
        if attribute_values:
            params['ExpressionAttributeValues'] = attribute_values
        if limit:
            params['Limit'] = limit
        if projection_expression:
            params['ProjectionExpression'] = projection_expression
        response = dynamodb.scan(**params)
        return response
    except ClientError as e:
        handle_dynamodb_error(e)

def scan_all_items(table_name: str) -> list:
    # Paginated scan — avoid in production for large tables
    items = []
    last_key = None
    while True:
        params = {'TableName': table_name}
        if last_key:
            params['ExclusiveStartKey'] = last_key
        response = dynamodb.scan(**params)
        items.extend(response['Items'])
        last_key = response.get('LastEvaluatedKey')
        if not last_key:
            break
    return items

def parallel_scan(table_name: str, total_segments: int = 4) -> list:
    # Parallel scan splits table into segments scanned concurrently
    import concurrent.futures

    def scan_segment(segment: int):
        items = []
        last_key = None
        while True:
            params = {
                'TableName': table_name,
                'TotalSegments': total_segments,
                'Segment': segment
            }
            if last_key:
                params['ExclusiveStartKey'] = last_key
            response = dynamodb.scan(**params)
            items.extend(response['Items'])
            last_key = response.get('LastEvaluatedKey')
            if not last_key:
                break
        return items

    with concurrent.futures.ThreadPoolExecutor(max_workers=total_segments) as executor:
        futures = [executor.submit(scan_segment, i) for i in range(total_segments)]
        results = [f.result() for f in futures]
    all_items = []
    for items in results:
        all_items.extend(items)
    return all_items
```

## GSI Operations

### Create GSI
```python
def create_gsi(
    table_name: str,
    index_name: str,
    partition_key: str,
    partition_key_type: str = 'S',
    sort_key: str = None,
    sort_key_type: str = None,
    projection_type: str = 'ALL',
    non_key_attributes: list = None,
    rcu: int = 5,
    wcu: int = 5
):
    # projection_type: ALL / KEYS_ONLY / INCLUDE
    # non_key_attributes: required for INCLUDE projection
    try:
        attribute_definitions = [
            {'AttributeName': partition_key, 'AttributeType': partition_key_type}
        ]
        key_schema = [
            {'AttributeName': partition_key, 'KeyType': 'HASH'}
        ]

        if sort_key:
            attribute_definitions.append(
                {'AttributeName': sort_key, 'AttributeType': sort_key_type}
            )
            key_schema.append(
                {'AttributeName': sort_key, 'KeyType': 'RANGE'}
            )

        projection = {'ProjectionType': projection_type}
        if non_key_attributes and projection_type == 'INCLUDE':
            projection['NonKeyAttributes'] = non_key_attributes

        response = dynamodb.update_table(
            TableName=table_name,
            AttributeDefinitions=attribute_definitions,
            GlobalSecondaryIndexUpdates=[
                {
                    'Create': {
                        'IndexName': index_name,
                        'KeySchema': key_schema,
                        'Projection': projection,
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': rcu,
                            'WriteCapacityUnits': wcu
                        }
                    }
                }
            ]
        )
        return response
    except ClientError as e:
        handle_dynamodb_error(e)
```

## Waiters

```python
def wait_for_table_active(table_name: str, timeout: int = 600) -> bool:
    # timeout in seconds; returns True if ACTIVE, False on timeout
    waiter = dynamodb.get_waiter('table_exists')
    try:
        waiter.wait(
            TableName=table_name,
            WaiterConfig={'Delay': 10, 'MaxAttempts': timeout // 10}
        )
        return True
    except Exception:
        return False

def wait_for_table_deleted(table_name: str, timeout: int = 300) -> bool:
    # timeout in seconds; returns True if deleted, False on timeout
    waiter = dynamodb.get_waiter('table_not_exists')
    try:
        waiter.wait(
            TableName=table_name,
            WaiterConfig={'Delay': 10, 'MaxAttempts': timeout // 10}
        )
        return True
    except Exception:
        return False
```

## Error Handling

```python
def handle_dynamodb_error(error: ClientError):
    # Consistent error handler; raises Exception with recovery guidance
    error_code = error.response['Error']['Code']
    error_message = error.response['Error']['Message']

    recovery_map = {
        'TableAlreadyExists': 'HALT - Table exists. Use describe-table.',
        'ResourceNotFoundException': 'HALT - Table not found. Check name.',
        'LimitExceededException': 'HALT - Wait or reduce capacity.',
        'ProvisionedThroughputExceededException': 'RETRY - Exponential backoff, max 10 retries.',
        'ConditionalCheckFailedException': 'HALT - Condition failed. Item may already exist.',
        'ValidationException': 'FIX - Check attribute types or expression syntax.',
        'ItemCollectionSizeLimitExceededException': 'HALT - Reduce item size or split items.',
        'TransactionConflictException': 'RETRY - Transaction conflict, retry operation.',
        'IdempotentParameterMismatchException': 'HALT - Different idempotent token used.',
    }

    recovery = recovery_map.get(error_code, 'HALT - Check AWS documentation.')
    raise Exception(f"DynamoDB Error [{error_code}]: {error_message}\nRecovery: {recovery}")
```
