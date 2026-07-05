# DynamoDB Capacity/Throughput Errors — Detailed Recovery

## ProvisionedThroughputExceededException

### 1. Exponential Backoff

```python
import time, random
def retry_with_backoff(operation, max_retries=10):
    for attempt in range(max_retries):
        try:
            return operation()
        except ClientError as e:
            if e.response['Error']['Code'] == 'ProvisionedThroughputExceededException':
                delay = min(2 ** attempt * 0.1 + random.uniform(0, 0.1), 60)
                time.sleep(delay)
            else:
                raise
    raise Exception("Max retries exceeded")
```

### 2. Enable Auto-Scaling

```bash
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/{{table_name}} \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --min-capacity {{user.RCU}} \
  --max-capacity {{user.MaxRCU}}
```

### 3. Switch to On-Demand

```bash
aws dynamodb update-table \
  --table-name {{table_name}} \
  --billing-mode PAY_PER_REQUEST
```

### 4. Throttling Detection via CloudWatch

```python
from datetime import datetime, timedelta
cloudwatch = boto3.client('cloudwatch')
response = cloudwatch.get_metric_statistics(
    Namespace='AWS/DynamoDB',
    MetricName='ThrottledRequests',
    Dimensions=[
        {'Name': 'TableName', 'Value': table_name},
        {'Name': 'Operation', 'Value': 'GetItem'}
    ],
    StartTime=datetime.utcnow() - timedelta(minutes=5),
    EndTime=datetime.utcnow(),
    Period=60,
    Statistics=['Sum']
)
```

### 5. Backoff Handler Class

```python
class ThrottlingHandler:
    def __init__(self, max_retries: int = 10):
        self.max_retries = max_retries
    def execute(self, operation, *args, **kwargs):
        for attempt in range(self.max_retries):
            try:
                return operation(*args, **kwargs)
            except ClientError as e:
                if e.response['Error']['Code'] == 'ProvisionedThroughputExceededException':
                    delay = min(2 ** attempt * 0.1, 60) + random.uniform(0, 0.1)
                    time.sleep(delay)
                else:
                    raise
        raise Exception(f"Failed after {self.max_retries} retries")
```