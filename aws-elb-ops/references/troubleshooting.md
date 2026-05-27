# Troubleshooting — ELB

## Common Error Codes

| Error | Agent Action |
|-------|-------------|
| DuplicateLoadBalancerName (400) | HALT; use different name |
| InvalidSubnet (400) | HALT; verify subnets |
| InvalidSecurityGroup (400) | HALT; verify SG |
| InvalidVpcId (400) | HALT; verify VPC |
| InvalidParameterValue (400) | Fix parameter; retry once |
| QuotaExceeded (400) | HALT; request quota increase |
| ListenerNotFound (404) | HALT; verify ARN |
| LoadBalancerNotFound (404) | HALT; verify ARN |
| TargetGroupNotFound (404) | HALT; verify ARN |
| ResourceInUse (409) | Remove dependencies first |
| InvalidConfigurationRequest (400) | Review config; retry once |
| ThrottlingException (429) | Backoff; retry 3x |
| ServiceUnavailable (500) | Retry 3x; HALT if persists |

## Diagnostic Order

1. **Verify credentials**: `aws sts get-caller-identity`
2. **Verify VPC**: `aws ec2 describe-vpcs --vpc-ids {{user.vpc_id}}`
3. **Verify subnets**: `aws ec2 describe-subnets --subnet-ids {{user.subnet_ids}}`
4. **Verify security groups**: `aws ec2 describe-security-groups --group-ids {{user.sg_ids}}`
5. **Verify load balancer exists**: `aws elbv2 describe-load-balancers --load-balancer-arns {{arn}}`
6. **Verify target group exists**: `aws elbv2 describe-target-groups --target-group-arns {{arn}}`
7. **Check target health**: `aws elbv2 describe-target-health --target-group-arn {{arn}}`

## Common Issues

### DuplicateLoadBalancerName

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Cannot create LB | Name already in use | Use different name (names are unique per region) |
| Name reused after delete | ELB retains deleted LB name for protection period | Wait or use different name |

### InvalidSubnet

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Subnet not found | Wrong subnet ID | Verify subnet exists in region |
| Subnets not same VPC | Subnets from different VPCs | Use subnets from same VPC |
| Subnet not in valid AZ | Availability Zone mismatch | Use subnets in same AZs as LB |

### InvalidSecurityGroup

| Symptom | Cause | Resolution |
|---------|-------|------------|
| SG not found | Wrong security group ID | Verify SG exists in region |
| SG not same VPC | SG from different VPC | Use SG from same VPC as subnets |
| NLB with SG | NLB does not support SG | Remove SG parameter for NLB |

### LoadBalancerNotFound

| Symptom | Cause | Resolution |
|---------|-------|------------|
| ARN not found | Wrong ARN format | Verify full ARN including region and account |
| LB deleted | LB already deleted | Recreate LB if needed |
| Wrong region | LB in different region | Check correct region |

### ResourceInUse (Delete Conflict)

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Cannot delete LB | Listeners attached | Delete listeners first |
| Cannot delete LB | Target groups referenced | Delete listeners referencing TG |
| Cannot delete TG | Targets registered | Deregister targets first |
| Cannot delete TG | Referenced by listener | Delete listener or modify default action |

### Target Health Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| All targets unhealthy | Health check path invalid | Verify health check path returns 200 |
| Targets timing out | Port mismatch | Verify target port matches health check port |
| Targets draining | Deregistration in progress | Wait for draining to complete |
| Targets unavailable | Health check disabled | Enable health checks |

### Listener Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Cannot create HTTPS listener | Certificate not found | Verify ACM certificate ARN |
| Cannot create HTTPS listener | Certificate not in region | Use certificate in same region |
| Listener redirect fails | Invalid redirect URL | Fix redirect URL format |
| Authentication fails | Cognito/OIDC config wrong | Verify IdP configuration |

### Cross-Zone Load Balancing

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Uneven traffic distribution | Cross-zone disabled | Enable cross-zone load balancing |
| Targets in single AZ overloaded | Cross-zone disabled | Enable or distribute targets across AZs |

### NLB Specific Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Cannot resolve DNS | NLB not yet provisioned | Wait for NLB to become active |
| High latency | Cross-zone disabled | Enable cross-zone for balanced distribution |
| Connection resets | Health check too aggressive | Adjust health check thresholds |
| Source IP not visible | Check target type | Use instance or IP target type |

### ALB Specific Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| 502 Bad Gateway | Target not responding | Verify target health and port |
| 503 Service Unavailable | No healthy targets | Register targets and verify health |
| 504 Gateway Timeout | Idle timeout too short | Increase idle_timeout attribute |
| HTTP/2 not working | HTTP/2 disabled | Enable routing.http2.enabled attribute |

## Permissions Required

| Action | Minimum IAM Permissions |
|--------|-------------------------|
| Create LB | `elasticloadbalancing:CreateLoadBalancer` |
| Describe LB | `elasticloadbalancing:DescribeLoadBalancers` |
| Delete LB | `elasticloadbalancing:DeleteLoadBalancer` |
| Create Target Group | `elasticloadbalancing:CreateTargetGroup` |
| Register Targets | `elasticloadbalancing:RegisterTargets` |
| Describe Target Health | `elasticloadbalancing:DescribeTargetHealth` |
| Create Listener | `elasticloadbalancing:CreateListener` |
| Delete Listener | `elasticloadbalancing:DeleteListener` |
| Create Rule | `elasticloadbalancing:CreateRule` |
| Modify LB Attributes | `elasticloadbalancing:ModifyLoadBalancerAttributes` |
| Describe VPC/Subnets | `ec2:DescribeVpcs`, `ec2:DescribeSubnets` |
| Describe Security Groups | `ec2:DescribeSecurityGroups` |

## Cleanup Sequence (Delete Load Balancer)

```
1. List listeners: describe-listeners --load-balancer-arn {{lb_arn}}
2. Delete each listener: delete-listener --listener-arn {{listener_arn}}
3. List target groups: describe-target-groups --load-balancer-arn {{lb_arn}}
4. Deregister targets: deregister-targets for each TG
5. Delete target groups: delete-target-group for each
6. Delete load balancer: delete-load-balancer --load-balancer-arn {{lb_arn}}
```

## Cleanup Sequence (Delete Target Group)

```
1. Deregister all targets: deregister-targets --target-group-arn {{tg_arn}}
2. Verify no targets: describe-target-health should return empty
3. Delete target group: delete-target-group --target-group-arn {{tg_arn}}
```

## Health Check Troubleshooting

```bash
# Check target health status
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:region:account:targetgroup/name/id \
  --output json

# Common health check issues:
# 1. Path returns 404: Fix health check path
# 2. Timeout: Increase timeout or fix application
# 3. Wrong port: Verify target port matches config

# Verify health check configuration
aws elbv2 describe-target-groups \
  --target-group-arns arn:aws:elasticloadbalancing:region:account:targetgroup/name/id \
  --output json | jq '.TargetGroups[0].HealthCheckConfig'
```

## Listener Troubleshooting

```bash
# Check listener configuration
aws elbv2 describe-listeners \
  --load-balancer-arn arn:aws:elasticloadbalancing:region:account:loadbalancer/app/name/id \
  --output json

# Verify SSL certificate
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:region:account:certificate/id \
  --output json

# Check listener rules
aws elbv2 describe-rules \
  --listener-arn arn:aws:elasticloadbalancing:region:account:listener/app/name/id/port \
  --output json
```

## Recovery Actions

| Error | Max Retries | Action |
|-------|-------------|--------|
| 5xx ServiceUnavailable | 3 | Backoff 2s, 4s, 8s; HALT after 3 |
| 429 ThrottlingException | 3 | Exponential backoff |
| 400 InvalidParameterValue | 1 | Fix; retry once |
| 400 DuplicateLoadBalancerName | 0 | HALT; use different name |
| 409 ResourceInUse | 0 | HALT; clean dependencies first |
| 404 LoadBalancerNotFound | 0 | HALT; verify ARN |
| 404 TargetGroupNotFound | 0 | HALT; verify ARN |

## CloudWatch Metrics for Troubleshooting

| Metric | LB Type | Purpose |
|--------|---------|---------|
| TargetResponseTime | ALB | Backend latency |
| RequestCount | ALB | Traffic volume |
| HTTPCode_Target_2XX/4XX/5XX | ALB | Backend response codes |
| HTTPCode_ELB_4XX/5XX | ALB | ELB errors (502, 503, 504) |
| ActiveConnectionCount | NLB | Connection count |
| NewConnectionCount | NLB | Connection rate |
| ProcessedBytes | NLB | Throughput |
| HealthyHostCount | ALB/NLB | Healthy target count |
| UnHealthyHostCount | ALB/NLB | Unhealthy target count |

## Diagnostic Commands

```bash
# Full LB status
aws elbv2 describe-load-balancers \
  --load-balancer-arns {{lb_arn}} \
  --output json | jq '.LoadBalancers[0].{Name,State,Type,DNSName}'

# Full target group status
aws elbv2 describe-target-groups \
  --target-group-arns {{tg_arn}} \
  --output json | jq '.TargetGroups[0].{TargetGroupName,Protocol,Port,HealthCheckConfig}'

# Target health breakdown
aws elbv2 describe-target-health \
  --target-group-arn {{tg_arn}} \
  --output json | jq '.TargetHealthDescriptions[].{TargetId,TargetHealth}'

# LB attributes
aws elbv2 describe-load-balancer-attributes \
  --load-balancer-arn {{lb_arn}} \
  --output json
```

## Access Logs

Enable access logs for troubleshooting:
```bash
aws elbv2 modify-load-balancer-attributes \
  --load-balancer-arn {{lb_arn}} \
  --attributes Key=access_logs.s3.enabled,Value=true Key=access_logs.s3.bucket,Value={{bucket_name}} \
  --output json
```