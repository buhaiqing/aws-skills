# boto3 SDK Usage — WAF

## Client Setup

```python
import boto3
client = boto3.client('wafv2', region_name='us-east-1')  # CLOUDFRONT scope
client = boto3.client('wafv2', region_name='us-west-2')  # REGIONAL scope
```

## Create Web ACL with AWS Managed Rules

```python
response = client.create_web_acl(
    Name='prod-web-acl',
    Scope='REGIONAL',
    DefaultAction={'Allow': {}},
    Rules=[
        {
            'Name': 'AWS-AWSManagedRulesCommonRuleSet',
            'Priority': 0,
            'Statement': {
                'ManagedRuleGroupStatement': {
                    'VendorName': 'AWS',
                    'Name': 'AWSManagedRulesCommonRuleSet'
                }
            },
            'OverrideAction': {'None': {}},
            'VisibilityConfig': {
                'SampledRequestsEnabled': True,
                'CloudWatchMetricsEnabled': True,
                'MetricName': 'CommonRuleSet'
            }
        },
        {
            'Name': 'RateLimit-2000',
            'Priority': 1,
            'Statement': {
                'RateBasedStatement': {
                    'Limit': 2000,
                    'AggregateKeyType': 'IP'
                }
            },
            'Action': {'Block': {}},
            'VisibilityConfig': {
                'SampledRequestsEnabled': True,
                'CloudWatchMetricsEnabled': True,
                'MetricName': 'RateLimit-2000'
            }
        }
    ],
    VisibilityConfig={
        'SampledRequestsEnabled': True,
        'CloudWatchMetricsEnabled': True,
        'MetricName': 'prod-web-acl'
    }
)
web_acl_arn = response['Summary']['ARN']
print(f"Created: {web_acl_arn}")
```

## Associate with ALB

```python
alb_arn = 'arn:aws:elasticloadbalancing:region:account:loadbalancer/app/my-alb/xxx'
client.associate_web_acl(
    WebACLArn=web_acl_arn,
    ResourceArn=alb_arn
)
print(f"Associated Web ACL with {alb_arn}")
```

## AIOps: Auto-Enable Rate Limiting (AH-08)

```python
from datetime import datetime, timedelta

def auto_enable_rate_limit(web_acl_name: str, scope: str, web_acl_id: str, lock_token: str,
                            rate_limit: int = 1000):
    """AH-08: Emergency rate limiting during traffic anomaly.
    Decision: [AUTO_HEAL]
    """
    client = boto3.client('wafv2')
    
    rate_rule = {
        'Name': 'EmergencyRateLimit',
        'Priority': 100,
        'Statement': {
            'RateBasedStatement': {
                'Limit': rate_limit,
                'AggregateKeyType': 'IP'
            }
        },
        'Action': {'Block': {}},
        'VisibilityConfig': {
            'SampledRequestsEnabled': True,
            'CloudWatchMetricsEnabled': True,
            'MetricName': 'EmergencyRateLimit'
        }
    }
    
    response = client.update_web_acl(
        Name=web_acl_name,
        Scope=scope,
        Id=web_acl_id,
        DefaultAction={'Allow': {}},
        Rules=[rate_rule],
        LockToken=lock_token,
        VisibilityConfig={
            'SampledRequestsEnabled': True,
            'CloudWatchMetricsEnabled': True,
            'MetricName': web_acl_name
        }
    )
    return response


def check_waf_effectiveness(web_acl_name: str):
    """Monitor WAF blocked requests over last 24h."""
    cw = boto3.client('cloudwatch')
    end = datetime.utcnow()
    start = end - timedelta(hours=24)
    
    response = cw.get_metric_statistics(
        Namespace='AWS/WAFV2',
        MetricName='BlockedRequests',
        Dimensions=[
            {'Name': 'WebACL', 'Value': web_acl_name},
            {'Name': 'Rule', 'Value': 'All'}
        ],
        StartTime=start,
        EndTime=end,
        Period=3600,
        Statistics=['Sum']
    )
    
    total_blocked = sum(dp['Sum'] for dp in response['Datapoints'])
    print(f"WAF blocked {total_blocked} requests in last 24h")
    return total_blocked
```

## Error Handling

```python
import botocore.exceptions

try:
    client.create_web_acl(...)
except botocore.exceptions.ClientError as e:
    code = e.response['Error']['Code']
    if code == 'WAFDuplicateItemException':
        print("Web ACL name already exists")
    elif code == 'WAFInvalidParameterException':
        print("Invalid parameter: check input values")
    elif code == 'WAFLimitsExceededException':
        print("WCU limit exceeded: simplify rules")
```

## Common Error Codes

| Error Code | Action |
|-----------|--------|
| WAFDuplicateItemException | HALT; use different name |
| WAFInvalidParameterException | Fix parameter; retry once |
| WAFLimitsExceededException | HALT; reduce WCU or request increase |
| WAFInternalErrorException | Retry 3x; HALT |
| WAFNonexistentItemException | HALT; verify ARN/ID |
| WAFAssociatedItemException | HALT; disassociate first |