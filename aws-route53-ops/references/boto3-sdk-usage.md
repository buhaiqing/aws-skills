# boto3 SDK Usage - Route53

Python boto3 patterns for Route53 operations.

## Client Initialization

```python
import boto3
from botocore.exceptions import ClientError

route53 = boto3.client('route53', region_name='{{env.AWS_DEFAULT_REGION}}')
```

## Hosted Zone Operations

```python
def create_hosted_zone(name: str, caller_reference: str, vpc_id: str = None, comment: str = None):
    """Create a hosted zone."""
    try:
        params = {
            'Name': name,
            'CallerReference': caller_reference
        }
        if vpc_id:
            params['VPC'] = {'VPCRegion': '{{env.AWS_DEFAULT_REGION}}', 'VPCId': vpc_id}
            params['HostedZoneConfig'] = {'Comment': comment or '', 'PrivateZone': True}
        
        response = route53.create_hosted_zone(**params)
        return response['HostedZone']
    except ClientError as e:
        handle_route53_error(e)

def get_hosted_zone(zone_id: str) -> dict:
    """Get hosted zone details."""
    try:
        response = route53.get_hosted_zone(Id=zone_id)
        return response['HostedZone']
    except ClientError as e:
        handle_route53_error(e)

def list_hosted_zones() -> list:
    """List all hosted zones."""
    try:
        response = route53.list_hosted_zones()
        return response['HostedZones']
    except ClientError as e:
        handle_route53_error(e)

def delete_hosted_zone(zone_id: str):
    """Delete a hosted zone."""
    try:
        route53.delete_hosted_zone(Id=zone_id)
    except ClientError as e:
        handle_route53_error(e)
```

## Record Set Operations

```python
def change_resource_record_sets(zone_id: str, changes: list) -> dict:
    """
    Change resource record sets.
    
    Args:
        zone_id: Hosted zone ID
        changes: List of change dicts with Action and ResourceRecordSet
    """
    try:
        response = route53.change_resource_record_sets(
            HostedZoneId=zone_id,
            ChangeBatch={'Changes': changes}
        )
        return response['ChangeInfo']
    except ClientError as e:
        handle_route53_error(e)

def upsert_record(zone_id: str, name: str, record_type: str, values: list, ttl: int = 300):
    """Create or update a record."""
    change = {
        'Action': 'UPSERT',
        'ResourceRecordSet': {
            'Name': name,
            'Type': record_type,
            'TTL': ttl,
            'ResourceRecords': [{'Value': v} for v in values]
        }
    }
    return change_resource_record_sets(zone_id, [change])

def delete_record(zone_id: str, name: str, record_type: str, values: list, ttl: int = 300):
    """Delete a record."""
    change = {
        'Action': 'DELETE',
        'ResourceRecordSet': {
            'Name': name,
            'Type': record_type,
            'TTL': ttl,
            'ResourceRecords': [{'Value': v} for v in values]
        }
    }
    return change_resource_record_sets(zone_id, [change])

def list_resource_record_sets(zone_id: str) -> list:
    """List all resource record sets in a zone."""
    try:
        response = route53.list_resource_record_sets(HostedZoneId=zone_id)
        return response['ResourceRecordSets']
    except ClientError as e:
        handle_route53_error(e)
```

## Health Check Operations

```python
def create_health_check(
    caller_reference: str,
    ip_address: str = None,
    port: int = 80,
    check_type: str = 'HTTP',
    resource_path: str = '/',
    fqdn: str = None
) -> dict:
    """Create a health check."""
    try:
        config = {
            'Type': check_type,
            'Port': port,
            'RequestInterval': 30,
            'FailureThreshold': 3
        }
        
        if ip_address:
            config['IPAddress'] = ip_address
        if fqdn:
            config['FullyQualifiedDomainName'] = fqdn
        if resource_path:
            config['ResourcePath'] = resource_path
        
        response = route53.create_health_check(
            CallerReference=caller_reference,
            HealthCheckConfig=config
        )
        return response['HealthCheck']
    except ClientError as e:
        handle_route53_error(e)

def get_health_check(health_check_id: str) -> dict:
    """Get health check details."""
    try:
        response = route53.get_health_check(HealthCheckId=health_check_id)
        return response['HealthCheck']
    except ClientError as e:
        handle_route53_error(e)

def update_health_check(health_check_id: str, **kwargs) -> dict:
    """Update health check configuration."""
    try:
        response = route53.update_health_check(
            HealthCheckId=health_check_id,
            **kwargs
        )
        return response['HealthCheck']
    except ClientError as e:
        handle_route53_error(e)

def delete_health_check(health_check_id: str):
    """Delete a health check."""
    try:
        route53.delete_health_check(HealthCheckId=health_check_id)
    except ClientError as e:
        handle_route53_error(e)
```

## Error Handling

```python
def handle_route53_error(error: ClientError):
    """Handle Route53 errors with recovery guidance."""
    error_code = error.response['Error']['Code']
    error_message = error.response['Error']['Message']
    
    recovery_map = {
        'NoSuchHostedZone': 'HALT - Hosted zone does not exist.',
        'NoSuchHealthCheck': 'HALT - Health check does not exist.',
        'InvalidChangeBatch': 'FIX - Check record set syntax and values.',
        'PriorRequestNotComplete': 'RETRY - Wait for previous change to complete.',
        'HealthCheckAlreadyExists': 'HALT - Health check with this caller reference already exists.',
        'HostedZoneAlreadyExists': 'HALT - Zone with this name already exists.',
    }
    
    recovery = recovery_map.get(error_code, 'HALT - Check AWS documentation.')
    raise Exception(f"Route53 Error [{error_code}]: {error_message}\nRecovery: {recovery}")
```

## Complete Workflow Example

```python
def create_alias_record(zone_id: str, name: str, target: str, hosted_zone_id: str) -> dict:
    """
    Create an alias record for AWS resources.
    
    Args:
        zone_id: Hosted zone ID
        name: Record name
        target: Target resource (e.g., ALB DNS name)
        hosted_zone_id: Target hosted zone ID
    """
    change = {
        'Action': 'UPSERT',
        'ResourceRecordSet': {
            'Name': name,
            'Type': 'A',
            'AliasTarget': {
                'HostedZoneId': hosted_zone_id,
                'DNSName': target,
                'EvaluateTargetHealth': True
            }
        }
    }
    return change_resource_record_sets(zone_id, [change])
```