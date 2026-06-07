# boto3 SDK Usage — EventBridge

## Bootstrap

```python
import boto3, json, os

events = boto3.client('events', region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'))
scheduler = boto3.client('scheduler', region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'))
pipes = boto3.client('pipes', region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'))
```

## Common Patterns

### Event Rule + Target
```python
# Put rule
rule = events.put_rule(
    Name='ec2-state-change',
    EventPattern=json.dumps({
        'source': ['aws.ec2'],
        'detail-type': ['EC2 Instance State-change Notification']
    }),
    State='ENABLED'
)
rule_arn = rule['RuleArn']

# Put target
events.put_targets(
    Rule='ec2-state-change',
    Targets=[{
        'Id': '1',
        'Arn': 'arn:aws:lambda:us-east-1:123456789012:function:my-handler'
    }]
)
```

### Schedule
```python
response = scheduler.create_schedule(
    Name='my-schedule',
    ScheduleExpression='rate(5 minutes)',
    Target={
        'Arn': 'arn:aws:lambda:us-east-1:123456789012:function:my-handler',
        'RoleArn': 'arn:aws:iam::123456789012:role/scheduler-role'
    },
    FlexibleTimeWindow={'Mode': 'OFF'}
)
```

### Delete Rule (with target cleanup)
```python
# List targets
targets = events.list_targets_by_rule(Rule='my-rule')
target_ids = [t['Id'] for t in targets['Targets']]

# Remove targets
if target_ids:
    events.remove_targets(Rule='my-rule', Ids=target_ids)

# Delete rule
events.delete_rule(Name='my-rule')
```

### Archive + Replay
```python
events.create_archive(
    ArchiveName='my-archive',
    EventSourceArn='arn:aws:events:us-east-1:123456789012:event-bus/default',
    RetentionDays=30
)

events.start_replay(
    ReplayName='my-replay',
    EventSourceArn='arn:aws:events:us-east-1:123456789012:archive/my-archive',
    Destination={'Arn': 'arn:aws:events:us-east-1:123456789012:event-bus/default'},
    EventStartTime='2026-06-01T00:00:00Z',
    EventEndTime='2026-06-02T00:00:00Z'
)
```

### API Destination + Connection
```python
# Create connection
conn = events.create_connection(
    Name='my-conn',
    AuthorizationType='API_KEY',
    AuthParameters={
        'ApiKeyAuthParameters': {
            'ApiKeyName': 'X-API-Key',
            'ApiKeyValue': 'my-api-key'
        }
    }
)
conn_arn = conn['ConnectionArn']

# Create API destination
events.create_api_destination(
    Name='my-api-dest',
    ConnectionArn=conn_arn,
    InvocationEndpoint='https://api.example.com/webhook',
    HttpMethod='POST'
)
```

### Pipe
```python
pipes.create_pipe(
    Name='my-pipe',
    Source='arn:aws:sqs:us-east-1:123456789012:my-queue',
    Target='arn:aws:lambda:us-east-1:123456789012:function:my-handler',
    RoleArn='arn:aws:iam::123456789012:role/pipe-role'
)
```

## Error Handling

```python
from botocore.exceptions import ClientError

try:
    events.put_rule(Name='my-rule', EventPattern='{}', State='ENABLED')
except ClientError as e:
    code = e.response['Error']['Code']
    if code == 'ResourceNotFoundException':
        # Event bus doesn't exist
        pass
    elif code == 'ConcurrentModificationException':
        # Retry
        pass
    elif code == 'LimitExceededException':
        raise RuntimeError(f"Resource limit exceeded: {e.response['Error']['Message']}")
    else:
        raise
```

## Retry Strategy

```python
from botocore.config import Config
events = boto3.client('events', config=Config(retries={'max_attempts': 3, 'mode': 'adaptive'}))