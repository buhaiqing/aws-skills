# boto3 SDK Usage — Systems Manager (SSM)

## Client Initialization

```python
import boto3

ssm = boto3.client('ssm', region_name='us-east-1')
```

---

## send_command

Execute remote command on managed instances.

```python
response = ssm.send_command(
    InstanceIds=['i-1234567890abcdef0', 'i-0987654321fedcba0'],
    DocumentName='AWS-RunShellScript',
    Parameters={
        'commands': [
            'df -h',
            'uptime',
            'systemctl status nginx'
        ]
    },
    TimeoutSeconds=3600  # Max execution time
)

command_id = response['Command']['CommandId']
print(f"Command ID: {command_id}")
```

**Response Structure**:
```python
{
    'Command': {
        'CommandId': 'cmd-1234567890abcdef0',
        'DocumentName': 'AWS-RunShellScript',
        'InstanceIds': ['i-1234567890abcdef0'],
        'Status': 'Pending',
        'RequestedDateTime': datetime(2026, 5, 10, 12, 0, 0)
    }
}
```

---

## get_command_invocation

Get execution result for a specific instance.

```python
response = ssm.get_command_invocation(
    CommandId='cmd-1234567890abcdef0',
    InstanceId='i-1234567890abcdef0'
)

status = response['Status']
stdout = response['StandardOutputContent']
stderr = response['StandardErrorContent']
exit_code = response['ResponseCode']

print(f"Status: {status}")
print(f"Exit Code: {exit_code}")
print(f"STDOUT:\n{stdout}")
print(f"STDERR:\n{stderr}")
```

**Response Fields**:
| Field | Description |
|-------|-------------|
| `Status` | Success, Failed, TimedOut, Cancelled |
| `ResponseCode` | Exit code (0 = success) |
| `StandardOutputContent` | STDOUT text |
| `StandardErrorContent` | STDERR text |
| `ExecutionEndDate` | Completion timestamp |

---

## list_command_invocations

List all invocations for a command.

```python
response = ssm.list_command_invocations(
    CommandId='cmd-1234567890abcdef0',
    Details=True
)

for invocation in response['CommandInvocations']:
    print(f"Instance: {invocation['InstanceId']}")
    print(f"Status: {invocation['Status']}")
```

---

## describe_instance_information

List managed instances.

```python
response = ssm.describe_instance_information(
    Filters=[
        {'Key': 'InstanceIds', 'Values': ['i-1234567890abcdef0']}
    ]
)

for instance in response['InstanceInformationList']:
    print(f"ID: {instance['InstanceId']}")
    print(f"Status: {instance['PingStatus']}")  # Online/Offline
    print(f"Agent Version: {instance['AgentVersion']}")
```

---

## cancel_command

Cancel a running command.

```python
response = ssm.cancel_command(
    CommandId='cmd-1234567890abcdef0'
)
```

---

## start_session (Session Manager)

Start interactive session.

```python
response = ssm.start_session(
    Target='i-1234567890abcdef0',
    DocumentName='AWS-StartInteractiveSession'
)

session_id = response['SessionId']
url = response['Url']
```

---

## Polling Helper

Wait for command completion with polling.

```python
import time

def wait_for_command(ssm, command_id, instance_id, timeout=300, interval=5):
    """Poll until command reaches terminal state."""
    start = time.time()
    terminal_states = ['Success', 'Failed', 'Cancelled', 'TimedOut']
    
    while time.time() - start < timeout:
        response = ssm.get_command_invocation(
            CommandId=command_id,
            InstanceId=instance_id
        )
        status = response['Status']
        
        if status in terminal_states:
            return response
        
        print(f"Status: {status}... waiting")
        time.sleep(interval)
    
    raise TimeoutError(f"Command {command_id} did not complete in {timeout}s")

# Usage
result = wait_for_command(ssm, 'cmd-12345', 'i-12345')
print(f"Final status: {result['Status']}")
print(f"Output: {result['StandardOutputContent']}")
```

---

## Error Handling

```python
from botocore.exceptions import ClientError

try:
    response = ssm.send_command(
        InstanceIds=['i-invalid'],
        DocumentName='AWS-RunShellScript',
        Parameters={'commands': ['echo test']}
    )
except ClientError as e:
    error_code = e.response['Error']['Code']
    error_msg = e.response['Error']['Message']
    
    if error_code == 'InvalidInstanceId':
        print("Instance not managed by SSM or Agent not installed")
    elif error_code == 'DocumentNotFound':
        print("Invalid document name")
    elif error_code == 'ThrottlingException':
        print("Rate limited; implement backoff")
    elif error_code == 'InternalServerError':
        print("AWS service error; retry")
```

---

## Common Error Codes

| Error Code | HTTP | Recovery |
|------------|------|----------|
| `InvalidInstanceId` | 400 | Verify SSM Agent installed |
| `DocumentNotFound` | 400 | Check document name |
| `InvalidDocumentContent` | 400 | Fix document parameters |
| `ThrottlingException` | 429 | Exponential backoff (max 3) |
| `InternalServerError` | 500 | Retry 3x; HALT |
| `ServiceUnavailable` | 503 | Retry 3x; HALT |

---

## Exponential Backoff Pattern

```python
import time
import random

def send_command_with_retry(ssm, instance_ids, commands, max_retries=3):
    """Send command with exponential backoff for throttling."""
    for attempt in range(max_retries):
        try:
            return ssm.send_command(
                InstanceIds=instance_ids,
                DocumentName='AWS-RunShellScript',
                Parameters={'commands': commands}
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'ThrottlingException':
                wait = (2 ** attempt) + random.uniform(0, 1)
                print(f"Throttled; waiting {wait:.1f}s...")
                time.sleep(wait)
            else:
                raise
    
    raise RuntimeError(f"Failed after {max_retries} retries")
```

---

## SSM Documents Reference

| Document Name | Parameters |
|--------------|------------|
| `AWS-RunShellScript` | `commands` (list), `executionTimeout` (seconds) |
| `AWS-RunPowerShellScript` | `commands` (list), `executionTimeout` (seconds) |
| `AWS-UpdateSSMAgent` | `version` (optional) |
| `AWS-InstallApplication` | `application`, `source` |
| `AWS-ConfigurePackage` | `packageName`, `action`, `installationType` |