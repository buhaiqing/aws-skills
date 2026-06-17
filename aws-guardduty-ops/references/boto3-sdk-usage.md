# AWS GuardDuty Boto3 SDK Usage

## Common Patterns

### List Detectors
```python
import boto3
from botocore.exceptions import ClientError

def list_detectors(region: str) -> list:
    try:
        client = boto3.client('guardduty', region_name=region)
        response = client.list_detectors()
        return response.get('DetectorIds', [])
    except ClientError as e:
        raise RuntimeError(f"Failed to list detectors: {e}")
```

### Create Filter
```python
def create_filter(region: str, detector_id: str, filter_name: str, action: str, rank: int) -> dict:
    try:
        client = boto3.client('guardduty', region_name=region)
        response = client.create_filter(
            DetectorId=detector_id,
            Name=filter_name,
            Action=action,
            Rank=rank
        )
        return response
    except ClientError as e:
        raise RuntimeError(f"Failed to create filter: {e}")
```

### Delete Filter
```python
def delete_filter(region: str, detector_id: str, filter_name: str) -> None:
    try:
        client = boto3.client('guardduty', region_name=region)
        client.delete_filter(
            DetectorId=detector_id,
            FilterName=filter_name
        )
    except ClientError as e:
        raise RuntimeError(f"Failed to delete filter: {e}")
```

### List Filters
```python
def list_filters(region: str, detector_id: str) -> list:
    try:
        client = boto3.client('guardduty', region_name=region)
        response = client.list_filters(DetectorId=detector_id)
        return response.get('FilterNames', [])
    except ClientError as e:
        raise RuntimeError(f"Failed to list filters: {e}")
```

### Get Filter
```python
def get_filter(region: str, detector_id: str, filter_name: str) -> dict:
    try:
        client = boto3.client('guardduty', region_name=region)
        response = client.get_filter(
            DetectorId=detector_id,
            FilterName=filter_name
        )
        return response
    except ClientError as e:
        raise RuntimeError(f"Failed to get filter: {e}")
```

## Error Handling

Common exceptions:
- `ResourceNotFoundException` - Resource doesn't exist
- `AccessDeniedException` - Insufficient permissions
- `InvalidInputException` - Invalid input parameters
- `ThrottlingException` - Request throttled
- `InternalServerErrorException` - Internal AWS error