# Multi-Region AIOps — Cross-Region LB Orchestration

_Lastest update: 2026-05-31_

This document defines how to aggregate LB health, latency, and cost across multiple AWS regions for cross-region failover and global observability.

---

## Architecture

```
User → Route53 Latency-Based Routing
         ├── us-east-1 (Primary) → ALB-A → Targets
         └── eu-west-1 (Secondary) → ALB-B → Targets
              └── Health Check → failover on primary outage
```

## Cross-Region Health Aggregation

```bash
for region in us-east-1 us-west-2 eu-west-1 ap-southeast-1; do
  healthy=$(aws cloudwatch get-metric-statistics --region $region \
    --namespace AWS/ApplicationELB --metric-name HealthyHostCount \
    --statistics Minimum --period 300 --output json)
  echo "$region: $healthy"
done
```

## Cross-Region Latency Comparison

```bash
aws cloudwatch get-metric-data --metric-data-queries '[
  {"Id":"us-east-1","MetricStat":{"Metric":{"Namespace":"AWS/ApplicationELB","MetricName":"TargetResponseTime"},"Period":300,"Stat":"p99"},"Region":"us-east-1"},
  {"Id":"eu-west-1","MetricStat":{"Metric":{"Namespace":"AWS/ApplicationELB","MetricName":"TargetResponseTime"},"Period":300,"Stat":"p99"},"Region":"eu-west-1"}
]'
```

## Cross-Region Auto-Failover

Trigger: us-east-1 HealthyHostCount = 0 for 2+ consecutive periods

```
1. [aws-elb-ops] Detect primary region LB unhealthy
2. [aws-route53-ops] Update DNS weight: primary=0, secondary=100
3. [aws-cloudwatch-ops] Verify secondary LB handling traffic
4. [aws-waf-ops] Ensure WAF ACL replicated in secondary region
5. [aws-acm-ops] Verify certificates valid in secondary region
6. Notify: "Failover to eu-west-1 complete. Monitor before rollback"
```

## Cross-Region Cost Comparison

```bash
aws ce get-cost-and-usage --time-period Start=2026-05-01,End=2026-05-31 \
  --granularity MONTHLY --metrics UnblendedCost \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon Elastic Load Balancing"]}}' \
  --group-by '[{"Type":"DIMENSION","Key":"REGION"}]'
```