# Core Concepts — ELB

## What is AWS ELB

- **Purpose**: Elastic Load Balancing — automatically distributes incoming traffic across multiple targets
- **Category**: Networking & Content Delivery
- **Console**: https://console.aws.amazon.com/ec2/v2/home?#LoadBalancers
- **Docs**: https://docs.aws.amazon.com/elasticloadbalancing/
- **Pricing**: https://aws.amazon.com/elasticloadbalancing/pricing/

## Load Balancer Types

| Type | Layer | Best For |
|------|-------|----------|
| ALB | Layer 7 (HTTP/HTTPS) | Web apps, microservices, container-based |
| NLB | Layer 4 (TCP/UDP/TLS) | High perf, low latency, gaming, IoT |
| CLB | Layer 4/7 (legacy) | Legacy apps (being deprecated) |

> Use `aws elbv2 describe-load-balancers --query "LoadBalancers[*].{Name:LoadBalancerName,Type:Type,Scheme:Scheme,State:State.Code}"` to list existing LBs.

## Quotas (Use API for current values)

```bash
# Check current quotas
aws service-quotas get-service-quota --service-code elasticloadbalancing --quota-code L-53DA43FF  # ALBs per region
aws service-quotas get-service-quota --service-code elasticloadbalancing --quota-code L-60BC2B0B  # NLBs per region
aws service-quotas get-service-quota --service-code elasticloadbalancing --quota-code L-11C51B2B  # Target groups per region
```

| Quota | Default | Adjustable |
|-------|---------|------------|
| LBs per Region (per type) | 20 | Yes |
| Target Groups per Region | 3000 | Yes |
| Listeners per LB | 50 | No |
| Rules per ALB Listener | 100 | No |
| Targets per Target Group | 1000 | Yes |

## Load Balancer Attributes (Use API for complete list)

```bash
aws elbv2 describe-load-balancer-attributes --load-balancer-arn {{arn}} --query "Attributes[*].{Key:Key,Value:Value}"
```

| Key | Supported | Description |
|-----|-----------|-------------|
| deletion_protection.enabled | ALB, NLB | Prevent accidental deletion |
| idle_timeout.timeout_seconds | ALB | Connection idle timeout |
| load_balancing.cross_zone.enabled | ALB, NLB | Cross-zone load balancing |
| routing.http2.enabled | ALB | HTTP/2 support |

## States & Health (Use API for current state)

```bash
# LB state
aws elbv2 describe-load-balancers --load-balancer-arns {{arn}} --query "LoadBalancers[0].State.Code"
# States: provisioning → active → (active_impaired | failed)

# Target health
aws elbv2 describe-target-health --target-group-arn {{arn}} --query "TargetHealthDescriptions[*].{Id:Target.Id,State:TargetHealth.State}"
# Health states: healthy | unhealthy | unused | draining | unavailable
```

## Target Types

| Type | Supported | Description |
|------|-----------|-------------|
| instance | ALB, NLB | EC2 instance ID |
| ip | ALB, NLB | IP address |
| lambda | ALB only | Lambda function ARN |

## Routing (Use API for complete rules)

```bash
# List listener rules
aws elbv2 describe-rules --listener-arn {{arn}} --query "Rules[*].{Priority:Priority, Conditions:Conditions, Actions:Actions}"
```
- **ALB**: Path/host/header/query-string/source-ip/method-based routing (Layer 7)
- **NLB**: TCP/UDP port-based routing only (Layer 4)

## Best Practices

### High Availability
- Deploy across ≥2 AZs; use ≥2 targets per Target Group; enable cross-zone

### Security
- ALB: Security groups, HTTPS with ACM certs, WAF, deletion protection
- NLB: TLS listeners, no SG support; source IP preserved

### Performance
- NLB for ultra-low latency; ALB for content-based routing

### Monitoring
- CloudWatch metrics: `TargetResponseTime`, `HealthyHostCount`, `HTTPCode_Target_5XX`