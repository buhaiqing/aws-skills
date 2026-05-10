# AWS CLI Usage — ELB

## Command Map (elbv2 for ALB/NLB)

| Goal | CLI Command | JSON Output Path |
|------|-------------|------------------|
| Create ALB/NLB | `aws elbv2 create-load-balancer` | `.LoadBalancers[0].LoadBalancerArn` |
| Describe LBs | `aws elbv2 describe-load-balancers` | `.LoadBalancers[]` |
| Delete LB | `aws elbv2 delete-load-balancer` | Empty (success) |
| Create Target Group | `aws elbv2 create-target-group` | `.TargetGroups[0].TargetGroupArn` |
| Describe Target Groups | `aws elbv2 describe-target-groups` | `.TargetGroups[]` |
| Delete Target Group | `aws elbv2 delete-target-group` | Empty (success) |
| Register Targets | `aws elbv2 register-targets` | Empty (success) |
| Deregister Targets | `aws elbv2 deregister-targets` | Empty (success) |
| Create Listener | `aws elbv2 create-listener` | `.Listeners[0].ListenerArn` |
| Describe Listeners | `aws elbv2 describe-listeners` | `.Listeners[]` |
| Delete Listener | `aws elbv2 delete-listener` | Empty (success) |
| Describe Target Health | `aws elbv2 describe-target-health` | `.TargetHealthDescriptions[]` |
| Modify LB | `aws elbv2 modify-load-balancer-attributes` | `.Attributes[]` |

## Classic Load Balancer (elb)

| Goal | CLI Command | JSON Output Path |
|------|-------------|------------------|
| Create CLB | `aws elb create-load-balancer` | `.LoadBalancerName` |
| Describe CLBs | `aws elb describe-load-balancers` | `.LoadBalancerDescriptions[]` |
| Delete CLB | `aws elb delete-load-balancer` | Empty (success) |
| Configure Health Check | `aws elb configure-health-check` | `.HealthCheck` |
| Register Instances | `aws elb register-instances-with-load-balancer` | `.Instances[]` |

## Key CLI Conventions

### Global Service
ELB is **regional** — region parameter required.

### Output Format
Always use `--output json` for agent parsing.

### Load Balancer Types (elbv2)
- `application` — ALB (Layer 7)
- `network` — NLB (Layer 4)

## Common Patterns

### Create Application Load Balancer
```bash
aws elbv2 create-load-balancer \
  --name my-alb \
  --type application \
  --subnets subnet-aaa subnet-bbb \
  --security-groups sg-xxx \
  --output json
```

### Create Network Load Balancer
```bash
aws elbv2 create-load-balancer \
  --name my-nlb \
  --type network \
  --subnets subnet-aaa subnet-bbb \
  --output json
```

### Create Target Group (HTTP)
```bash
aws elbv2 create-target-group \
  --name my-targets \
  --protocol HTTP \
  --port 80 \
  --vpc-id vpc-xxx \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --output json
```

### Create Target Group (TCP for NLB)
```bash
aws elbv2 create-target-group \
  --name my-tcp-targets \
  --protocol TCP \
  --port 8080 \
  --vpc-id vpc-xxx \
  --output json
```

### Register EC2 Instances as Targets
```bash
aws elbv2 register-targets \
  --target-group-arn arn:aws:elasticloadbalancing:region:account:targetgroup/my-targets/xxx \
  --targets Id=i-aaa Id=i-bbb \
  --output json
```

### Register Lambda as Target (ALB only)
```bash
aws elbv2 register-targets \
  --target-group-arn arn:aws:elasticloadbalancing:region:account:targetgroup/my-lambda-tg/xxx \
  --targets Id=arn:aws:lambda:region:account:function:my-function \
  --output json
```

### Create Listener (HTTP)
```bash
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:region:account:loadbalancer/app/my-alb/xxx \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:region:account:targetgroup/my-targets/xxx \
  --output json
```

### Create Listener (HTTPS with SSL)
```bash
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:region:account:loadbalancer/app/my-alb/xxx \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=arn:aws:acm:region:account:certificate/xxx \
  --ssl-policy ELBSecurityPolicy-2016-08 \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:region:account:targetgroup/my-targets/xxx \
  --output json
```

### Describe Load Balancers
```bash
aws elbv2 describe-load-balancers --output json
# Filter by ARN
aws elbv2 describe-load-balancers \
  --load-balancer-arns arn:aws:elasticloadbalancing:region:account:loadbalancer/app/my-alb/xxx \
  --output json
```

### Describe Target Health
```bash
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:region:account:targetgroup/my-targets/xxx \
  --output json
```

### Describe Listeners
```bash
aws elbv2 describe-listeners \
  --load-balancer-arn arn:aws:elasticloadbalancing:region:account:loadbalancer/app/my-alb/xxx \
  --output json
```

### Modify Load Balancer Attributes
```bash
aws elbv2 modify-load-balancer-attributes \
  --load-balancer-arn arn:aws:elasticloadbalancing:region:account:loadbalancer/app/my-alb/xxx \
  --attributes Key=deletion_protection.enabled,Value=true \
  --output json
```

### Delete Listener (Required before LB delete)
```bash
aws elbv2 delete-listener \
  --listener-arn arn:aws:elasticloadbalancing:region:account:listener/app/my-alb/xxx/yyy \
  --output json
```

### Delete Target Group (After deregistering targets)
```bash
aws elbv2 delete-target-group \
  --target-group-arn arn:aws:elasticloadbalancing:region:account:targetgroup/my-targets/xxx \
  --output json
```

### Delete Load Balancer
```bash
# Safety Gate: Confirm with user before deletion
aws elbv2 delete-load-balancer \
  --load-balancer-arn arn:aws:elasticloadbalancing:region:account:loadbalancer/app/my-alb/xxx \
  --output json
```

### Classic Load Balancer Operations
```bash
# Create CLB (legacy)
aws elb create-load-balancer \
  --load-balancer-name my-clb \
  --listeners Protocol=HTTP,LoadBalancerPort=80,InstanceProtocol=HTTP,InstancePort=80 \
  --subnets subnet-aaa subnet-bbb \
  --security-groups sg-xxx \
  --output json

# Configure health check
aws elb configure-health-check \
  --load-balancer-name my-clb \
  --health-check Target=HTTP:80/health,Interval=30,Timeout=5,UnhealthyThreshold=2,HealthyThreshold=10 \
  --output json

# Register instances
aws elb register-instances-with-load-balancer \
  --load-balancer-name my-clb \
  --instances i-aaa i-bbb \
  --output json

# Describe CLBs
aws elb describe-load-balancers --output json

# Delete CLB
aws elb delete-load-balancer --load-balancer-name my-clb --output json
```

## ARN Format

| Resource | ARN Pattern |
|----------|-------------|
| ALB | `arn:aws:elasticloadbalancing:region:account:loadbalancer/app/name/id` |
| NLB | `arn:aws:elasticloadbalancing:region:account:loadbalancer/net/name/id` |
| CLB | `arn:aws:elasticloadbalancing:region:account:loadbalancer/name` |
| Target Group | `arn:aws:elasticloadbalancing:region:account:targetgroup/name/id` |
| Listener | `arn:aws:elasticloadbalancing:region:account:listener/app/name/id/port` |

## Waiters

ELB state transitions require polling:

| Operation | Wait Command | Terminal State |
|-----------|--------------|----------------|
| Create ALB | Poll describe | `available` |
| Create NLB | Poll describe | `active` |
| Delete LB | Poll describe | Not found |
| Register targets | Poll target health | `healthy` |

## CLI vs API Coverage

| Operation (API) | CLI Available | Notes |
|-----------------|---------------|-------|
| CreateLoadBalancer | ✅ | `create-load-balancer` (elbv2) |
| DescribeLoadBalancers | ✅ | `describe-load-balancers` (elbv2) |
| DeleteLoadBalancer | ✅ | `delete-load-balancer` (elbv2) |
| CreateTargetGroup | ✅ | `create-target-group` (elbv2) |
| RegisterTargets | ✅ | `register-targets` (elbv2) |
| DescribeTargetHealth | ✅ | `describe-target-health` (elbv2) |
| CreateListener | ✅ | `create-listener` (elbv2) |
| DeleteListener | ✅ | `delete-listener` (elbv2) |
| CreateRule | ✅ | `create-rule` (elbv2) |
| ModifyListener | ✅ | `modify-listener` (elbv2) |

## Credential Handling

CLI reads credentials in priority order:
1. Environment: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
2. Config file: `~/.aws/credentials`
3. IAM role (EC2/Lambda)

Verify:
```bash
aws sts get-caller-identity --output json
```