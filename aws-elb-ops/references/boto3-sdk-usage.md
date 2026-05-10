# boto3 SDK Usage — ELB

## Client Initialization

```python
import boto3

# elbv2 for ALB/NLB
client = boto3.client('elbv2', region_name='us-east-1')

# elb for Classic Load Balancer (legacy)
clb_client = boto3.client('elb', region_name='us-east-1')
```

## Operation Patterns

### Create Application Load Balancer

```python
response = client.create_load_balancer(
    Name='my-alb',
    Type='application',
    Subnets=['subnet-aaa', 'subnet-bbb'],
    SecurityGroups=['sg-xxx'],
    Tags=[
        {'Key': 'Environment', 'Value': 'production'}
    ]
)

lb_arn = response['LoadBalancers'][0]['LoadBalancerArn']
lb_dns_name = response['LoadBalancers'][0]['DNSName']
print(f"ALB ARN: {lb_arn}")
print(f"DNS Name: {lb_dns_name}")
```

### Create Network Load Balancer

```python
response = client.create_load_balancer(
    Name='my-nlb',
    Type='network',
    Subnets=['subnet-aaa', 'subnet-bbb'],
    # NLB does not use security groups
)

lb_arn = response['LoadBalancers'][0]['LoadBalancerArn']
print(f"NLB ARN: {lb_arn}")
```

### Create Target Group

```python
response = client.create_target_group(
    Name='my-targets',
    Protocol='HTTP',
    Port=80,
    VpcId='vpc-xxx',
    HealthCheckPath='/health',
    HealthCheckIntervalSeconds=30,
    HealthCheckTimeoutSeconds=5,
    HealthyThresholdCount=5,
    UnhealthyThresholdCount=2,
    Matcher={'HttpCode': '200'}
)

tg_arn = response['TargetGroups'][0]['TargetGroupArn']
print(f"Target Group ARN: {tg_arn}")
```

### Create Target Group (IP targets for NLB)

```python
response = client.create_target_group(
    Name='my-ip-targets',
    Protocol='TCP',
    Port=8080,
    VpcId='vpc-xxx',
    TargetType='ip'  # Use IP addresses instead of instance IDs
)
```

### Register Targets (EC2 Instances)

```python
response = client.register_targets(
    TargetGroupArn='arn:aws:elasticloadbalancing:region:account:targetgroup/my-targets/xxx',
    Targets=[
        {'Id': 'i-aaa'},
        {'Id': 'i-bbb'},
        {'Id': 'i-ccc', 'Port': 8080}  # Optional override port
    ]
)
print("Targets registered")
```

### Register Targets (IP addresses)

```python
response = client.register_targets(
    TargetGroupArn='arn:aws:elasticloadbalancing:region:account:targetgroup/my-ip-targets/xxx',
    Targets=[
        {'Id': '10.0.1.10'},
        {'Id': '10.0.2.20', 'Port': 8080}
    ]
)
```

### Register Targets (Lambda function)

```python
response = client.register_targets(
    TargetGroupArn='arn:aws:elasticloadbalancing:region:account:targetgroup/my-lambda-tg/xxx',
    Targets=[
        {'Id': 'arn:aws:lambda:region:account:function:my-function'}
    ]
)
```

### Describe Target Health

```python
response = client.describe_target_health(
    TargetGroupArn='arn:aws:elasticloadbalancing:region:account:targetgroup/my-targets/xxx'
)

for target in response['TargetHealthDescriptions']:
    target_id = target['Target']['Id']
    health_status = target['TargetHealth']['State']
    print(f"Target {target_id}: {health_status}")
    # States: healthy, unhealthy, unused, draining, unavailable
```

### Create Listener

```python
response = client.create_listener(
    LoadBalancerArn='arn:aws:elasticloadbalancing:region:account:loadbalancer/app/my-alb/xxx',
    Protocol='HTTP',
    Port=80,
    DefaultActions=[
        {
            'Type': 'forward',
            'TargetGroupArn': 'arn:aws:elasticloadbalancing:region:account:targetgroup/my-targets/xxx'
        }
    ]
)

listener_arn = response['Listeners'][0]['ListenerArn']
print(f"Listener ARN: {listener_arn}")
```

### Create Listener (HTTPS)

```python
response = client.create_listener(
    LoadBalancerArn='arn:aws:elasticloadbalancing:region:account:loadbalancer/app/my-alb/xxx',
    Protocol='HTTPS',
    Port=443,
    Certificates=[
        {'CertificateArn': 'arn:aws:acm:region:account:certificate/xxx'}
    ],
    SslPolicy='ELBSecurityPolicy-2016-08',
    DefaultActions=[
        {
            'Type': 'forward',
            'TargetGroupArn': 'arn:aws:elasticloadbalancing:region:account:targetgroup/my-targets/xxx'
        }
    ]
)
```

### Create Listener Rule (Path-based routing)

```python
response = client.create_rule(
    ListenerArn='arn:aws:elasticloadbalancing:region:account:listener/app/my-alb/xxx/80',
    Conditions=[
        {
            'Field': 'path-pattern',
            'Values': ['/api/*']
        }
    ],
    Priority=1,
    Actions=[
        {
            'Type': 'forward',
            'TargetGroupArn': 'arn:aws:elasticloadbalancing:region:account:targetgroup/api-targets/xxx'
        }
    ]
)
```

### Describe Load Balancers

```python
response = client.describe_load_balancers()

for lb in response['LoadBalancers']:
    print(f"{lb['LoadBalancerName']}: {lb['State']['Code']}")
    print(f"  ARN: {lb['LoadBalancerArn']}")
    print(f"  Type: {lb['Type']}")
    print(f"  DNS: {lb['DNSName']}")

# Pagination
paginator = client.get_paginator('describe_load_balancers')
for page in paginator.paginate():
    for lb in page['LoadBalancers']:
        print(lb['LoadBalancerName'])
```

### Describe Load Balancer Attributes

```python
response = client.describe_load_balancer_attributes(
    LoadBalancerArn='arn:aws:elasticloadbalancing:region:account:loadbalancer/app/my-alb/xxx'
)

for attr in response['Attributes']:
    print(f"{attr['Key']}: {attr['Value']}")
```

### Modify Load Balancer Attributes

```python
response = client.modify_load_balancer_attributes(
    LoadBalancerArn='arn:aws:elasticloadbalancing:region:account:loadbalancer/app/my-alb/xxx',
    Attributes=[
        {'Key': 'deletion_protection.enabled', 'Value': 'true'},
        {'Key': 'idle_timeout.timeout_seconds', 'Value': '60'}
    ]
)
print("Attributes modified")
```

### Deregister Targets

```python
response = client.deregister_targets(
    TargetGroupArn='arn:aws:elasticloadbalancing:region:account:targetgroup/my-targets/xxx',
    Targets=[
        {'Id': 'i-aaa'},
        {'Id': 'i-bbb'}
    ]
)
print("Targets deregistered")
```

### Delete Listener

```python
response = client.delete_listener(
    ListenerArn='arn:aws:elasticloadbalancing:region:account:listener/app/my-alb/xxx/80'
)
print("Listener deleted")
```

### Delete Target Group

```python
# Must deregister all targets first
response = client.delete_target_group(
    TargetGroupArn='arn:aws:elasticloadbalancing:region:account:targetgroup/my-targets/xxx'
)
print("Target group deleted")
```

### Delete Load Balancer

```python
# Safety Gate: Confirm with user before deletion
# Must delete listeners first

response = client.delete_load_balancer(
    LoadBalancerArn='arn:aws:elasticloadbalancing:region:account:loadbalancer/app/my-alb/xxx'
)
print("Load balancer deleted")
```

### Classic Load Balancer Operations

```python
# Create CLB (legacy)
clb_client = boto3.client('elb')

response = clb_client.create_load_balancer(
    LoadBalancerName='my-clb',
    Listeners=[
        {
            'Protocol': 'HTTP',
            'LoadBalancerPort': 80,
            'InstanceProtocol': 'HTTP',
            'InstancePort': 80
        }
    ],
    Subnets=['subnet-aaa', 'subnet-bbb'],
    SecurityGroups=['sg-xxx']
)

# Configure health check
response = clb_client.configure_health_check(
    LoadBalancerName='my-clb',
    HealthCheck={
        'Target': 'HTTP:80/health',
        'Interval': 30,
        'Timeout': 5,
        'UnhealthyThreshold': 2,
        'HealthyThreshold': 10
    }
)

# Register instances
response = clb_client.register_instances_with_load_balancer(
    LoadBalancerName='my-clb',
    Instances=[
        {'InstanceId': 'i-aaa'},
        {'InstanceId': 'i-bbb'}
    ]
)

# Describe CLB
response = clb_client.describe_load_balancers(
    LoadBalancerNames=['my-clb']
)

# Delete CLB
response = clb_client.delete_load_balancer(
    LoadBalancerName='my-clb'
)
```

## Error Handling

```python
from botocore.exceptions import ClientError

try:
    response = client.create_load_balancer(
        Name='my-alb',
        Type='application',
        Subnets=['subnet-xxx']
    )
except ClientError as e:
    code = e.response['Error']['Code']
    
    if code == 'DuplicateLoadBalancerName':
        print("Load balancer name already exists")
    elif code == 'InvalidSubnet':
        print("Invalid subnet ID or subnet not in same VPC")
    elif code == 'QuotaExceeded':
        print("ELB quota reached")
    elif code == 'Throttling':
        # Retry with backoff
        pass
    else:
        raise
```

## Common Error Codes

| Error Code | HTTP | Action |
|------------|------|--------|
| DuplicateLoadBalancerName | 400 | HALT; use different name |
| InvalidSubnet | 400 | HALT; verify subnet IDs |
| InvalidSecurityGroup | 400 | HALT; verify SG IDs |
| InvalidVpcId | 400 | HALT; verify VPC ID |
| QuotaExceeded | 400 | HALT; request quota increase |
| ListenerNotFound | 404 | HALT; verify listener ARN |
| LoadBalancerNotFound | 404 | HALT; verify LB ARN |
| TargetGroupNotFound | 404 | HALT; verify TG ARN |
| ThrottlingException | 429 | Backoff; retry 3x |
| ResourceInUse | 409 | HALT; delete dependencies first |

## Waiters

ELB provides built-in waiters:

```python
# Wait for load balancer to be available
waiter = client.get_waiter('load_balancer_available')
waiter.wait(
    LoadBalancerArns=['arn:aws:elasticloadbalancing:region:account:loadbalancer/app/my-alb/xxx']
)

# Wait for load balancer to be deleted
waiter = client.get_waiter('load_balancer_deleted')
waiter.wait(
    LoadBalancerArns=['arn:aws:elasticloadbalancing:region:account:loadbalancer/app/my-alb/xxx']
)

# Wait for target in target group
waiter = client.get_waiter('target_in_service')
waiter.wait(
    TargetGroupArn='arn:aws:elasticloadbalancing:region:account:targetgroup/my-targets/xxx',
    Targets=[{'Id': 'i-xxx'}]
)
```

## Custom Polling for Target Health

```python
import time

def wait_for_targets_healthy(client, target_group_arn, target_ids, max_wait=300):
    """Wait for all targets to become healthy."""
    targets = [{'Id': tid} for tid in target_ids]
    
    for i in range(max_wait // 5):
        response = client.describe_target_health(
            TargetGroupArn=target_group_arn,
            Targets=targets
        )
        
        all_healthy = True
        for desc in response['TargetHealthDescriptions']:
            if desc['TargetHealth']['State'] != 'healthy':
                all_healthy = False
                print(f"Target {desc['Target']['Id']}: {desc['TargetHealth']['State']}")
        
        if all_healthy:
            print("All targets healthy")
            return True
        
        time.sleep(5)
    
    raise TimeoutError(f"Targets not healthy after {max_wait}s")
```

## Pagination Pattern

```python
paginator = client.get_paginator('describe_load_balancers')
for page in paginator.paginate():
    for lb in page['LoadBalancers']:
        print(f"{lb['LoadBalancerName']}: {lb['Type']}")
```

## Retry Strategy

```python
import time
from botocore.config import Config

config = Config(retries={'max_attempts': 3, 'mode': 'standard'})
client = boto3.client('elbv2', region_name='us-east-1', config=config)
```