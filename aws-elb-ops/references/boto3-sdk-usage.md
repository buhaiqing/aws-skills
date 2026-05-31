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

---

## AIOps: Health Diagnostics & Auto-Healing (boto3)

### Auto-Heal AH-01: Target Re-Registration

```python
import time
import boto3

client = boto3.client('elbv2')
cw = boto3.client('cloudwatch')

def auto_heal_target(tg_arn: str, target_id: str, port: int = 80, max_retry: int = 2):
    """AH-01: Deregister, wait, re-register, verify health.
    Decision: [AUTO_HEAL] — reversible, low risk.
    """
    for attempt in range(max_retry):
        print(f"Attempt {attempt + 1}: Re-registering {target_id}")
        
        # 1. Deregister
        client.deregister_targets(
            TargetGroupArn=tg_arn,
            Targets=[{'Id': target_id}]
        )
        print("Deregistered")
        
        # 2. Wait for completion
        for _ in range(12):  # max 60s
            try:
                resp = client.describe_target_health(
                    TargetGroupArn=tg_arn,
                    Targets=[{'Id': target_id}]
                )
                state = resp['TargetHealthDescriptions'][0]['TargetHealth']['State']
                if state == 'unused':
                    break
            except:
                break  # target removed from TG
            time.sleep(5)
        
        # 3. Wait 30s for stabilization
        time.sleep(30)
        
        # 4. Re-register
        client.register_targets(
            TargetGroupArn=tg_arn,
            Targets=[{'Id': target_id, 'Port': port}]
        )
        print("Re-registered")
        
        # 5. Verify healthy (max 180s)
        for _ in range(36):
            resp = client.describe_target_health(
                TargetGroupArn=tg_arn,
                Targets=[{'Id': target_id}]
            )
            state = resp['TargetHealthDescriptions'][0]['TargetHealth']['State']
            if state == 'healthy':
                print(f"Target healthy after re-registration")
                return True
            time.sleep(5)
        
        print(f"Attempt {attempt + 1} failed")
    
    print(f"Auto-heal failed after {max_retry} attempts. Downgrade to [MANUAL].")
    return False
```

### AH-03: Enable Cross-Zone Load Balancing

```python
def enable_cross_zone(lb_arn: str) -> bool:
    """AH-03: Auto-enable cross-zone load balancing.
    Decision: [AUTO_HEAL] — no data loss, reversible.
    """
    response = client.modify_load_balancer_attributes(
        LoadBalancerArn=lb_arn,
        Attributes=[
            {'Key': 'load_balancing.cross_zone.enabled', 'Value': 'true'}
        ]
    )
    
    # Verify
    attrs = client.describe_load_balancer_attributes(
        LoadBalancerArn=lb_arn
    )['Attributes']
    for attr in attrs:
        if attr['Key'] == 'load_balancing.cross_zone.enabled':
            return attr['Value'] == 'true'
    return False
```

### RC-01: 502 Error Diagnostics (Multi-Metric Correlation)

```python
from datetime import datetime, timedelta
from dateutil.parser import parse

def diagnose_502_errors(lb_arn: str, tg_arn: str, target_ids: list[str]):
    """RC-01: Cross-module 502 error RCA.
    Collects evidence from ELB metrics + EC2 status + CloudTrail.
    """
    end = datetime.utcnow()
    start = end - timedelta(hours=1)
    
    # 1. Check LB metrics
    metrics = cw.get_metric_statistics(
        Namespace='AWS/ApplicationELB',
        MetricName='HTTPCode_ELB_5XX',
        Dimensions=[{'Name': 'LoadBalancer', 'Value': lb_arn}],
        StartTime=start,
        EndTime=end,
        Period=300,
        Statistics=['Sum']
    )
    print(f"ELB 5XX count in last hour: {sum(dp['Sum'] for dp in metrics['Datapoints'])}")
    
    # 2. Check target health
    health = client.describe_target_health(
        TargetGroupArn=tg_arn
    )
    for desc in health['TargetHealthDescriptions']:
        target = desc['Target']['Id']
        state = desc['TargetHealth']['State']
        reason = desc['TargetHealth'].get('Description', '')
        print(f"Target {target}: {state} ({reason})")
    
    # 3. Check target EC2 CPU (cross-module)
    ec2 = boto3.client('ec2')
    for tid in target_ids:
        status = ec2.describe_instance_status(
            InstanceIds=[tid]
        )['InstanceStatuses']
        if status:
            s = status[0]
            print(f"EC2 {tid}: System={s['SystemStatus']['Status']}, "
                  f"Instance={s['InstanceStatus']['Status']}")
    
    # 4. Check CloudTrail for changes (cross-module)
    ct = boto3.client('cloudtrail')
    events = ct.lookup_events(
        LookupAttributes=[{
            'AttributeKey': 'ResourceType',
            'AttributeValue': 'AWS::ElasticLoadBalancing::LoadBalancer'
        }],
        StartTime=start,
        EndTime=end
    )
    for event in events.get('Events', []):
        print(f"Change detected: {event['EventName']} by {event['Username']} at {event['EventTime']}")
```

### Compliance Scan (AUTO_HEAL)

```python
def scan_and_fix_compliance(lb_arn: str) -> dict:
    """Run compliance scan, auto-fix where possible."""
    results = {}
    attrs = client.describe_load_balancer_attributes(
        LoadBalancerArn=lb_arn
    )['Attributes']
    
    attr_map = {a['Key']: a['Value'] for a in attrs}
    
    # Check deletion protection
    if attr_map.get('deletion_protection.enabled') != 'true':
        client.modify_load_balancer_attributes(
            LoadBalancerArn=lb_arn,
            Attributes=[{'Key': 'deletion_protection.enabled', 'Value': 'true'}]
        )
        results['deletion_protection'] = 'FIXED [AUTO_HEAL]'
    else:
        results['deletion_protection'] = 'PASS'
    
    # Check cross-zone
    if attr_map.get('load_balancing.cross_zone.enabled') != 'true':
        enable_cross_zone(lb_arn)
        results['cross_zone'] = 'FIXED [AUTO_HEAL]'
    else:
        results['cross_zone'] = 'PASS'
    
    # Check invalid header dropping (ALB only)
    if 'routing.http.drop_invalid_header_fields.enabled' in attr_map:
        if attr_map['routing.http.drop_invalid_header_fields.enabled'] != 'true':
            client.modify_load_balancer_attributes(
                LoadBalancerArn=lb_arn,
                Attributes=[{'Key': 'routing.http.drop_invalid_header_fields.enabled', 'Value': 'true'}]
            )
            results['invalid_header_drop'] = 'FIXED [AUTO_HEAL]'
        else:
            results['invalid_header_drop'] = 'PASS'
    
    return results
```

### Cost: Idle LB Detection

```python
def detect_idle_lbs() -> list[dict]:
    """CO-01: Detect load balancers with 0 connections for 24h+."""
    idle = []
    paginator = client.get_paginator('describe_load_balancers')
    
    for page in paginator.paginate():
        for lb in page['LoadBalancers']:
            metrics = cw.get_metric_statistics(
                Namespace='AWS/ApplicationELB',
                MetricName='ActiveConnectionCount',
                Dimensions=[{'Name': 'LoadBalancer', 'Value': lb['LoadBalancerArn']}],
                StartTime=datetime.utcnow() - timedelta(days=1),
                EndTime=datetime.utcnow(),
                Period=86400,
                Statistics=['Sum']
            )
            total_connections = sum(
                dp['Sum'] for dp in metrics['Datapoints']
            )
            if total_connections == 0:
                idle.append({
                    'name': lb['LoadBalancerName'],
                    'arn': lb['LoadBalancerArn'],
                    'type': lb['Type'],
                    'created': str(lb['CreatedTime'])
                })
                print(f"[AI_ASSIST] Idle LB: {lb['LoadBalancerName']} — 0 connections in 24h")
    
    return idle
```
```