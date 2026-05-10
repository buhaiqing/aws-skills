# boto3 SDK Usage - Secrets Manager

Python boto3 patterns for Secrets Manager operations.

## Client Initialization

```python
import boto3
from botocore.exceptions import ClientError

sm = boto3.client('secretsmanager', region_name='{{env.AWS_DEFAULT_REGION}}')
```

## Secret Operations

```python
def create_secret(name: str, secret_string: str, description: str = None, kms_key_id: str = None):
    """Create a new secret."""
    try:
        params = {
            'Name': name,
            'SecretString': secret_string
        }
        if description:
            params['Description'] = description
        if kms_key_id:
            params['KmsKeyId'] = kms_key_id
        
        response = sm.create_secret(**params)
        return response
    except ClientError as e:
        handle_sm_error(e)

def get_secret_value(secret_id: str, version_id: str = None, version_stage: str = None) -> str:
    """Get secret value."""
    try:
        params = {'SecretId': secret_id}
        if version_id:
            params['VersionId'] = version_id
        if version_stage:
            params['VersionStage'] = version_stage
        
        response = sm.get_secret_value(**params)
        return response.get('SecretString') or response.get('SecretBinary')
    except ClientError as e:
        handle_sm_error(e)

def update_secret(secret_id: str, secret_string: str):
    """Update secret value."""
    try:
        response = sm.put_secret_value(
            SecretId=secret_id,
            SecretString=secret_string,
            VersionStages=['AWSCURRENT']
        )
        return response
    except ClientError as e:
        handle_sm_error(e)

def delete_secret(secret_id: str, recovery_window: int = 30, force: bool = False):
    """Delete a secret."""
    try:
        if force:
            response = sm.delete_secret(
                SecretId=secret_id,
                ForceDeleteWithoutRecovery=True
            )
        else:
            response = sm.delete_secret(
                SecretId=secret_id,
                RecoveryWindowInDays=recovery_window
            )
        return response
    except ClientError as e:
        handle_sm_error(e)

def restore_secret(secret_id: str):
    """Restore a deleted secret."""
    try:
        response = sm.restore_secret(SecretId=secret_id)
        return response
    except ClientError as e:
        handle_sm_error(e)
```

## Error Handling

```python
def handle_sm_error(error: ClientError):
    """Handle Secrets Manager errors."""
    error_code = error.response['Error']['Code']
    error_message = error.response['Error']['Message']
    
    recovery_map = {
        'ResourceNotFoundException': 'HALT - Secret not found.',
        'InvalidRequestException': 'FIX - Invalid request parameters.',
        'InvalidParameterException': 'FIX - Invalid parameter value.',
        'EncryptionFailure': 'FIX - Encryption failed, check KMS key.',
        'DecryptionFailure': 'FIX - Decryption failed, check KMS key.',
        'InternalServiceError': 'RETRY - Internal error, retry.',
    }
    
    recovery = recovery_map.get(error_code, 'HALT - Check AWS documentation.')
    raise Exception(f"Secrets Manager Error [{error_code}]: {error_message}\nRecovery: {recovery}")
```