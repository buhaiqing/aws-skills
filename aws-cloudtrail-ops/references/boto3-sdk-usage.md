# boto3 SDK Usage - CloudTrail

Python boto3 patterns for CloudTrail operations.

## Client Initialization

```python
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

# Standard client
cloudtrail = boto3.client('cloudtrail', region_name='{{env.AWS_DEFAULT_REGION}}')

# With retry configuration
config = Config(
    retries={
        'max_attempts': 5,
        'mode': 'exponential'
    }
)
cloudtrail = boto3.client('cloudtrail', region_name='{{env.AWS_DEFAULT_REGION}}', config=config)
```

## Trail Operations

### Create Trail
```python
def create_trail(
    name: str,
    s3_bucket_name: str,
    s3_key_prefix: str = None,
    is_multi_region: bool = False,
    enable_log_validation: bool = True,
    kms_key_id: str = None,
    is_organization_trail: bool = False,
    tags: list = None
):
    """
    Create a CloudTrail trail.
    
    Args:
        name: Trail name (unique per region)
        s3_bucket_name: S3 bucket for log delivery
        s3_key_prefix: Optional prefix for log files
        is_multi_region: Enable multi-region trail
        enable_log_validation: Enable log file validation (recommended)
        kms_key_id: Optional KMS key for encryption
        is_organization_trail: Enable for AWS Organization
        tags: List of tag dicts [{'Key': 'Name', 'Value': 'value'}]
    
    Returns:
        dict: Trail details
    """
    try:
        params = {
            'Name': name,
            'S3BucketName': s3_bucket_name,
            'EnableLogFileValidation': enable_log_validation
        }
        
        if s3_key_prefix:
            params['S3KeyPrefix'] = s3_key_prefix
        
        if is_multi_region:
            params['IsMultiRegionTrail'] = True
        
        if kms_key_id:
            params['KmsKeyId'] = kms_key_id
        
        if is_organization_trail:
            params['IsOrganizationTrail'] = True
        
        if tags:
            params['TagsList'] = tags
        
        response = cloudtrail.create_trail(**params)
        return response['Trail']
    
    except ClientError as e:
        handle_cloudtrail_error(e)
```

### Describe Trails
```python
def describe_trails(trail_names: list = None) -> list:
    """
    Get details of CloudTrail trails.
    
    Args:
        trail_names: Optional list of trail names to filter
    
    Returns:
        list: Trail details
    """
    try:
        params = {}
        if trail_names:
            params['trailNameList'] = trail_names
        
        response = cloudtrail.describe_trails(**params)
        return response['trailList']
    
    except ClientError as e:
        handle_cloudtrail_error(e)

def get_trail_details(trail_name: str) -> dict:
    """Get details of a specific trail."""
    trails = describe_trails([trail_name])
    return trails[0] if trails else None
```

### Get Trail Status
```python
def get_trail_status(trail_name: str) -> dict:
    """
    Get logging status of a trail.
    
    Args:
        trail_name: Trail name
    
    Returns:
        dict: Status including IsLogging, delivery info
    """
    try:
        response = cloudtrail.get_trail_status(Name=trail_name)
        return response
    except ClientError as e:
        handle_cloudtrail_error(e)

def is_trail_logging(trail_name: str) -> bool:
    """Check if trail is actively logging."""
    status = get_trail_status(trail_name)
    return status.get('IsLogging', False)
```

### Update Trail
```python
def update_trail(
    name: str,
    s3_bucket_name: str = None,
    s3_key_prefix: str = None,
    kms_key_id: str = None,
    enable_log_validation: bool = None
):
    """
    Update trail configuration.
    
    Args:
        name: Trail name
        s3_bucket_name: New S3 bucket name
        s3_key_prefix: New S3 key prefix
        kms_key_id: New KMS key ID
        enable_log_validation: Enable/disable log validation
    
    Returns:
        dict: Updated trail details
    """
    try:
        params = {'Name': name}
        
        if s3_bucket_name:
            params['S3BucketName'] = s3_bucket_name
        if s3_key_prefix:
            params['S3KeyPrefix'] = s3_key_prefix
        if kms_key_id:
            params['KmsKeyId'] = kms_key_id
        if enable_log_validation is not None:
            params['EnableLogFileValidation'] = enable_log_validation
        
        response = cloudtrail.update_trail(**params)
        return response['Trail']
    
    except ClientError as e:
        handle_cloudtrail_error(e)
```

### Delete Trail
```python
def delete_trail(name: str):
    """
    Delete a CloudTrail trail.
    
    SAFETY: Stops all logging for this trail.
    
    Args:
        name: Trail name to delete
    """
    try:
        cloudtrail.delete_trail(Name=name)
    except ClientError as e:
        handle_cloudtrail_error(e)
```

### Start/Stop Logging
```python
def start_logging(trail_name: str):
    """Start logging for a trail."""
    try:
        cloudtrail.start_logging(Name=trail_name)
    except ClientError as e:
        handle_cloudtrail_error(e)

def stop_logging(trail_name: str):
    """Stop logging for a trail."""
    try:
        cloudtrail.stop_logging(Name=trail_name)
    except ClientError as e:
        handle_cloudtrail_error(e)
```

## Event Operations

### Lookup Events
```python
def lookup_events(
    lookup_attributes: list = None,
    start_time: datetime = None,
    end_time: datetime = None,
    max_results: int = 50,
    next_token: str = None
):
    """
    Query CloudTrail events.
    
    Args:
        lookup_attributes: List of {'AttributeKey': '...', 'AttributeValue': '...'}
        start_time: Start of time range
        end_time: End of time range
        max_results: Max events to return (1-50)
        next_token: Pagination token
    
    Returns:
        dict: Events and next token
    """
    try:
        params = {'MaxResults': max_results}
        
        if lookup_attributes:
            params['LookupAttributes'] = lookup_attributes
        
        if start_time:
            params['StartTime'] = start_time
        
        if end_time:
            params['EndTime'] = end_time
        
        if next_token:
            params['NextToken'] = next_token
        
        response = cloudtrail.lookup_events(**params)
        return response
    
    except ClientError as e:
        handle_cloudtrail_error(e)

def lookup_events_by_username(username: str, max_results: int = 50):
    """Query events by username."""
    return lookup_events(
        lookup_attributes=[
            {'AttributeKey': 'Username', 'AttributeValue': username}
        ],
        max_results=max_results
    )

def lookup_events_by_event_name(event_name: str, max_results: int = 50):
    """Query events by API action name."""
    return lookup_events(
        lookup_attributes=[
            {'AttributeKey': 'EventName', 'AttributeValue': event_name}
        ],
        max_results=max_results
    )

def lookup_events_all(lookup_attributes: list = None, start_time: datetime = None, end_time: datetime = None):
    """Query all events with pagination."""
    events = []
    next_token = None
    
    while True:
        response = lookup_events(
            lookup_attributes=lookup_attributes,
            start_time=start_time,
            end_time=end_time,
            max_results=50,
            next_token=next_token
        )
        
        events.extend(response.get('Events', []))
        next_token = response.get('NextToken')
        
        if not next_token:
            break
    
    return events
```

## Event Selector Operations

### Get Event Selectors
```python
def get_event_selectors(trail_name: str) -> list:
    """
    Get event selectors for a trail.
    
    Args:
        trail_name: Trail name
    
    Returns:
        list: Event selectors
    """
    try:
        response = cloudtrail.get_event_selectors(TrailName=trail_name)
        return response.get('EventSelectors', [])
    except ClientError as e:
        handle_cloudtrail_error(e)
```

### Put Event Selectors
```python
def put_event_selectors(
    trail_name: str,
    event_selectors: list
):
    """
    Configure event selectors for data events.
    
    Args:
        trail_name: Trail name
        event_selectors: List of event selector dicts
    
    Example event_selectors:
        [
            {
                'ReadWriteType': 'All',
                'IncludeManagementEvents': True,
                'DataResources': [
                    {
                        'Type': 'AWS::S3::Object',
                        'Values': ['arn:aws:s3:::bucket/*']
                    }
                ]
            }
        ]
    
    Returns:
        dict: Updated event selectors
    """
    try:
        response = cloudtrail.put_event_selectors(
            TrailName=trail_name,
            EventSelectors=event_selectors
        )
        return response['EventSelectors']
    except ClientError as e:
        handle_cloudtrail_error(e)

def enable_s3_data_events(trail_name: str, bucket_arns: list):
    """Enable S3 data events logging."""
    selectors = [
        {
            'ReadWriteType': 'All',
            'IncludeManagementEvents': True,
            'DataResources': [
                {
                    'Type': 'AWS::S3::Object',
                    'Values': bucket_arns
                }
            ]
        }
    ]
    return put_event_selectors(trail_name, selectors)

def enable_lambda_data_events(trail_name: str, function_arns: list = None):
    """Enable Lambda data events logging."""
    values = function_arns if function_arns else ['arn:aws:lambda:*:*:function:*']
    selectors = [
        {
            'ReadWriteType': 'All',
            'IncludeManagementEvents': True,
            'DataResources': [
                {
                    'Type': 'AWS::Lambda::Function',
                    'Values': values
                }
            ]
        }
    ]
    return put_event_selectors(trail_name, selectors)
```

## Complete Flow Examples

### Create Trail Complete
```python
def create_trail_complete(config: dict) -> dict:
    """
    Complete trail creation flow.
    
    Args:
        config: Dict with trail parameters
    
    Returns:
        dict: Trail details with status
    """
    # Create trail
    trail = create_trail(
        name=config['name'],
        s3_bucket_name=config['s3_bucket'],
        s3_key_prefix=config.get('s3_prefix'),
        is_multi_region=config.get('is_multi_region', False),
        enable_log_validation=config.get('enable_validation', True),
        kms_key_id=config.get('kms_key_id'),
        is_organization_trail=config.get('is_org_trail', False)
    )
    
    # Start logging
    start_logging(config['name'])
    
    # Get final status
    status = get_trail_status(config['name'])
    
    return {
        'name': trail['Name'],
        'arn': trail['TrailARN'],
        's3_bucket': trail['S3BucketName'],
        'is_logging': status['IsLogging'],
        'home_region': trail['HomeRegion']
    }
```

### Query User Activity
```python
def query_user_activity(
    username: str,
    start_time: datetime = None,
    end_time: datetime = None
) -> list:
    """
    Query all activity by a specific user.
    
    Args:
        username: IAM username
        start_time: Start time
        end_time: End time
    
    Returns:
        list: User events
    """
    if not end_time:
        end_time = datetime.utcnow()
    if not start_time:
        start_time = end_time - timedelta(days=7)
    
    events = lookup_events_all(
        lookup_attributes=[
            {'AttributeKey': 'Username', 'AttributeValue': username}
        ],
        start_time=start_time,
        end_time=end_time
    )
    
    return [
        {
            'event_id': e['EventId'],
            'event_time': e['EventTime'],
            'event_name': e['EventName'],
            'event_source': e['EventSource'],
            'username': e['Username'],
            'source_ip': e.get('SourceIPAddress'),
            'request_params': e.get('RequestParameters'),
            'response': e.get('ResponseElements')
        }
        for e in events
    ]
```

## Error Handling

```python
def handle_cloudtrail_error(error: ClientError):
    """
    Handle CloudTrail errors with recovery guidance.
    
    Args:
        error: ClientError from boto3
    
    Raises:
        Exception with recovery guidance
    """
    error_code = error.response['Error']['Code']
    error_message = error.response['Error']['Message']
    
    recovery_map = {
        'TrailAlreadyExists': 'HALT - Trail exists. Use describe-trails.',
        'TrailNotFound': 'HALT - Trail not found. Check trail name.',
        'InsufficientS3BucketPolicy': 'FIX - Update S3 bucket policy for CloudTrail.',
        'S3BucketNotFound': 'FIX - Create S3 bucket first.',
        'InvalidCloudWatchLogsLogGroup': 'FIX - Verify CloudWatch Logs log group exists.',
        'KMSKeyNotFound': 'FIX - Verify KMS key exists.',
        'InvalidS3BucketName': 'FIX - Check S3 bucket name format.',
        'InvalidS3KeyPrefix': 'FIX - Check S3 key prefix format.',
        'InvalidTrailName': 'FIX - Trail name 3-128 chars, alphanumeric with dashes.',
        'OrganizationNotFound': 'FIX - Organization trail requires AWS Organization.',
        'NotOrganizationMasterAccount': 'FIX - Org trail must be created from management account.',
    }
    
    recovery = recovery_map.get(error_code, 'HALT - Check AWS documentation.')
    
    raise Exception(f"CloudTrail Error [{error_code}]: {error_message}\nRecovery: {recovery}")
```