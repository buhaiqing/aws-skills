# Integration Guide — ELB AIOps: CloudTrail & AWS Config

_Latest update: 2026-05-31_

This document covers how to integrate CloudTrail (change audit) and AWS Config (compliance & drift detection)
with the ELB AIOps closed-loop. Both services are **free-tier eligible** for basic usage and require no
additional infrastructure.

---

## 1. CloudTrail Integration

### What CloudTrail Provides

CloudTrail records all API calls to ELB, EC2, VPC, and related services as **management events**.
These events are essential for:
- **RC-01/RC-03 RCA**: Track who changed what and when around anomaly time
- **CM-03 Auto-rollback**: Identify the last known-good configuration
- **AH-05 SG drift**: Detect security group rule changes
- **CO-05 Cost anomaly**: Correlate cost spikes with resource creation events

### Enablement Status

| Component | Status | Cost |
|-----------|--------|------|
| Management Events | ✅ **Default ON** — 90-day retention | Free |
| Data Events (S3, Lambda) | ⚠️ Optional — manually enable | Extra cost |
| CloudTrail Insights | ⚠️ Optional — anomalous activity detection | ~$1/event |
| Trails to S3 (long-term) | ⚠️ Optional — > 90-day retention | S3 storage |

**For AIOps purposes, management events are sufficient and free.**

### Key CloudTrail Events for ELB AIOps

#### Load Balancer Events
```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceType,AttributeValue=AWS::ElasticLoadBalancing::LoadBalancer \
  --start-time "2026-05-30T00:00:00Z" --end-time "2026-05-31T00:00:00Z"
```

| Event Name | AIOps Use |
|-----------|-----------|
| `CreateLoadBalancer` | Quota tracking, cost anomaly RCA |
| `DeleteLoadBalancer` | Safety audit, CM-01 impact analysis |
| `ModifyLoadBalancerAttributes` | Compliance drift detection |
| `SetSecurityGroups` | RC-03 target unhealthy RCA |
| `SetSubnets` | Network connectivity change tracking |
| `CreateListener` / `DeleteListener` | Traffic routing change audit |
| `CreateRule` / `DeleteRule` | Routing rule drift detection |
| `RegisterTargets` / `DeregisterTargets` | Target health change tracking |

#### Related Events from Other Services

```bash
# Security Group changes — often root cause of health check failures
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=AuthorizeSecurityGroupIngress \
  --start-time "{{T0-2h}}" --end-time "{{T0+5m}}"
```

| Event Name | Service | AIOps Use |
|-----------|---------|-----------|
| `AuthorizeSecurityGroupIngress` | EC2 | Possible health check blocker |
| `RevokeSecurityGroupIngress` | EC2 | Possible accidental rule removal |
| `RunInstances` | EC2 | New target registration tracking |
| `TerminateInstances` | EC2 | Target disappearance RCA |
| `StopInstances` | EC2 | Target health change |
| `CreateAutoScalingGroup` | AutoScaling | ASG-LB binding audit |
| `ChangeResourceRecordSets` | Route53 | DNS routing change — failover audit |

### RCA Integration Pattern

When an anomaly is detected, the AI agent runs this standardized CloudTrail query:

```bash
# Standard query: changes related to a specific LB within time window
LB_ARN="arn:aws:elasticloadbalancing:us-east-1:123456789:loadbalancer/app/my-alb/xxx"
T0="2026-05-31T10:23:00Z"

aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue="$LB_ARN" \
  --start-time "$(date -d '$T0 - 2 hours' -u +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -d '$T0 + 5 minutes' -u +%Y-%m-%dT%H:%M:%SZ)" \
  --query 'Events[].{Time:EventTime,Name:EventName,User:Username,Resource:Resources[0].ResourceName}'
```

### RCA Decision Matrix (CloudTrail-Augmented)

| CloudTrail Finding | Anomaly Symptom | Diagnosis |
|--------------------|-----------------|-----------|
| SG rule changed near T0 | Targets unhealthy | **Root cause**: SG blocking health check traffic → `[AUTO_HEAL]` revert |
| Listener deleted near T0 | 502 errors | **Root cause**: Listener removed → `[MANUAL]` recreate |
| Instance terminated near T0 | UnHealthyHostCount > 0 | **Root cause**: Target instance terminated → `[AI_ASSIST]` add new target |
| No change events | Gradual latency increase | **Root cause**: Capacity saturation (organic growth) → `[AI_ASSIST]` scale |

---

## 2. AWS Config Integration

### What AWS Config Provides

AWS Config continuously monitors and records **resource configuration changes** and evaluates them against
**desired compliance rules**. For ELB AIOps, this enables:
- **CM-04 Compliance scanning**: Automated baseline verification
- **AH-05 Configuration drift detection**: Revert non-compliant changes
- **Resource dependency mapping**: Which LB is connected to which TG/SG/Listener

### Enablement

```bash
# Step 1: Enable AWS Config recorder (one-time per region)
aws configservice put-configuration-recorder \
  --configuration-recorder name=default,roleARN=arn:aws:iam::{{account}}:role/aws-config-role

# Step 2: Enable Config delivery channel
aws configservice put-delivery-channel \
  --delivery-channel name=default,s3BucketName=config-bucket-{{account}}

# Step 3: Start recording
aws configservice start-configuration-recorder --configuration-recorder-name default
```

**Cost**: AWS Config costs ~$0.003 per configuration item recorded. For ELB resources, this is minimal.

### AIOps Config Rules for ELB

| Rule | Description | Expected Value | Severity | Auto-Heal |
|------|-------------|---------------|----------|-----------|
| `alb-desync-mitigation-mode` | ALB desync protection | `DEFENSIVE` or `MONITOR` | HIGH | `[AUTO_HEAL]` |
| `alb-http-drop-invalid-header-enabled` | Drop invalid HTTP headers | `true` | MEDIUM | `[AUTO_HEAL]` |
| `alb-waf-enabled` | WAF association | Associated | HIGH | `[MANUAL]` |
| `elb-deletion-protection-enabled` | Deletion protection | `true` | HIGH | `[AUTO_HEAL]` |
| `elb-logging-enabled` | Access logs | `true` | MEDIUM | `[AI_ASSIST]` |
| `elb-cross-zone-load-balancing-enabled` | Cross-zone | `true` | MEDIUM | `[AUTO_HEAL]` |
| `acm-certificate-expiration-check` | Certificate expiry | > 30 days | CRITICAL | `[AI_ASSIST]` |

### Compliance Scan Script

```bash
# Full ELB compliance scan (CLI-based, no Config dependency)
for lb_arn in $(aws elbv2 describe-load-balancers --query "LoadBalancers[].LoadBalancerArn" --output text); do
  echo "=== $lb_arn ==="
  attrs=$(aws elbv2 describe-load-balancer-attributes --load-balancer-arn "$lb_arn")

  del_prot=$(echo "$attrs" | jq -r '.Attributes[] | select(.Key=="deletion_protection.enabled") | .Value')
  cross_zone=$(echo "$attrs" | jq -r '.Attributes[] | select(.Key=="load_balancing.cross_zone.enabled") | .Value')
  access_logs=$(echo "$attrs" | jq -r '.Attributes[] | select(.Key=="access_logs.s3.enabled") | .Value')

  echo "  deletion_protection: $del_prot [$([ "$del_prot" = "true" ] && echo 'OK' || echo 'FIX')]"
  echo "  cross_zone: $cross_zone [$([ "$cross_zone" = "true" ] && echo 'OK' || echo 'FIX')]"
  echo "  access_logs: $access_logs [$([ "$access_logs" = "true" ] && echo 'OK' || echo 'WARN')]"
done
```

### Drift Detection Pattern

```bash
# Capture baseline (first run)
aws elbv2 describe-load-balancer-attributes --load-balancer-arn {{lb_arn}} > /tmp/lb-baseline-{{lb_name}}.json

# Compare with current state (subsequent runs)
aws elbv2 describe-load-balancer-attributes --load-balancer-arn {{lb_arn}} > /tmp/lb-current-{{lb_name}}.json
diff /tmp/lb-baseline-{{lb_name}}.json /tmp/lb-current-{{lb_name}}.json && echo "No drift" || echo "Drift detected!"
```

---

## 3. Data Source Enablement Checklist

### Required (Free, Default ON)

- [ ] AWS CloudWatch Metrics (ALB: AWS/ApplicationELB, NLB: AWS/NetworkELB)
- [ ] AWS CloudTrail Management Events (90-day retention, free)
- [ ] AWS Service Quotas API
- [ ] EC2 Status Checks

### Recommended (Minimal Cost)

- [ ] **ALB Access Logs** → S3 bucket (for per-URL, per-target latency and error analysis)
  ```bash
  aws elbv2 modify-load-balancer-attributes --load-balancer-arn {{arn}} \
    --attributes Key=access_logs.s3.enabled,Value=true \
                 Key=access_logs.s3.bucket,Value=my-elb-logs
  ```
- [ ] **VPC Flow Logs** → CloudWatch Logs (for connection-level network diagnostics)
  ```bash
  aws ec2 create-flow-logs --resource-type VPC --resource-ids {{vpc_id}} \
    --log-group-name /aws/vpc/flow-logs --traffic-type ALL
  ```
- [ ] **AWS Config** (for compliance scanning and drift detection)
- [ ] **CloudWatch Anomaly Detection** (ML-based threshold — requires 2+ weeks data)

### Optional (Advanced)

- [ ] CloudTrail Data Events (S3 Access Logs monitoring, extra cost)
- [ ] CloudTrail Insights (anomalous API activity)
- [ ] AWS X-Ray (distributed tracing for latency decomposition)
- [ ] AWS Health Dashboard events (proactive service issue alerts)

---

## 4. Still Needs Enhancement (Gaps List)

| # | Area | Current State | Enhancement Needed | Priority |
|---|------|---------------|-------------------|----------|
| 1 | **aws-waf-ops module** | Does not exist | WAF ACL management, rate-limiting rules, DDoS mitigation (AH-08 placeholder) | P2 |
| 2 | **aws-acm-ops → ELB auto-bind** | Docs describe binding but no auto-execution | Auto-bind renewed cert to HTTPS listener without manual intervention | P2 |
| 3 | **CloudWatch dashboard templates** | Individual widget JSON in SKILL.md | Full pre-built dashboard JSON for ELB health + cost + compliance | P2 |
| 4 | **EventBridge integration** | Not documented | Trigger AIOps workflows on CloudTrail events (e.g., SG change → auto compliance check) | P2 |
| 5 | **Feedback loop automation** | Documented in principle | Implement actual feedback metrics collection (success rate tracking DB) | P3 |
| 6 | **Multi-region AIOps** | Single-region only | Cross-region LB health aggregation and failover orchestration | P3 |
| 7 | **SLA breach auto-escalation** | Not documented | Auto-create PagerDuty/Jira ticket when auto-heal fails 2x | P3 |
| 8 | **Capacity planning dashboard** | CLI FORECAST only | Grafana/CloudWatch dashboard with FORECAST + anomaly overlay | P2 |
| 9 | **aws-cost-ops integration** | Referenced but no binding | Track ELB cost breakdown per-LB per-environment | P2 |
| 10 | **Pre-commit compliance hook** | Not implemented | Git hook that runs compliance scan before allowing LB config changes | P3 |

### Enhancement Description

**P2-01: WAF Module**
- Create `aws-waf-ops` skill for Web ACL management
- Integrate with ELB for AH-08 DDoS rate limiting
- Auto-attach WAF ACL to internet-facing ALBs during compliance scan

**P2-03: Pre-built CloudWatch Dashboard**
- One-click deployment dashboard showing:
  - LB health: HealthyHostCount + UnHealthyHostCount per TG
  - Latency: p50/p90/p99 trend + anomaly band
  - Errors: 5XX rate + ELB_5XX
  - Cost: ConsumedLCUs trend + FORECAST
  - Compliance: deletion_protection + cross_zone + access_logs status

**P2-04: EventBridge Automation**
```json
{
  "eventPattern": {
    "source": ["aws.elasticloadbalancing"],
    "detail-type": ["AWS API Call via CloudTrail"],
    "detail": {
      "eventSource": ["elasticloadbalancing.amazonaws.com"],
      "eventName": ["ModifyLoadBalancerAttributes", "SetSecurityGroups"]
    }
  },
  "targets": [
    {"arn": "arn:aws:lambda:...:function:trigger-compliance-scan"}
  ]
}
```

**P2-09: Cost Breakdown**
```bash
# Per-LB cost tracking via tags
aws elbv2 describe-tags --resource-arns {{lb_arn}} \
  --query "TagDescriptions[0].Tags[?Key=='Environment'].Value"
aws ce get-cost-and-usage \
  --time-period Start=2026-05-01,End=2026-05-31
  --granularity DAILY
  --filter '{"Dimensions":{"Key":"LINKED_ACCOUNT","Values":["{{account}}"]}}'
  --metrics "UsageQuantity" "BlendedCost"
  --group-by '[{"Type":"DIMENSION","Key":"SERVICE"}]'
```