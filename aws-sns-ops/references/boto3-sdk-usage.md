# boto3 SDK Usage - SNS

Python boto3 patterns for SNS operations.

## Client Initialization

```python
import boto3
from botocore.exceptions import ClientError

sns = boto3.client('sns', region_name='{{env.AWS_DEFAULT_REGION}}')
```

## Topic Operations

```python
def create_topic(name: str, fifo: bool = False) -> str:
    """Create topic and return ARN."""
    try:
        params = {'Name': name}
        
        if fifo:
            name = f"{name}.fifo" if not name.endswith('.fifo') else name
            params['Name'] = name
            params['Attributes'] = {
                'FifoTopic': 'true',
                'ContentBasedDeduplication': 'true'
            }
        
        response = sns.create_topic(**params)
        return response['TopicArn']
    except ClientError as e:
        handle_sns_error(e)

def get_topic_attributes(topic_arn: str) -> dict:
    """Get topic attributes."""
    try:
        response = sns.get_topic_attributes(TopicArn=topic_arn)
        return response['Attributes']
    except ClientError as e:
        handle_sns_error(e)

def list_topics() -> list:
    """List all topics."""
    try:
        response = sns.list_topics()
        return response.get('Topics', [])
    except ClientError as e:
        handle_sns_error(e)

def delete_topic(topic_arn: str):
    """Delete a topic."""
    try:
        sns.delete_topic(TopicArn=topic_arn)
    except ClientError as e:
        handle_sns_error(e)
```

## Subscription Operations

```python
def subscribe(topic_arn: str, protocol: str, endpoint: str) -> str:
    """Subscribe endpoint to topic."""
    try:
        response = sns.subscribe(
            TopicArn=topic_arn,
            Protocol=protocol,
            Endpoint=endpoint
        )
        return response['SubscriptionArn']
    except ClientError as e:
        handle_sns_error(e)

def list_subscriptions(topic_arn: str) -> list:
    """List subscriptions for topic."""
    try:
        response = sns.list_subscriptions_by_topic(TopicArn=topic_arn)
        return response.get('Subscriptions', [])
    except ClientError as e:
        handle_sns_error(e)

def unsubscribe(subscription_arn: str):
    """Unsubscribe from topic."""
    try:
        sns.unsubscribe(SubscriptionArn=subscription_arn)
    except ClientError as e:
        handle_sns_error(e)

def set_filter_policy(subscription_arn: str, policy: dict):
    """Set subscription filter policy."""
    try:
        sns.set_subscription_attributes(
            SubscriptionArn=subscription_arn,
            AttributeName='FilterPolicy',
            AttributeValue=json.dumps(policy)
        )
    except ClientError as e:
        handle_sns_error(e)
```

## Message Operations

```python
def publish(topic_arn: str, message: str, subject: str = None, attributes: dict = None) -> str:
    """Publish message to topic."""
    try:
        params = {
            'TopicArn': topic_arn,
            'Message': message
        }
        if subject:
            params['Subject'] = subject
        if attributes:
            params['MessageAttributes'] = attributes
        
        response = sns.publish(**params)
        return response['MessageId']
    except ClientError as e:
        handle_sns_error(e)
```

## Error Handling

```python
def handle_sns_error(error: ClientError):
    """Handle SNS errors."""
    error_code = error.response['Error']['Code']
    error_message = error.response['Error']['Message']
    
    recovery_map = {
        'NotFound': 'HALT - Resource not found.',
        'TopicNotFound': 'HALT - Topic does not exist.',
        'SubscriptionNotFound': 'HALT - Subscription does not exist.',
        'InvalidParameter': 'FIX - Invalid parameter value.',
        'InvalidParameterValue': 'FIX - Check parameter values.',
        'EndpointDisabled': 'FIX - Endpoint is disabled.',
    }
    
    recovery = recovery_map.get(error_code, 'HALT - Check AWS documentation.')
    raise Exception(f"SNS Error [{error_code}]: {error_message}\nRecovery: {recovery}")
```