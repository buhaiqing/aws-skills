# boto3 SDK Usage - Step Functions

Python boto3 patterns for AWS Step Functions operations.

## Client Initialization

```python
import boto3
from botocore.exceptions import ClientError

sfn = boto3.client('stepfunctions')
```

## State Machine Operations

```python
def create_state_machine(
    name: str,
    definition: str,
    role_arn: str,
    state_machine_type: str = 'STANDARD',
    logging_configuration: dict = None
) -> dict:
    """Create state machine."""
    try:
        params = {
            'name': name,
            'definition': definition,
            'roleArn': role_arn,
            'type': state_machine_type
        }
        if logging_configuration:
            params['loggingConfiguration'] = logging_configuration
        
        response = sfn.create_state_machine(**params)
        return response
    except ClientError as e:
        handle_sfn_error(e)

def describe_state_machine(arn: str) -> dict:
    """Describe state machine."""
    try:
        response = sfn.describe_state_machine(stateMachineArn=arn)
        return response
    except ClientError as e:
        handle_sfn_error(e)

def update_state_machine(arn: str, definition: str = None, role_arn: str = None) -> dict:
    """Update state machine."""
    try:
        params = {'stateMachineArn': arn}
        if definition:
            params['definition'] = definition
        if role_arn:
            params['roleArn'] = role_arn
        
        response = sfn.update_state_machine(**params)
        return response
    except ClientError as e:
        handle_sfn_error(e)

def delete_state_machine(arn: str):
    """Delete state machine."""
    try:
        sfn.delete_state_machine(stateMachineArn=arn)
    except ClientError as e:
        handle_sfn_error(e)

def list_state_machines() -> list:
    """List state machines."""
    try:
        response = sfn.list_state_machines()
        return response.get('stateMachines', [])
    except ClientError as e:
        handle_sfn_error(e)
```

## Execution Operations

```python
def start_execution(
    state_machine_arn: str,
    name: str = None,
    input_data: str = None
) -> dict:
    """Start state machine execution."""
    try:
        params = {'stateMachineArn': state_machine_arn}
        if name:
            params['name'] = name
        if input_data:
            params['input'] = input_data
        
        response = sfn.start_execution(**params)
        return response
    except ClientError as e:
        handle_sfn_error(e)

def stop_execution(execution_arn: str, cause: str = None) -> dict:
    """Stop execution."""
    try:
        params = {'executionArn': execution_arn}
        if cause:
            params['cause'] = cause
        
        return sfn.stop_execution(**params)
    except ClientError as e:
        handle_sfn_error(e)

def describe_execution(execution_arn: str) -> dict:
    """Describe execution."""
    try:
        return sfn.describe_execution(executionArn=execution_arn)
    except ClientError as e:
        handle_sfn_error(e)

def list_executions(state_machine_arn: str, max_results: int = 10, status_filter: str = None) -> list:
    """List executions."""
    try:
        params = {
            'stateMachineArn': state_machine_arn,
            'maxResults': max_results
        }
        if status_filter:
            params['statusFilter'] = status_filter
        
        response = sfn.list_executions(**params)
        return response.get('executions', [])
    except ClientError as e:
        handle_sfn_error(e)

def get_execution_history(execution_arn: str, max_results: int = 100) -> list:
    """Get execution history."""
    try:
        response = sfn.get_execution_history(
            executionArn=execution_arn,
            maxResults=max_results
        )
        return response.get('events', [])
    except ClientError as e:
        handle_sfn_error(e)
```

## Error Handling

```python
def handle_sfn_error(error: ClientError):
    """Handle Step Functions errors."""
    error_code = error.response['Error']['Code']
    error_message = error.response['Error']['Message']
    
    recovery_map = {
        'StateMachineDoesNotExist': 'HALT - State machine does not exist.',
        'ExecutionDoesNotExist': 'HALT - Execution does not exist.',
        'InvalidDefinition': 'FIX - Invalid ASL definition.',
        'StateMachineDeleting': 'HALT - State machine is being deleted.',
        'ExecutionAlreadyExists': 'HALT - Execution with same name exists.',
        'ExecutionLimitExceeded': 'HALT - Exceeded concurrent execution limit.',
        'MissingRequiredParameter': 'FIX - Missing required parameter.'
    }
    
    recovery = recovery_map.get(error_code, 'HALT - Check AWS docs.')
    raise Exception(f"StepFunctions Error [{error_code}]: {error_message}\nRecovery: {recovery}")
```