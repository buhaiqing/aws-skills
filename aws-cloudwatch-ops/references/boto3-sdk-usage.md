# boto3 SDK Usage — CloudWatch

## Client Initialization

```python
import boto3
import os

client = boto3.client(
    'cloudwatch',
    region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
)
```

## Operation Patterns

### Put Metric Alarm

```python
response = client.put_metric_alarm(
    AlarmName='HighCPU',
    MetricName='CPUUtilization',
    Namespace='AWS/EC2',
    Statistic='Average',
    Period=60,
    Threshold=80,
    ComparisonOperator='GreaterThanThreshold',
    EvaluationPeriods=3,
    AlarmActions=['arn:aws:sns:us-east-1:123456789:my-topic']
)
print(f"Alarm created: HighCPU")
```

### Put Alarm with Dimensions

```python
response = client.put_metric_alarm(
    AlarmName='InstanceHighCPU',
    MetricName='CPUUtilization',
    Namespace='AWS/EC2',
    Dimensions=[
        {'Name': 'InstanceId', 'Value': 'i-1234567890abcdef0'}
    ],
    Statistic='Average',
    Period=300,
    Threshold=90,
    ComparisonOperator='GreaterThanThreshold',
    EvaluationPeriods=2,
    DatapointsToAlarm=2  # Minimum breaches to alarm
)
```

### Describe Alarms

```python
# All alarms
response = client.describe_alarms()
for alarm in response['MetricAlarms']:
    print(f"{alarm['AlarmName']} - {alarm['StateValue']}")

# Specific alarm
response = client.describe_alarms(AlarmNames=['HighCPU'])
if response['MetricAlarms']:
    alarm = response['MetricAlarms'][0]
    print(f"State: {alarm['StateValue']}")
    print(f"Threshold: {alarm['Threshold']}")

# By state
response = client.describe_alarms(StateValue='ALARM')
```

### Delete Alarms

```bash
response = client.delete_alarms(AlarmNames=['HighCPU'])
```

### List Metrics

```python
# All metrics
response = client.list_metrics()
for m in response['Metrics']:
    print(f"{m['Namespace']}/{m['MetricName']}")

# By namespace
response = client.list_metrics(Namespace='AWS/EC2')

# By metric name
response = client.list_metrics(
    Namespace='AWS/EC2',
    MetricName='CPUUtilization'
)

# With dimensions
response = client.list_metrics(
    Namespace='AWS/EC2',
    MetricName='CPUUtilization',
    Dimensions=[{'Name': 'InstanceId', 'Value': 'i-xxx'}]
)

# Pagination
paginator = client.get_paginator('list_metrics')
for page in paginator.paginate(Namespace='AWS/EC2'):
    for m in page['Metrics']:
        print(m['MetricName'])
```

### Get Metric Statistics

```python
from datetime import datetime, timedelta

response = client.get_metric_statistics(
    Namespace='AWS/EC2',
    MetricName='CPUUtilization',
    Dimensions=[{'Name': 'InstanceId', 'Value': 'i-1234567890abcdef0'}],
    Statistics=['Average', 'Maximum'],
    Period=300,
    StartTime=datetime.utcnow() - timedelta(hours=1),
    EndTime=datetime.utcnow()
)

for datapoint in response['Datapoints']:
    print(f"{datapoint['Timestamp']}: Avg={datapoint['Average']}, Max={datapoint['Maximum']}")
```

### Get Metric Data (Advanced)

```python
response = client.get_metric_data(
    MetricDataQueries=[
        {
            'Id': 'cpu',
            'MetricStat': {
                'Metric': {
                    'Namespace': 'AWS/EC2',
                    'MetricName': 'CPUUtilization'
                },
                'Stat': 'Average',
                'Period': 300
            }
        },
        {
            'Id': 'mem',
            'MetricStat': {
                'Metric': {
                    'Namespace': 'AWS/EC2',
                    'MetricName': 'MemoryUtilization'
                },
                'Stat': 'Average',
                'Period': 300
            }
        }
    ],
    StartTime=datetime.utcnow() - timedelta(hours=1),
    EndTime=datetime.utcnow()
)

for result in response['MetricDataResults']:
    print(f"{result['Id']}: {result['Values']}")
```

### Put Custom Metric Data

```python
response = client.put_metric_data(
    Namespace='MyApplication',
    MetricData=[
        {
            'MetricName': 'RequestCount',
            'Value': 100,
            'Unit': 'Count',
            'Dimensions': [
                {'Name': 'Service', 'Value': 'API'},
                {'Name': 'Method', 'Value': 'GET'}
            ]
        }
    ]
)
```

### Put Dashboard

```python
dashboard_body = {
    "widgets": [
        {
            "type": "metric",
            "properties": {
                "metrics": [["AWS/EC2", "CPUUtilization"]],
                "period": 300,
                "stat": "Average"
            }
        }
    ]
}

response = client.put_dashboard(
    DashboardName='MyDashboard',
    DashboardBody=json.dumps(dashboard_body)
)
```

## Error Handling

```python
from botocore.exceptions import ClientError

try:
    response = client.put_metric_alarm(**params)
except ClientError as e:
    code = e.response['Error']['Code']
    
    if code == 'InvalidParameterValue':
        print("Invalid threshold or comparison operator")
    elif code == 'ResourceNotFound':
        print("Metric or namespace not found")
    elif code == 'LimitExceeded':
        print("Too many alarms")
    else:
        raise
```

## Common Error Codes

| Error Code | HTTP | Action |
|------------|------|--------|
| InvalidParameterValue | 400 | Fix threshold/operator |
| ResourceNotFound | 404 | Verify metric exists |
| LimitExceeded | 403 | Delete unused alarms |
| ThrottlingException | 429 | Backoff and retry |
| InternalError | 500 | Retry 3x; then HALT |

## Comparison Operators

```python
operators = [
    'GreaterThanThreshold',
    'GreaterThanOrEqualToThreshold',
    'LessThanThreshold',
    'LessThanOrEqualToThreshold',
    'LessThanLowerOrGreaterThanUpperThreshold',  # Anomaly detection
    'LessThanLowerThreshold',
    'GreaterThanUpperThreshold'
]
```

## Unit Types

```python
units = [
    'Seconds', 'Microseconds', 'Milliseconds',
    'Bytes', 'Kilobytes', 'Megabytes', 'Gigabytes', 'Terabytes',
    'Bits', 'Kilobits', 'Megabits', 'Gigabits', 'Terabits',
    'Percent', 'Count', 'Count/Second',
    'None'  # Default
]
```