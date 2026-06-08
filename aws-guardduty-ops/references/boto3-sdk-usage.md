# boto3 SDK Usage - GuardDuty

Python boto3 patterns for GuardDuty operations. All functions use `handle_gd_error(e)` for error handling.

## Client Initialization
```python
import boto3
from botocore.exceptions import ClientError
gd = boto3.client('guardduty', region_name='{{env.AWS_DEFAULT_REGION}}')
```

## Error Handling
```python
def handle_gd_error(error):
    code = error.response['Error']['Code']
    msg = error.response['Error']['Message']
    recovery_map = {
        'BadRequestException': 'HALT - fix params',
        'AccessDeniedException': 'HALT - check IAM permissions',
        'InternalServerErrorException': 'RETRY - 3x then HALT',
        'ResourceNotFoundException': 'HALT - verify detector/set ID',
    }
    recovery = recovery_map.get(code, 'HALT - check AWS docs')
    raise Exception(f"GuardDuty Error [{code}]: {msg}\nRecovery: {recovery}")
```

## Detector Operations

### Create / Get / Update / Delete
```python
def create_detector(enable=True, frequency='FIFTEEN_MINUTES'):
    try: return gd.create_detector(Enable=enable, FindingPublishingFrequency=frequency)['DetectorId']
    except ClientError as e: handle_gd_error(e)

def get_detector(detector_id):
    try: return gd.get_detector(DetectorId=detector_id)
    except ClientError as e: handle_gd_error(e)

def update_detector(detector_id, enable=True, frequency='ONE_HOUR'):
    try: return gd.update_detector(DetectorId=detector_id, Enable=enable, FindingPublishingFrequency=frequency)
    except ClientError as e: handle_gd_error(e)

def delete_detector(detector_id):
    try: return gd.delete_detector(DetectorId=detector_id)
    except ClientError as e: handle_gd_error(e)

def list_detectors():
    try: return gd.list_detectors()['DetectorIds']
    except ClientError as e: handle_gd_error(e)
```

## Finding Operations

### List / Get / Archive / Unarchive
```python
def list_findings(detector_id, criteria=None):
    params = {'DetectorId': detector_id}
    if criteria: params['FindingCriteria'] = criteria
    try: return gd.list_findings(**params)['FindingIds']
    except ClientError as e: handle_gd_error(e)

def get_findings(detector_id, finding_ids):
    try: return gd.get_findings(DetectorId=detector_id, FindingIds=finding_ids)['Findings']
    except ClientError as e: handle_gd_error(e)

def archive_findings(detector_id, finding_ids):
    try: return gd.archive_findings(DetectorId=detector_id, FindingIds=finding_ids)
    except ClientError as e: handle_gd_error(e)

def unarchive_findings(detector_id, finding_ids):
    try: return gd.unarchive_findings(DetectorId=detector_id, FindingIds=finding_ids)
    except ClientError as e: handle_gd_error(e)
```

## Filter Operations

### Create / Update / Delete / List
```python
def create_filter(detector_id, name, action, rank, criteria):
    try: return gd.create_filter(DetectorId=detector_id, Name=name, Action=action, Rank=rank, FindingCriteria=criteria)
    except ClientError as e: handle_gd_error(e)

def update_filter(detector_id, name, criteria):
    try: return gd.update_filter(DetectorId=detector_id, Name=name, FindingCriteria=criteria)
    except ClientError as e: handle_gd_error(e)

def delete_filter(detector_id, name):
    try: return gd.delete_filter(DetectorId=detector_id, Name=name)
    except ClientError as e: handle_gd_error(e)

def list_filters(detector_id):
    try: return gd.list_filters(DetectorId=detector_id)['FilterNames']
    except ClientError as e: handle_gd_error(e)

def get_filter(detector_id, name):
    try: return gd.get_filter(DetectorId=detector_id, Name=name)
    except ClientError as e: handle_gd_error(e)
```

## IP Set Operations

### Create / Update / Delete / List / Activate
```python
def create_ip_set(detector_id, name, fmt, location, activate=True):
    try: return gd.create_ip_set(DetectorId=detector_id, Name=name, Format=fmt, Location=location, Activate=activate)['IpSetId']
    except ClientError as e: handle_gd_error(e)

def update_ip_set(detector_id, ip_set_id, location=None, activate=None):
    params = {'DetectorId': detector_id, 'IpSetId': ip_set_id}
    if location: params['Location'] = location
    if activate is not None: params['Activate'] = activate
    try: return gd.update_ip_set(**params)
    except ClientError as e: handle_gd_error(e)

def delete_ip_set(detector_id, ip_set_id):
    try: return gd.delete_ip_set(DetectorId=detector_id, IpSetId=ip_set_id)
    except ClientError as e: handle_gd_error(e)

def list_ip_sets(detector_id):
    try: return gd.list_ip_sets(DetectorId=detector_id)['IpSetIds']
    except ClientError as e: handle_gd_error(e)

def get_ip_set(detector_id, ip_set_id):
    try: return gd.get_ip_set(DetectorId=detector_id, IpSetId=ip_set_id)
    except ClientError as e: handle_gd_error(e)
```

## Threat Intel Set Operations

### Create / Update / Delete / List / Activate
```python
def create_threat_intel_set(detector_id, name, fmt, location, activate=True):
    try: return gd.create_threat_intel_set(DetectorId=detector_id, Name=name, Format=fmt, Location=location, Activate=activate)['ThreatIntelSetId']
    except ClientError as e: handle_gd_error(e)

def update_threat_intel_set(detector_id, threat_intel_set_id, location=None, activate=None):
    params = {'DetectorId': detector_id, 'ThreatIntelSetId': threat_intel_set_id}
    if location: params['Location'] = location
    if activate is not None: params['Activate'] = activate
    try: return gd.update_threat_intel_set(**params)
    except ClientError as e: handle_gd_error(e)

def delete_threat_intel_set(detector_id, threat_intel_set_id):
    try: return gd.delete_threat_intel_set(DetectorId=detector_id, ThreatIntelSetId=threat_intel_set_id)
    except ClientError as e: handle_gd_error(e)

def list_threat_intel_sets(detector_id):
    try: return gd.list_threat_intel_sets(DetectorId=detector_id)['ThreatIntelSetIds']
    except ClientError as e: handle_gd_error(e)

def get_threat_intel_set(detector_id, threat_intel_set_id):
    try: return gd.get_threat_intel_set(DetectorId=detector_id, ThreatIntelSetId=threat_intel_set_id)
    except ClientError as e: handle_gd_error(e)
```

## Member Account Operations

### Invite / Accept / Disassociate / Delete
```python
def invite_members(detector_id, account_ids, message="Enable GuardDuty"):
    try: return gd.invite_members(DetectorId=detector_id, AccountIds=account_ids, Message=message)
    except ClientError as e: handle_gd_error(e)

def list_members(detector_id):
    try: return gd.list_members(DetectorId=detector_id)['Members']
    except ClientError as e: handle_gd_error(e)

def get_members(detector_id, account_ids):
    try: return gd.get_members(DetectorId=detector_id, AccountIds=account_ids)['Members']
    except ClientError as e: handle_gd_error(e)

def disassociate_members(detector_id, account_ids):
    try: return gd.disassociate_members(DetectorId=detector_id, AccountIds=account_ids)
    except ClientError as e: handle_gd_error(e)

def delete_members(detector_id, account_ids):
    try: return gd.delete_members(DetectorId=detector_id, AccountIds=account_ids)
    except ClientError as e: handle_gd_error(e)

def accept_invitation(detector_id, master_id, invitation_id):
    try: return gd.accept_invitation(DetectorId=detector_id, MasterId=master_id, InvitationId=invitation_id)
    except ClientError as e: handle_gd_error(e)
```

## Publishing Destination Operations

### Create / Describe / Update / Delete
```python
def create_publishing_destination(detector_id, dest_type, dest_props):
    try: return gd.create_publishing_destination(DetectorId=detector_id, DestinationType=dest_type, DestinationProperties=dest_props)['DestinationId']
    except ClientError as e: handle_gd_error(e)

def describe_publishing_destination(detector_id, destination_id):
    try: return gd.describe_publishing_destination(DetectorId=detector_id, DestinationId=destination_id)
    except ClientError as e: handle_gd_error(e)

def update_publishing_destination(detector_id, destination_id, dest_props):
    try: return gd.update_publishing_destination(DetectorId=detector_id, DestinationId=destination_id, DestinationProperties=dest_props)
    except ClientError as e: handle_gd_error(e)

def delete_publishing_destination(detector_id, destination_id):
    try: return gd.delete_publishing_destination(DetectorId=detector_id, DestinationId=destination_id)
    except ClientError as e: handle_gd_error(e)

def list_publishing_destinations(detector_id):
    try: return gd.list_publishing_destinations(DetectorId=detector_id)['Destinations']
    except ClientError as e: handle_gd_error(e)
```
