# boto3 SDK Usage - KMS

Python boto3 patterns for KMS operations.

## Client Initialization

```python
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

# Standard client
kms = boto3.client('kms', region_name='{{env.AWS_DEFAULT_REGION}}')

# With retry configuration
config = Config(
    retries={
        'max_attempts': 10,
        'mode': 'adaptive'
    }
)
kms = boto3.client('kms', region_name='{{env.AWS_DEFAULT_REGION}}', config=config)
```

## Key Operations

### Create Key
```python
def create_key(
    description: str,
    key_usage: str = 'ENCRYPT_DECRYPT',
    key_spec: str = 'SYMMETRIC_DEFAULT',
    policy: str = None,
    tags: list = None,
    multi_region: bool = False
):
    """
    Create a KMS key.
    
    Args:
        description: Key description
        key_usage: 'ENCRYPT_DECRYPT' or 'SIGN_VERIFY'
        key_spec: 'SYMMETRIC_DEFAULT', 'RSA_2048', 'RSA_3072', 'RSA_4096', 'ECC_NIST_P256', etc.
        policy: Key policy JSON string
        tags: List of tag dicts [{'TagKey': 'key', 'TagValue': 'value'}]
        multi_region: Create multi-region key
    
    Returns:
        dict: Key metadata
    """
    try:
        params = {
            'Description': description,
            'KeyUsage': key_usage,
            'KeySpec': key_spec
        }
        
        if policy:
            params['Policy'] = policy
        
        if tags:
            params['Tags'] = tags
        
        if multi_region:
            params['MultiRegion'] = True
        
        response = kms.create_key(**params)
        return response['KeyMetadata']
    
    except ClientError as e:
        handle_kms_error(e)
```

### Describe Key
```python
def describe_key(key_id: str) -> dict:
    """
    Get key metadata.
    
    Args:
        key_id: Key ID, ARN, or alias
    
    Returns:
        dict: Key metadata
    """
    try:
        response = kms.describe_key(KeyId=key_id)
        return response['KeyMetadata']
    except ClientError as e:
        handle_kms_error(e)

def get_key_state(key_id: str) -> str:
    """Get key state (Enabled, Disabled, PendingDeletion, etc.)."""
    key = describe_key(key_id)
    return key['KeyState']

def is_key_enabled(key_id: str) -> bool:
    """Check if key is enabled."""
    key = describe_key(key_id)
    return key['Enabled']
```

### List Keys
```python
def list_keys(limit: int = None) -> list:
    """
    List all KMS keys.
    
    Args:
        limit: Max keys to return
    
    Returns:
        list: Key metadata list
    """
    try:
        params = {}
        if limit:
            params['Limit'] = limit
        
        response = kms.list_keys(**params)
        return response['Keys']
    except ClientError as e:
        handle_kms_error(e)

def list_keys_all() -> list:
    """List all keys with pagination."""
    keys = []
    marker = None
    
    while True:
        params = {'Limit': 100}
        if marker:
            params['Marker'] = marker
        
        response = kms.list_keys(**params)
        keys.extend(response['Keys'])
        
        marker = response.get('NextMarker')
        if not marker:
            break
    
    return keys
```

### Enable/Disable Key
```python
def enable_key(key_id: str):
    """Enable a KMS key."""
    try:
        kms.enable_key(KeyId=key_id)
    except ClientError as e:
        handle_kms_error(e)

def disable_key(key_id: str):
    """
    Disable a KMS key.
    
    WARNING: Affects all services using this key.
    """
    try:
        kms.disable_key(KeyId=key_id)
    except ClientError as e:
        handle_kms_error(e)
```

### Schedule Key Deletion
```python
def schedule_key_deletion(key_id: str, pending_window: int = 30) -> dict:
    """
    Schedule key for deletion.
    
    SAFETY: Key will be permanently deleted after pending window.
    All data encrypted with this key will be UNRECOVERABLE.
    
    Args:
        key_id: Key ID or ARN
        pending_window: Days before deletion (7-30)
    
    Returns:
        dict: Deletion schedule info
    """
    try:
        response = kms.schedule_key_deletion(
            KeyId=key_id,
            PendingWindowInDays=pending_window
        )
        return response
    except ClientError as e:
        handle_kms_error(e)

def cancel_key_deletion(key_id: str) -> dict:
    """Cancel scheduled key deletion."""
    try:
        response = kms.cancel_key_deletion(KeyId=key_id)
        return response
    except ClientError as e:
        handle_kms_error(e)
```

## Key Rotation

```python
def enable_key_rotation(key_id: str):
    """Enable automatic annual key rotation."""
    try:
        kms.enable_key_rotation(KeyId=key_id)
    except ClientError as e:
        handle_kms_error(e)

def disable_key_rotation(key_id: str):
    """Disable automatic key rotation."""
    try:
        kms.disable_key_rotation(KeyId=key_id)
    except ClientError as e:
        handle_kms_error(e)

def get_key_rotation_status(key_id: str) -> bool:
    """Check if key rotation is enabled."""
    try:
        response = kms.get_key_rotation_status(KeyId=key_id)
        return response['KeyRotationEnabled']
    except ClientError as e:
        handle_kms_error(e)
```

## Alias Operations

```python
def create_alias(alias_name: str, key_id: str):
    """
    Create alias for key.
    
    Args:
        alias_name: Alias name (e.g., 'alias/my-key')
        key_id: Target key ID
    """
    try:
        kms.create_alias(
            AliasName=alias_name,
            TargetKeyId=key_id
        )
    except ClientError as e:
        handle_kms_error(e)

def update_alias(alias_name: str, new_key_id: str):
    """Update alias to point to different key."""
    try:
        kms.update_alias(
            AliasName=alias_name,
            TargetKeyId=new_key_id
        )
    except ClientError as e:
        handle_kms_error(e)

def delete_alias(alias_name: str):
    """Delete alias (does not delete key)."""
    try:
        kms.delete_alias(AliasName=alias_name)
    except ClientError as e:
        handle_kms_error(e)

def list_aliases(key_id: str = None) -> list:
    """List aliases, optionally filtered by key."""
    try:
        params = {}
        if key_id:
            params['KeyId'] = key_id
        
        response = kms.list_aliases(**params)
        return response['Aliases']
    except ClientError as e:
        handle_kms_error(e)
```

## Key Policy Operations

```python
def get_key_policy(key_id: str) -> str:
    """
    Get key policy.
    
    Returns:
        str: Policy JSON string
    """
    try:
        response = kms.get_key_policy(
            KeyId=key_id,
            PolicyName='default'
        )
        return response['Policy']
    except ClientError as e:
        handle_kms_error(e)

def put_key_policy(key_id: str, policy: str):
    """
    Update key policy.
    
    Args:
        key_id: Key ID
        policy: Policy JSON string
    """
    try:
        kms.put_key_policy(
            KeyId=key_id,
            PolicyName='default',
            Policy=policy
        )
    except ClientError as e:
        handle_kms_error(e)
```

## Grant Operations

```python
def create_grant(
    key_id: str,
    grantee_principal: str,
    operations: list,
    constraints: dict = None,
    grant_name: str = None
):
    """
    Create grant for key access.
    
    Args:
        key_id: Key ID
        grantee_principal: Grantee IAM principal ARN
        operations: List of operations ['Encrypt', 'Decrypt', ...]
        constraints: Encryption context constraints
        grant_name: Human-readable name
    
    Returns:
        dict: Grant info
    """
    try:
        params = {
            'KeyId': key_id,
            'GranteePrincipal': grantee_principal,
            'Operations': operations
        }
        
        if constraints:
            params['Constraints'] = constraints
        
        if grant_name:
            params['Name'] = grant_name
        
        response = kms.create_grant(**params)
        return response
    except ClientError as e:
        handle_kms_error(e)

def list_grants(key_id: str) -> list:
    """List grants for a key."""
    try:
        response = kms.list_grants(KeyId=key_id)
        return response['Grants']
    except ClientError as e:
        handle_kms_error(e)

def retire_grant(key_id: str, grant_id: str = None, grant_token: str = None):
    """Retire grant."""
    try:
        params = {'KeyId': key_id}
        if grant_id:
            params['GrantId'] = grant_id
        if grant_token:
            params['GrantToken'] = grant_token
        
        kms.retire_grant(**params)
    except ClientError as e:
        handle_kms_error(e)

def revoke_grant(key_id: str, grant_id: str):
    """Revoke grant."""
    try:
        kms.revoke_grant(KeyId=key_id, GrantId=grant_id)
    except ClientError as e:
        handle_kms_error(e)
```

## Encrypt/Decrypt Operations

```python
def encrypt_data(key_id: str, plaintext: bytes, encryption_context: dict = None) -> bytes:
    """
    Encrypt data with KMS key.
    
    Args:
        key_id: Key ID
        plaintext: Data to encrypt (max 4096 bytes)
        encryption_context: Optional encryption context
    
    Returns:
        bytes: Encrypted ciphertext
    """
    try:
        params = {
            'KeyId': key_id,
            'Plaintext': plaintext
        }
        
        if encryption_context:
            params['EncryptionContext'] = encryption_context
        
        response = kms.encrypt(**params)
        return response['CiphertextBlob']
    except ClientError as e:
        handle_kms_error(e)

def decrypt_data(ciphertext: bytes, encryption_context: dict = None) -> bytes:
    """
    Decrypt data.
    
    Args:
        ciphertext: Encrypted data
        encryption_context: Must match encryption context used
    
    Returns:
        bytes: Decrypted plaintext
    """
    try:
        params = {'CiphertextBlob': ciphertext}
        
        if encryption_context:
            params['EncryptionContext'] = encryption_context
        
        response = kms.decrypt(**params)
        return response['Plaintext']
    except ClientError as e:
        handle_kms_error(e)

def re_encrypt(ciphertext: bytes, new_key_id: str) -> bytes:
    """
    Re-encrypt data with new key.
    
    Args:
        ciphertext: Existing ciphertext
        new_key_id: New encryption key
    
    Returns:
        bytes: New ciphertext
    """
    try:
        response = kms.re_encrypt(
            CiphertextBlob=ciphertext,
            DestinationKeyId=new_key_id
        )
        return response['CiphertextBlob']
    except ClientError as e:
        handle_kms_error(e)
```

## Data Key Operations

```python
def generate_data_key(key_id: str, key_spec: str = 'AES_256') -> dict:
    """
    Generate data key for envelope encryption.
    
    Args:
        key_id: KMS key ID
        key_spec: 'AES_128', 'AES_256', or use number_of_bytes
    
    Returns:
        dict: Contains Plaintext (clear key) and CiphertextBlob (encrypted key)
    
    SECURITY: Plaintext key should be used immediately and removed from memory
    """
    try:
        response = kms.generate_data_key(
            KeyId=key_id,
            KeySpec=key_spec
        )
        return response
    except ClientError as e:
        handle_kms_error(e)

def generate_data_key_without_plaintext(key_id: str, key_spec: str = 'AES_256') -> bytes:
    """
    Generate data key without returning plaintext.
    
    Use for external systems that will receive the key.
    
    Returns:
        bytes: Encrypted data key
    """
    try:
        response = kms.generate_data_key_without_plaintext(
            KeyId=key_id,
            KeySpec=key_spec
        )
        return response['CiphertextBlob']
    except ClientError as e:
        handle_kms_error(e)

def generate_random(number_of_bytes: int = 32) -> bytes:
    """Generate cryptographically secure random bytes."""
    try:
        response = kms.generate_random(NumberOfBytes=number_of_bytes)
        return response['Plaintext']
    except ClientError as e:
        handle_kms_error(e)
```

## Complete Flow Examples

### Envelope Encryption
```python
def envelope_encrypt(plaintext: bytes, kms_key_id: str) -> dict:
    """
    Encrypt large data using envelope encryption.
    
    Args:
        plaintext: Data to encrypt
        kms_key_id: KMS key ID
    
    Returns:
        dict: Contains encrypted_data and encrypted_key
    """
    import os
    from cryptography.fernet import Fernet
    
    # Generate data key
    data_key = generate_data_key(kms_key_id, 'AES_256')
    
    # Use data key for local encryption (using Fernet as example)
    # In production, use proper AES-GCM or ChaCha20-Poly1305
    f = Fernet(base64.urlsafe_b64encode(data_key['Plaintext']))
    encrypted_data = f.encrypt(plaintext)
    
    # Clear plaintext key from memory
    import ctypes
    ctypes.memset(id(data_key['Plaintext']), 0, len(data_key['Plaintext']))
    
    return {
        'encrypted_data': encrypted_data,
        'encrypted_key': data_key['CiphertextBlob']
    }

def envelope_decrypt(encrypted_data: bytes, encrypted_key: bytes, kms_key_id: str) -> bytes:
    """Decrypt data using envelope encryption."""
    from cryptography.fernet import Fernet
    
    # Decrypt data key
    data_key = decrypt_data(encrypted_key)
    
    # Decrypt data locally
    f = Fernet(base64.urlsafe_b64encode(data_key))
    plaintext = f.decrypt(encrypted_data)
    
    return plaintext
```

### Key Creation Complete Flow
```python
def create_key_complete(config: dict) -> dict:
    """
    Complete key creation with alias and policy.
    
    Args:
        config: Dict with key parameters
    
    Returns:
        dict: Key details
    """
    # Create key
    key = create_key(
        description=config['description'],
        key_usage=config.get('key_usage', 'ENCRYPT_DECRYPT'),
        key_spec=config.get('key_spec', 'SYMMETRIC_DEFAULT'),
        policy=config.get('policy'),
        tags=config.get('tags', []),
        multi_region=config.get('multi_region', False)
    )
    
    # Create alias if specified
    if config.get('alias'):
        create_alias(f"alias/{config['alias']}", key['KeyId'])
    
    # Enable rotation if specified
    if config.get('enable_rotation', False):
        enable_key_rotation(key['KeyId'])
    
    return {
        'key_id': key['KeyId'],
        'key_arn': key['Arn'],
        'alias': config.get('alias'),
        'state': key['KeyState'],
        'enabled': key['Enabled']
    }
```

## Error Handling

```python
def handle_kms_error(error: ClientError):
    """
    Handle KMS errors with recovery guidance.
    
    Args:
        error: ClientError from boto3
    
    Raises:
        Exception with recovery guidance
    """
    error_code = error.response['Error']['Code']
    error_message = error.response['Error']['Message']
    
    recovery_map = {
        'AlreadyExistsException': 'HALT - Key or alias already exists.',
        'NotFoundException': 'HALT - Key not found. Check ID/alias.',
        'DisabledException': 'FIX - Enable key with enable_key.',
        'InvalidKeyState': 'HALT - Key state incompatible. Check describe-key.',
        'InvalidKeyUsageException': 'FIX - Key not valid for operation. Check key usage.',
        'DependencyTimeoutException': 'RETRY - Service timeout, max 3 retries.',
        'KMSInvalidStateException': 'FIX - Fix key state before operation.',
        'LimitExceededException': 'HALT - Quota exceeded. Request increase.',
        'InvalidGrantIdException': 'HALT - Grant does not exist.',
        'InvalidGrantTokenException': 'HALT - Grant token invalid or expired.',
        'MalformedPolicyDocumentException': 'FIX - Key policy JSON invalid.',
        'TagException': 'FIX - Invalid tags. Check tag format.',
        'CloudHsmClusterInUseException': 'HALT - CloudHSM cluster in use.',
        'CloudHsmClusterNotActiveException': 'FIX - CloudHSM cluster not active.',
        'CustomKeyStoreHasCMKsException': 'HALT - Custom key store has keys.',
        'CustomKeyStoreInvalidStateException': 'FIX - Custom key store state invalid.',
        'CustomKeyStoreNotFoundException': 'HALT - Custom key store not found.',
    }
    
    recovery = recovery_map.get(error_code, 'HALT - Check AWS documentation.')
    
    raise Exception(f"KMS Error [{error_code}]: {error_message}\nRecovery: {recovery}")
```