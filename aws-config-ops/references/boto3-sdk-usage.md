# boto3 SDK Usage — AWS Config

## Bootstrap

```python
import boto3
import os

client = boto3.client(
    'config',
    region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
)

# With SSO profile
# session = boto3.Session(profile_name=os.environ.get('AWS_PROFILE'))
# client = session.client('config', region_name='us-east-1')
```

## Common Patterns

### Full Setup
```python
# Create service-linked role
iam = boto3.client('iam')
try:
    iam.create_service_linked_role(AWSServiceName='config.amazonaws.com')
except iam.exceptions.InvalidInputException:
    pass  # Already exists

# Put configuration recorder
client.put_configuration_recorder(
    ConfigurationRecorder={
        'name': 'default',
        'roleARN': 'arn:aws:iam::123456789012:role/aws-service-role/config.amazonaws.com/AWSServiceRoleForConfig',
    },
    RecordingGroup={
        'allSupported': True,
        'includeGlobalResourceTypes': True,
    }
)

# Put delivery channel
client.put_delivery_channel(
    DeliveryChannel={
        'name': 'default',
        's3BucketName': 'my-config-bucket',
        's3KeyPrefix': 'config',
        'configSnapshotDeliveryProperties': {
            'deliveryFrequency': 'TwentyFourHours'
        }
    }
)

# Start recorder
client.start_configuration_recorder(
    ConfigurationRecorderName='default'
)

# Verify
status = client.describe_configuration_recorder_status(
    ConfigurationRecorderNames=['default']
)
print(status['ConfigurationRecordersStatus'][0]['recording'])
```

### Config Rules
```python
# Put managed rule
client.put_config_rule(
    ConfigRule={
        'ConfigRuleName': 's3-public-read-prohibited',
        'Source': {
            'Owner': 'AWS',
            'SourceIdentifier': 'S3_BUCKET_PUBLIC_READ_PROHIBITED'
        },
        'Scope': {
            'ComplianceResourceTypes': ['AWS::S3::Bucket']
        }
    }
)

# Describe all rules
paginator = client.get_paginator('describe_config_rules')
for page in paginator.paginate():
    for rule in page['ConfigRules']:
        print(rule['ConfigRuleName'], rule['ConfigRuleState'])

# Start evaluation
client.start_config_rules_evaluation(
    ConfigRuleNames=['s3-public-read-prohibited']
)

# Get compliance results
from botocore.exceptions import ClientError

try:
    response = client.get_compliance_details_by_config_rule(
        ConfigRuleName='s3-public-read-prohibited',
        ComplianceTypes=['NON_COMPLIANT']
    )
    for result in response['EvaluationResults']:
        print(result['ComplianceResourceId'], result['ComplianceType'])
except ClientError as e:
    print(f"Error: {e.response['Error']['Code']}")
```

### Custom Rule (with Lambda ARN)
```python
client.put_config_rule(
    ConfigRule={
        'ConfigRuleName': 'check-instance-type',
        'Source': {
            'Owner': 'CUSTOM_LAMBDA',
            'SourceIdentifier': 'arn:aws:lambda:us-east-1:123456789012:function:my-config-rule',
            'SourceDetails': [
                {
                    'EventSource': 'aws.config',
                    'MessageType': 'ConfigurationItemChangeNotification'
                }
            ]
        },
        'MaximumExecutionFrequency': 'TwentyFourHours'
    }
)
```

### Conformance Pack
```python
response = client.put_conformance_pack(
    ConformancePackName='my-pack',
    TemplateS3Uri='s3://my-bucket/config-templates/my-pack.yaml',
    ConformancePackInputParameters=[
        {'ParameterName': 'bucketName', 'ParameterValue': 'my-bucket'}
    ]
)
print(f"Pack ARN: {response['ConformancePackArn']}")
```

### Aggregator
```python
# Single account
client.put_configuration_aggregator(
    ConfigurationAggregatorName='my-aggregator',
    AccountAggregationSources=[{
        'AccountIds': ['123456789012', '234567890123'],
        'AllAwsRegions': True
    }]
)

# Organization
client.put_configuration_aggregator(
    ConfigurationAggregatorName='org-aggregator',
    OrganizationAggregationSource={
        'RoleArn': 'arn:aws:iam::123456789012:role/aws-service-role/config.amazonaws.com/AWSServiceRoleForConfig',
        'AllAwsRegions': True
    }
)
```

### Resource Queries
```python
# Select resources with SQL
response = client.select_resource_config(
    Expression="SELECT resourceId, resourceName, tags WHERE resourceType = 'AWS::EC2::Instance'",
    Limit=100
)
for result in response['Results']:
    import json
    resource = json.loads(result)
    print(resource['resourceId'], resource.get('resourceName'))

# List discovered resources
response = client.list_discovered_resources(
    resourceType='AWS::EC2::Instance',
    limit=100
)
for r in response['resourceIdentifiers']:
    print(r['resourceId'], r.get('resourceName'))
```

### Organization Config Rules
```python
client.put_organization_config_rule(
    OrganizationConfigRuleName='org-s3-public-read-prohibited',
    OrganizationManagedRuleMetadata={
        'RuleIdentifier': 'S3_BUCKET_PUBLIC_READ_PROHIBITED',
        'MaximumExecutionFrequency': 'TwentyFourHours'
    }
)
```

### Delete Operations
```python
# Delete rule (requires user confirmation in GCL)
client.delete_config_rule(ConfigRuleName='s3-public-read-prohibited')

# Stop + delete recorder
client.stop_configuration_recorder(ConfigurationRecorderName='default')
client.delete_configuration_recorder(ConfigurationRecorderName='default')

# Delete delivery channel
client.delete_delivery_channel(DeliveryChannelName='default')
```

## Error Handling

```python
from botocore.exceptions import ClientError, BotoCoreError

try:
    client.put_config_rule(ConfigRule=rule_config)
except ClientError as e:
    code = e.response['Error']['Code']
    if code == 'MaxNumberOfConfigRulesExceeded':
        raise RuntimeError(f"Config rule limit reached: {e.response['Error']['Message']}")
    elif code == 'InsufficientPermissionsException':
        raise RuntimeError(f"IAM permission insufficient for Config rule")
    elif code in ['ThrottlingException', 'InternalError']:
        # Retryable
        pass
    else:
        raise
except BotoCoreError as e:
    raise
```

## Retry Strategy

```python
from botocore.config import Config

config = Config(retries={'max_attempts': 3, 'mode': 'adaptive'})
client = boto3.client('config', config=config)
```