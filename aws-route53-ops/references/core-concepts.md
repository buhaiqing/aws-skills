# Route53 Core Concepts

AWS Route53 architecture, components, and operational concepts.

## Service Overview

**AWS Route53** - Scalable and highly available Domain Name System (DNS) web service.

**Key Benefits:**
- Global distribution for low latency
- High availability (100% SLA)
- Integration with AWS services
- Health checks and failover
- Traffic flow management

## Hosted Zones

### Public Hosted Zone
- **Purpose**: Internet-facing DNS
- **Use case**: Public website domains
- **Name servers**: Global anycast

### Private Hosted Zone
- **Purpose**: Internal VPC DNS
- **Use case**: Private applications
- **Association**: Specific VPCs

### Zone Types

| Type | Visibility | Use Case |
|------|------------|----------|
| Public | Internet | External applications |
| Private | VPC only | Internal services |

## Record Types

### A Record
Maps hostname to IPv4 address.
```
www.example.com → 192.0.2.1
```

### AAAA Record
Maps hostname to IPv6 address.
```
www.example.com → 2001:db8::1
```

### CNAME Record
Alias to another hostname (cannot be at zone apex).
```
www.example.com → myapp.example.com
```

### ALIAS Record
AWS-specific, maps to AWS resources (can be at zone apex).
```
example.com → my-alb-1234567890.us-east-1.elb.amazonaws.com
```

### MX Record
Mail exchange servers.
```
example.com → 10 mail1.example.com
example.com → 20 mail2.example.com
```

### TXT Record
Text records (SPF, DKIM verification).
```
example.com → "v=spf1 include:_spf.google.com ~all"
```

## Routing Policies

### Simple Routing
Single resource for a record.

### Failover Routing
Active-passive failover with health checks.
- Primary: Active
- Secondary: Standby

### Weighted Routing
Distribute traffic by weight.
- Server-1: 70%
- Server-2: 30%

### Latency-based Routing
Route to lowest latency region.
- us-east-1: North America
- eu-west-1: Europe
- ap-southeast-1: Asia

### Geolocation Routing
Route based on user location.
- Country: US
- Continent: Europe
- Default: Global

## Health Checks

### Endpoint Health Checks
Monitor endpoint health via HTTP/HTTPS/TCP.

### Types
- **HTTP/HTTPS**: Web applications
- **TCP**: Database connectivity
- **Calculated**: Aggregate multiple checks
- **CloudWatch**: Alarm-based

### Configuration
- **Request Interval**: 10s or 30s
- **Failure Threshold**: 1-10 failures
- **Regions**: Global or specific

### Status
- **Healthy**: Passing checks
- **Unhealthy**: Failing threshold
- **LastChecked**: Timestamp

## Quotas

| Resource | Default | Notes |
|----------|---------|-------|
| Hosted zones per account | 500 | Can increase |
| Records per zone | 10,000 | Can increase |
| Health checks | 200 | Per account |
| Query logging configurations | 1,000 | Per account |

## Pricing

- **Hosted zones**: $0.50/month per zone
- **Queries**: $0.40-$0.80 per million queries
- **Health checks**: $0.50-$2.00 per check/month
- **Traffic Flow**: $50.00 per policy/month

## Best Practices

### DNS Management
- Use short TTLs for frequent changes
- Use alias records for AWS resources
- Enable health checks for critical endpoints
- Use multiple routing policies for high availability

### Security
- Enable DNSSEC for zone signing
- Use private zones for internal services
- Monitor query patterns for anomalies
- Restrict zone changes to authorized users

### Performance
- Use latency-based routing for global apps
- Enable query logging for analysis
- Monitor health check status
- Test failover scenarios regularly