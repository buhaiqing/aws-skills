# boto3 SDK Usage - CloudFront

Python boto3 patterns for CloudFront operations. Use region us-east-1.

## Client Initialization

```python
import boto3
from botocore.exceptions import ClientError

# CloudFront is global, always use us-east-1
cf = boto3.client('cloudfront', region_name='us-east-1')
```

## Distribution Operations

```python
def get_distribution_config(dist_id: str) -> tuple:
    """Get distribution config and ETag."""
    try:
        response = cf.get_distribution_config(Id=dist_id)
        return response['DistributionConfig'], response['ETag']
    except ClientError as e:
        handle_cf_error(e)

def create_s3_distribution(
    origin_id: str,
    s3_domain: str,
    comment: str = "CloudFront distribution",
    default_root: str = "index.html",
    price_class: str = "PriceClass_100"
) -> dict:
    """Create distribution with S3 origin."""
    try:
        config = {
            'Comment': comment,
            'PriceClass': price_class,
            'Enabled': True,
            'DefaultCacheBehavior': {
                'TargetOriginId': origin_id,
                'ViewerProtocolPolicy': 'redirect-to-https',
                'AllowedMethods': {
                    'Quantity': 2,
                    'Items': ['GET', 'HEAD']
                },
                'ForwardedValues': {
                    'QueryString': False,
                    'Cookies': {'Forward': 'none'}
                },
                'MinTTL': 0,
                'DefaultTTL': 86400,
                'MaxTTL': 31536000
            },
            'Origins': {
                'Quantity': 1,
                'Items': [{
                    'Id': origin_id,
                    'DomainName': s3_domain,
                    'S3OriginConfig': {'OriginAccessIdentity': ''}
                }]
            },
            'DefaultRootObject': default_root,
            'Origins': {'Quantity': 1, 'Items': [{'Id': origin_id, 'DomainName': s3_domain}]}
        }
        
        response = cf.create_distribution(DistributionConfig=config)
        return response['Distribution']
    except ClientError as e:
        handle_cf_error(e)

def create_custom_origin_distribution(
    origin_id: str,
    custom_origin_domain: str,
    comment: str = "CloudFront distribution",
    origin_protocol_policy: str = "https-only"
) -> dict:
    """Create distribution with custom origin (ELB, etc)."""
    try:
        config = {
            'Comment': comment,
            'Enabled': True,
            'DefaultCacheBehavior': {
                'TargetOriginId': origin_id,
                'ViewerProtocolPolicy': 'redirect-to-https',
                'AllowedMethods': {
                    'Quantity': 2,
                    'Items': ['GET', 'HEAD']
                },
                'ForwardedValues': {
                    'QueryString': False,
                    'Cookies': {'Forward': 'none'}
                }
            },
            'Origins': {
                'Quantity': 1,
                'Items': [{
                    'Id': origin_id,
                    'DomainName': custom_origin_domain,
                    'CustomOriginConfig': {
                        'HTTPPort': 80,
                        'HTTPSPort': 443,
                        'OriginProtocolPolicy': origin_protocol_policy,
                        'OriginSslProtocols': {'Quantity': 1, 'Items': ['TLSv1.2']}
                    }
                }]
            }
        }
        
        response = cf.create_distribution(DistributionConfig=config)
        return response['Distribution']
    except ClientError as e:
        handle_cf_error(e)

def update_distribution(dist_id: str, config: dict) -> dict:
    """Update distribution configuration."""
    try:
        _, etag = get_distribution_config(dist_id)
        
        response = cf.update_distribution(
            Id=dist_id,
            IfMatch=etag,
            DistributionConfig=config
        )
        return response['Distribution']
    except ClientError as e:
        handle_cf_error(e)

def delete_distribution(dist_id: str):
    """Delete a distribution (must be disabled first)."""
    try:
        _, etag = get_distribution_config(dist_id)
        cf.delete_distribution(Id=dist_id, IfMatch=etag)
    except ClientError as e:
        handle_cf_error(e)

def disable_distribution(dist_id: str) -> dict:
    """Disable a distribution."""
    try:
        config, etag = get_distribution_config(dist_id)
        config['Enabled'] = False
        
        response = cf.update_distribution(
            Id=dist_id,
            IfMatch=etag,
            DistributionConfig=config
        )
        return response['Distribution']
    except ClientError as e:
        handle_cf_error(e)
```

## Invalidations

```python
def create_invalidation(dist_id: str, paths: list, caller_ref: str = None) -> str:
    """Create cache invalidation."""
    try:
        import uuid
        ref = caller_ref or str(uuid.uuid4())
        
        response = cf.create_invalidation(
            DistributionId=dist_id,
            InvalidationBatch={
                'Paths': {
                    'Quantity': len(paths),
                    'Items': paths
                },
                'CallerReference': ref
            }
        )
        return response['Invalidation']['Id']
    except ClientError as e:
        handle_cf_error(e)

def get_invalidation_status(dist_id: str, inv_id: str) -> str:
    """Get invalidation status."""
    try:
        response = cf.get_invalidation(
            DistributionId=dist_id,
            Id=inv_id
        )
        return response['Invalidation']['Status']
    except ClientError as e:
        handle_cf_error(e)
```

## Origin Access Identity

```python
def create_oai(comment: str, caller_ref: str = None) -> dict:
    """Create Origin Access Identity."""
    try:
        import uuid
        ref = caller_ref or str(uuid.uuid4())
        
        response = cf.create_cloud_front_origin_access_identity(
            CloudFrontOriginAccessIdentityConfig={
                'CallerReference': ref,
                'Comment': comment
            }
        )
        return response['CloudFrontOriginAccessIdentity']
    except ClientError as e:
        handle_cf_error(e)
```

## Error Handling

```python
def handle_cf_error(error: ClientError):
    """Handle CloudFront errors."""
    error_code = error.response['Error']['Code']
    error_message = error.response['Error']['Message']
    
    recovery_map = {
        'NoSuchDistribution': 'HALT - Distribution not found.',
        'DistributionNotDisabled': 'FIX - Disable distribution before deletion.',
        'PreconditionFailed': 'FIX - ETag mismatch, get new config.',
        'InvalidIfMatchVersion': 'FIX - Invalid ETag version.',
        'TooManyDistributions': 'HALT - Exceeded distribution limit.',
        'IllegalUpdate': 'FIX - Invalid update operation.',
        'CNAMEAlreadyExists': 'FIX - CNAME already in use.'
    }
    
    recovery = recovery_map.get(error_code, 'HALT - Check AWS docs.')
    raise Exception(f"CloudFront Error [{error_code}]: {error_message}\nRecovery: {recovery}")
```