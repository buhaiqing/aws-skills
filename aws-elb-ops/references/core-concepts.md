# Core Concepts — ELB

## What is AWS ELB

- **Purpose**: Elastic Load Balancing — automatically distributes incoming traffic across multiple targets
- **Category**: Networking & Content Delivery
- **Console**: https://console.aws.amazon.com/ec2/v2/home?#LoadBalancers
- **Docs**: https://docs.aws.amazon.com/elasticloadbalancing/

## Load Balancer Types

| Type | Full Name | Layer | Best For |
|------|-----------|-------|----------|
| ALB | Application Load Balancer | Layer 7 (HTTP/HTTPS) | Web applications, microservices, container-based apps |
| NLB | Network Load Balancer | Layer 4 (TCP/UDP/TLS) | High performance, low latency, gaming, IoT |
| CLB | Classic Load Balancer | Layer 4/7 (legacy) | Legacy applications (being deprecated) |

## Key Components

### Load Balancer
| Component | Description | Console Path |
|-----------|-------------|--------------|
| Load Balancer | Entry point for traffic | EC2 → Load Balancers |
| DNS Name | Endpoint for routing | Load Balancer details |
| Availability Zones | Distribution across AZs | Load Balancer details |
| Security Groups | Network access control (ALB only) | Load Balancer details |

### Listener
| Component | Description | Console Path |
|-----------|-------------|--------------|
| Protocol | HTTP, HTTPS, TCP, TLS, UDP | Load Balancer → Listeners |
| Port | Listening port number | Listener details |
| Default Action | Forward, redirect, or fixed-response | Listener details |
| SSL Policy | Security policy for HTTPS/TLS | Listener details |
| Certificate | ACM certificate for HTTPS | Listener details |

### Target Group
| Component | Description | Console Path |
|-----------|-------------|--------------|
| Target Group | Collection of targets | EC2 → Target Groups |
| Protocol | HTTP, HTTPS, TCP, TLS, UDP | Target Group details |
| Port | Target port number | Target Group details |
| Target Type | instance, ip, lambda | Target Group details |
| Health Check | Monitoring target health | Target Group details |

### Rules (ALB only)
| Component | Description | Console Path |
|-----------|-------------|--------------|
| Rule | Path/host/header routing | Listener → Rules |
| Condition | Match criteria | Rule details |
| Action | Forward, redirect, authenticate | Rule details |
| Priority | Rule order (1-50000) | Rule details |

## Target Types

| Target Type | Supported LB | Description |
|--------------|--------------|-------------|
| instance | ALB, NLB | EC2 instance ID |
| ip | ALB, NLB | IP address (VPC CIDR or RFC 1918) |
| lambda | ALB only | Lambda function ARN |

## Health Check States

| State | Meaning | Traffic Routing |
|-------|---------|-----------------|
| healthy | Passing health checks | Route traffic |
| unhealthy | Failing health checks | Do not route |
| unused | Not registered to LB | Do not route |
| draining | Being deregistered | Stop routing, wait for connections |
| unavailable | Target disabled or health check disabled | Do not route |

## Load Balancer States

| State | Meaning |
|-------|---------|
| provisioning | Being created |
| active | Available and functional |
| active_impaired | Functional but degraded |
| failed | Creation failed |

## Quotas

| Quota | Default | Adjustable |
|-------|---------|------------|
| ALBs per Region | 20 | Yes |
| NLBs per Region | 20 | Yes |
| CLBs per Region | 20 | Yes |
| Target Groups per Region | 3000 | Yes |
| Listeners per LB | 50 | No |
| Rules per ALB Listener | 100 | No |
| Targets per Target Group | 1000 | Yes |
| Certificates per ALB | 25 | Yes |
| Zones per NLB | 10 | No |

## IP Address Types

| Type | ALB | NLB | Use Case |
|------|-----|-----|----------|
| ipv4 | ✅ | ✅ | IPv4 only |
| dualstack | ✅ | ✅ | IPv4 + IPv6 |

## Security Features

### ALB Security
- Security Groups: Required for ALB
- SSL/TLS: HTTPS listeners with ACM certificates
- WAF Integration: AWS WAF can be attached
- Authentication: Cognito or OIDC integration via rules

### NLB Security
- Security Groups: NOT supported
- TLS Listeners: TLS termination supported
- Source IP Preservation: Client IP visible to targets

## Routing Capabilities

### ALB (Layer 7)
| Routing Type | Condition Field | Example |
|--------------|-----------------|---------|
| Path-based | path-pattern | `/api/*` |
| Host-based | host-header | `api.example.com` |
| Header-based | http-header | `X-API-Version: v1` |
| Query string | query-string | `version=v1` |
| Source IP | source-ip | `10.0.0.0/8` |
| Method | http-request-method | `POST` |

### NLB (Layer 4)
- No path-based routing
- TCP/UDP port-based routing only
- Zonal DNS resolution for low latency

## Load Balancer Attributes

| Attribute | ALB | NLB | Description |
|-----------|-----|-----|-------------|
| deletion_protection.enabled | ✅ | ✅ | Prevent accidental deletion |
| idle_timeout.timeout_seconds | ✅ | - | Connection idle timeout (1-3600s) |
| load_balancing.cross_zone.enabled | ✅ | ✅ | Cross-zone load balancing |
| routing.http2.enabled | ✅ | - | HTTP/2 support |
| routing.http.drop_invalid_header_fields.enabled | ✅ | - | Drop invalid headers |
| waf.fail_open.enabled | ✅ | - | WAF fail-open behavior |

## Best Practices

### High Availability
- Deploy across multiple Availability Zones (minimum 2)
- Use at least 2 targets per Target Group
- Enable cross-zone load balancing

### Health Checks
- Use realistic health check paths
- Set appropriate thresholds (healthy: 5, unhealthy: 2)
- Monitor health check metrics

### Security
- Use HTTPS listeners with ACM certificates
- Apply appropriate security groups (ALB)
- Enable deletion protection

### Performance
- NLB for ultra-low latency requirements
- ALB for content-based routing
- Pre-warm ALB for predictable traffic spikes

### Monitoring
- Enable CloudWatch metrics
- Set up alarms for unhealthy targets
- Monitor latency and error rates

## Pricing

| LB Type | Base Hourly | Per LCU/NUC | Data Processing |
|---------|-------------|-------------|-----------------|
| ALB | $0.0225/hour | LCU: $0.008 | N/A |
| NLB | $0.0225/hour | NCU: $0.006 | $0.006/GB |
| CLB | $0.025/hour | $0.008/GB | Included |

## Related Services

| Service | Integration |
|---------|-------------|
| EC2 | Target instances |
| Auto Scaling | Automatic target registration |
| ECS | Container targets via IP mode |
| Lambda | Lambda targets (ALB) |
| Route 53 | DNS health checks and routing |
| WAF | Web application firewall (ALB) |
| Global Accelerator | Global load balancing (NLB) |
| CloudWatch | Metrics and alarms |
| Certificate Manager | SSL/TLS certificates |