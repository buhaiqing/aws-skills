# boto3 SDK Usage - SQS

Python boto3 patterns for SQS operations.

## Client Initialization

```python
import boto3
from botocore.exceptions import ClientError

sqs = boto3.client('sqs', region_name='{{env.AWS_DEFAULT_REGION}}')
```

## Queue Operations

```python
def create_queue(name: str, attributes: dict = None, fifo: bool = False) -> str:
    """Create a queue and return URL."""
    try:
        params = {'QueueName': name}
        
        if fifo:
            name = f"{name}.fifo" if not name.endswith('.fifo') else name
            params['QueueName'] = name
            params['Attributes'] = {
                'FifoQueue': 'true',
                'ContentBasedDeduplication': 'true'
            }
        
        if attributes:
            params['Attributes'] = attributes
        
        response = sqs.create_queue(**params)
        return response['QueueUrl']
    except ClientError as e:
        handle_sqs_error(e)

def get_queue_url(name: str) -> str:
    """Get queue URL by name."""
    try:
        response = sqs.get_queue_url(QueueName=name)
        return response['QueueUrl']
    except ClientError as e:
        handle_sqs_error(e)

def delete_queue(queue_url: str):
    """Delete a queue."""
    try:
        sqs.delete_queue(QueueUrl=queue_url)
    except ClientError as e:
        handle_sqs_error(e)
```

## Message Operations

```python
def send_message(queue_url: str, body: str, delay: int = 0, attributes: dict = None) -> str:
    """Send a message to queue."""
    try:
        params = {
            'QueueUrl': queue_url,
            'MessageBody': body
        }
        if delay > 0:
            params['DelaySeconds'] = delay
        if attributes:
            params['MessageAttributes'] = attributes
        
        response = sqs.send_message(**params)
        return response['MessageId']
    except ClientError as e:
        handle_sqs_error(e)

def receive_messages(queue_url: str, max_num: int = 1, wait_time: int = 0, visibility_timeout: int = 30) -> list:
    """Receive messages from queue."""
    try:
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=max_num,
            WaitTimeSeconds=wait_time,
            VisibilityTimeout=visibility_timeout
        )
        return response.get('Messages', [])
    except ClientError as e:
        handle_sqs_error(e)

def delete_message(queue_url: str, receipt_handle: str):
    """Delete a message."""
    try:
        sqs.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle
        )
    except ClientError as e:
        handle_sqs_error(e)

def purge_queue(queue_url: str):
    """Purge all messages from queue."""
    try:
        sqs.purge_queue(QueueUrl=queue_url)
    except ClientError as e:
        handle_sqs_error(e)
```

## Error Handling

```python
def handle_sqs_error(error: ClientError):
    """Handle SQS errors."""
    error_code = error.response['Error']['Code']
    error_message = error.response['Error']['Message']
    
    recovery_map = {
        'QueueDoesNotExist': 'HALT - Queue does not exist.',
        'QueueDeletedRecently': 'WAIT - Queue deleted recently, wait 60 seconds.',
        'InvalidMessageContents': 'FIX - Invalid characters in message.',
        'MessageTooLarge': 'FIX - Message exceeds 256KB limit.',
        'OverLimit': 'HALT - Exceeded queue limit.',
        'ReceiptHandleIsInvalid': 'FIX - Invalid receipt handle.',
        'PurgeQueueInProgress': 'WAIT - Purge already in progress.',
    }
    
    recovery = recovery_map.get(error_code, 'HALT - Check AWS documentation.')
    raise Exception(f"SQS Error [{error_code}]: {error_message}\nRecovery: {recovery}")
```