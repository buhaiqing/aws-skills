# boto3 SDK Usage — Amazon Athena

## Bootstrap

```python
import boto3
import os

client = boto3.client(
    'athena',
    region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
)

# With SSO profile
# session = boto3.Session(profile_name=os.environ.get('AWS_PROFILE'))
# client = session.client('athena', region_name='us-east-1')
```

## Common Patterns

### Create Workgroup
```python
client.create_work_group(
    Name='analytics-wg',
    Description='Analytics workgroup',
    Configuration={
        'ResultConfiguration': {
            'OutputLocation': 's3://my-query-results/athena/'
        }
    }
)
# Verify
wg = client.get_work_group(WorkGroup='analytics-wg')
print(wg['WorkGroup']['State'])
```

### Start Query Execution and Poll
```python
import time

response = client.start_query_execution(
    QueryString='SELECT count(*) FROM my_table',
    QueryExecutionContext={'Database': 'mydb'},
    ResultConfiguration={'OutputLocation': 's3://my-query-results/athena/'},
    WorkGroup='analytics-wg'
)
exec_id = response['QueryExecutionId']

# Poll until terminal state
for _ in range(150):  # max 300s at 2s intervals
    status = client.get_query_execution(QueryExecutionId=exec_id)
    state = status['QueryExecution']['State']
    if state in ('SUCCEEDED', 'FAILED', 'CANCELLED'):
        break
    time.sleep(2)

# Get results if succeeded
if state == 'SUCCEEDED':
    results = client.get_query_results(QueryExecutionId=exec_id)
    for row in results['ResultSet']['Rows']:
        print(row['Data'][0]['VarCharValue'])
```

### Workgroup Operations
```python
# List workgroups
paginator = client.get_paginator('list_work_groups')
for page in paginator.paginate():
    for wg in page['WorkGroups']:
        print(wg['Name'], wg['State'])

# Update workgroup
client.update_work_group(
    WorkGroup='analytics-wg',
    Description='Updated description',
    Configuration={
        'ResultConfiguration': {
            'OutputLocation': 's3://new-results/athena/'
        }
    }
)

# Delete workgroup
client.delete_work_group(WorkGroup='analytics-wg')
```

### Named Query Operations
```python
# Create
response = client.create_named_query(
    Name='daily-count',
    Database='mydb',
    QueryString='SELECT count(*) FROM events WHERE date = current_date',
    WorkGroup='analytics-wg'
)
query_id = response['NamedQueryId']

# Get
nq = client.get_named_query(NamedQueryId=query_id)
print(nq['NamedQuery']['QueryString'])

# Delete
client.delete_named_query(NamedQueryId=query_id)
```

### Data Catalog Operations
```python
# Create
client.create_data_catalog(
    Name='my-catalog',
    Type='LAMBDA',
    ConnectionType='LAMBDA',
    Parameters={'function': 'arn:aws:lambda:us-east-1:123456789012:function:my-catalog-fn'}
)

# List
catalogs = client.list_data_catalogs()
for cat in catalogs['DataCatalogsSummary']:
    print(cat['Name'], cat['Type'])

# Delete
client.delete_data_catalog(Name='my-catalog')
```

### Prepared Statement
```python
# Create
client.create_prepared_statement(
    StatementName='daily-report',
    QueryStatement='SELECT * FROM orders WHERE date > ? LIMIT 100',
    WorkGroup='analytics-wg',
    Description='Daily report template'
)

# Execute prepared statement
client.execute_statement(
    StatementName='daily-report',
    WorkGroup='analytics-wg',
    Parameters=['2026-01-01']
)

# Delete
client.delete_prepared_statement(
    StatementName='daily-report',
    WorkGroup='analytics-wg'
)
```

### Error Handling Pattern
```python
from botocore.exceptions import ClientError

try:
    client.start_query_execution(
        QueryString='SELECT * FROM nonexistent',
        QueryExecutionContext={'Database': 'mydb'},
        ResultConfiguration={'OutputLocation': 's3://bucket/prefix/'}
    )
except ClientError as e:
    code = e.response['Error']['Code']
    if code == 'InvalidRequestException':
        print(f"Invalid query: {e.response['Error']['Message']}")
    elif code == 'ThrottlingException':
        # Backoff and retry
        pass
    else:
        print(f"Error: {code}")
```
