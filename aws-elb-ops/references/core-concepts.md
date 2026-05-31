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

---

## AIOps: Full CloudWatch Metrics Reference

### ALB Metrics (AWS/ApplicationELB)

| Metric | AIOps Use Case | Statistic | Period | Anomaly Detection |
|--------|---------------|-----------|--------|-------------------|
| `TargetResponseTime` | Latency anomaly (p50/p90/p99) | Average, p90, p99 | 60s/300s | ✅ ANOMALY_DETECTION_BAND (seasonal) |
| `HTTPCode_Target_5XX` | Backend error rate | Sum | 60s/300s | ✅ Static threshold > 5% of total |
| `HTTPCode_Target_4XX` | Backend client errors (e.g., 404) | Sum | 300s | ✅ Static threshold |
| `HTTPCode_ELB_5XX` | ELB infrastructure issues | Sum | 60s | ⚠️ Should be 0; alarm at > 0 |
| `HealthyHostCount` | Target health level | Average, Minimum | 60s | ✅ Static threshold < minimum healthy |
| `UnHealthyHostCount` | Health degradation | Maximum | 60s | ✅ Static threshold > 0 |
| `RequestCount` | Traffic volume anomaly | Sum | 60s/300s | ✅ ANOMALY_DETECTION_BAND (seasonal) |
| `ActiveConnectionCount` | Connection pool saturation | Average, Maximum | 60s | ✅ Static threshold > 80% of capacity |
| `NewConnectionCount` | New connection rate | Sum | 60s | ✅ ANOMALY_DETECTION_BAND |
| `RejectedConnectionCount` | Capacity exhaustion | Sum | 60s | ⚠️ Should be 0; alarm at > 0 |
| `ConsumedLCUs` | Cost & capacity tracking | Average, Maximum | 60s | ✅ FORECAST for capacity planning |
| `ProcessedBytes` | Throughput tracking | Sum | 60s | ✅ ANOMALY_DETECTION_BAND |
| `RuleEvaluations` | Rule processing volume | Sum | 60s | ✅ Static threshold |
| `ClientTLSNegotiationErrorCount` | TLS handshake failures | Sum | 60s | ✅ Static threshold > 0 |

### NLB Metrics (AWS/NetworkELB)

| Metric | AIOps Use Case | Statistic | Period | Anomaly Detection |
|--------|---------------|-----------|--------|-------------------|
| `ActiveFlowCount` | Flow capacity tracking | Average, Maximum | 60s | ✅ Static threshold > 80% of limit |
| `NewFlowCount` | Traffic surge detection | Sum | 60s | ✅ ANOMALY_DETECTION_BAND (seasonal) |
| `ProcessedBytes` | Throughput anomaly | Sum | 60s | ✅ ANOMALY_DETECTION_BAND |
| `HealthyHostCount` | Target health level | Average, Minimum | 60s | ✅ Static threshold |
| `UnHealthyHostCount` | Health degradation | Maximum | 60s | ✅ Static threshold > 0 |
| `ConsumedLCUs` | Cost & capacity tracking | Average, Maximum | 60s | ✅ FORECAST for planning |

### Metric Math for Derived Metrics

```bash
# Error rate (% of total requests)
aws cloudwatch get-metric-data \
  --metric-data-queries '[
    {"Id":"errors","MetricStat":{"Metric":{"Namespace":"AWS/ApplicationELB","MetricName":"HTTPCode_Target_5XX"},"Period":300,"Stat":"Sum"},"Label":"5XX Errors"},
    {"Id":"total","MetricStat":{"Metric":{"Namespace":"AWS/ApplicationELB","MetricName":"RequestCount"},"Period":300,"Stat":"Sum"},"Label":"Total Requests"},
    {"Id":"rate","Expression":"errors/total*100","Label":"Error Rate %"}
  ]' \
  --start-time "{{u.start}}" --end-time "{{u.end}}"
```

| Expression | Description | AIOps Use |
|------------|-------------|-----------|
| `m1/SUM(m1)` | Percentage distribution | Cross-AZ imbalance detection |
| `rate(m1)` | Rate of change | Burst/ramp detection |
| `FORECAST(m1, "linear", 168)` | 7-day trend prediction | Capacity planning |
| `ANOMALY_DETECTION_BAND(m1, 2)` | ML-based threshold | Seasonal anomaly detection |

### CloudWatch Logs Insights — ELB Access Log Analysis

```bash
# Top 10 5XX error URLs
fields @timestamp, request_url, target_status_code
| filter elb_status_code >= 500
| stats count() by request_url
| sort count desc
| limit 10

# Latency distribution (p50/p90/p99)
fields @timestamp,
       target_processing_time * 1000 as target_ms,
       request_processing_time * 1000 as request_ms
| stats avg(target_ms) as avg,
         percentile(target_ms, 50) as p50,
         percentile(target_ms, 90) as p90,
         percentile(target_ms, 99) as p99

# Target health check analysis
fields @timestamp, target_ip, target_status_code
| filter request_url like /health/
| stats count() as total,
        sum(case when target_status_code >= 500 then 1 else 0 end) as errors
        by target_ip
| sort errors desc

# Abnormal user agents (DDoS/anomaly detection)
fields @timestamp, user_agent, target_ip
| stats count() by user_agent
| sort count desc
| limit 100
```

---

## AIOps: Health Trend Analysis

### Anomaly Detection Patterns

| Pattern ID | Detection Method | Threshold | Data Required |
|-----------|-----------------|-----------|---------------|
| **PT-01** | Target flapping | >3 state transitions per target per 5 min | `describe-target-health` history |
| **PT-02** | Latency spike | TargetResponseTime > baseline μ + 3σ | 7+ days CloudWatch data |
| **PT-03** | Error rate surge | HTTPCode_Target_5XX > 5% of total OR 2× daily avg | 14+ days CloudWatch data |
| **PT-04** | Connection saturation | ActiveConnectionCount > 80% of max or >0 RejectedConnectionCount | `describe-load-balancer-attributes` capacity |
| **PT-05** | Cross-AZ imbalance | RequestCount std dev across AZs > 30% of mean | 24h+ CloudWatch with TargetGroup+AZ dimension |
| **PT-06** | Gradual degradation | HealthyHostCount linearly decreasing over 60 min | CloudWatch minimum statistic |
| **PT-07** | Traffic anomaly | RequestCount deviates from ANOMALY_DETECTION_BAND | 14+ days CloudWatch data |

### RCA Methodology: Time-Series Alignment

```
T-30min ─────────────────────────────── T0 ───────────────── T+15min
                  ↓
[CloudWatch] TargetResponseTime ↗       ← Latency starts rising
[CloudWatch] HTTPCode_Target_5XX ↗       ← Errors follow
[CloudWatch] HealthyHostCount ↘          ← Targets marked unhealthy
[CloudTrail]  SG/Listener change?        ← Check for config changes
[CloudWatch] EC2 CPUUtilization ↗        ← Backend overloaded
```

**Alignment Rule**: 
1. Identify T0 when the primary anomaly metric crossed threshold
2. Check all metrics for changes within [T0 - 30min, T0 + 15min]
3. Check CloudTrail events in same window → identify configuration changes
4. Check all metrics for changes within [T0 - 30min, T0 + 15min]

---

## AIOps: Data Source Map

```
                                  ┌──────────────────────┐
                                  │    AIOps Pipeline     │
                                  │  (This Skill Module)  │
                                  └──────┬───────┬───────┘
                                         │       │
                    ┌────────────────────┘       └────────────────────┐
                    ▼                                                   ▼
        ┌───────────────────────┐                     ┌───────────────────────────┐
        │  Real-time Telemetry   │                     │  Historical & Audit Data  │
        │  (CloudWatch Metrics)  │                     │  (S3 / CloudTrail / Logs) │
        └───────────────────────┘                     └───────────────────────────┘
           │           │                                      │
           ▼           ▼                                      ▼
   AWS/ApplicationELB  AWS/NetworkELB            ELB Access Logs (S3)
   TargetResponseTime  ActiveFlowCount           → Athena / Logs Insights
   HealthyHostCount    NewFlowCount              → Error, latency, pattern analysis
   RequestCount        ProcessedBytes
   HTTPCode_*_5XX      HealthyHostCount          CloudTrail (Management Events)
   ActiveConnCount     UnHealthyHostCount        → Configuration change tracking
   RejectedConnCount   ConsumedLCUs              → Rollback target identification
   ConsumedLCUs                                  → Security audit

        ┌────────────────────────────┐    ┌────────────────────────────┐
        │   Cross-Service Context     │    │   External Health Signals   │
        │   (Other Skill Modules)     │    │   (AWS Health / Config)     │
        └────────────────────────────┘    └────────────────────────────┘
           │           │                              │
           ▼           ▼                              ▼
   aws-ec2-ops    aws-vpc-ops              AWS Health API
   CPU/Mem/Disk   Flow Logs / SG           Service health events
   StatusCheck    NAT Gateway               Planned maintenance

   aws-route53-ops   aws-cloudwatch-ops    AWS Config Rules
   DNS health check  Anomaly detection      Compliance scanning
   Failover routing  FORECAST prediction     Drift detection
```

---

## AIOps: Cost Awareness

### ELB Pricing Components

| Component | ALB | NLB |
|-----------|-----|-----|
| Hourly charge | $0.0225/hr | $0.0225/hr |
| LCU hourly | $0.008/LCU | $0.006/LCU |
| Data processed | + per GB | + per GB |

### Cost Anomaly Detection

```bash
# Track LCU consumption trend
aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB \
  --metric-name ConsumedLCUs \
  --dimensions Name=LoadBalancer,Value={{lb_arn}} \
  --statistics Average --period 86400 \
  --start-time "$(date -d '-30 days' -u +%Y-%m-%dT00:00:00Z)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

### Optimization Heuristics

| Condition | Suggestion | Cost Impact |
|-----------|-----------|-------------|
| RequestCount < 100/min for 7 days | Consider removing LB, use direct connection | ~$16+/month |
| UnHealthyHostCount > 0 for 48h | Diagnose targets; idle LB still accrues cost | Waste of target resources |
| Rules > 20 per listener | Review if path-based routing could be simplified | Marginal |
| ALB with only TCP listeners | Migrate to NLB | ~25-40% less per LCU |

---

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
- **(AIOps)** Enable access logs (S3 destination) for root cause analysis
- **(AIOps)** Set anomaly detection alarms for seasonal traffic patterns
- **(AIOps)** Use FORECAST for weekly capacity planning
- **(AIOps)** Enable deletion protection + access logs for compliance

### AIOps Best Practices

1. **Enable access logs** — without them, RCA is blind for error/ latency analysis
2. **Tag all LBs with AIOps=true** — enables automated lifecycle management
3. **Set CloudWatch anomaly detection** on RequestCount and TargetResponseTime
4. **Run FORECAST weekly** for capacity planning on ConsumedLCUs
5. **Audit CloudTrail events** after any incident — configuration changes are a top cause
6. **Prefer [AUTO_HEAL] only for reversible operations** — target re-registration is safe; SG changes are not
7. **Maintain baseline** — capture healthy-state metrics for comparison during RCA
