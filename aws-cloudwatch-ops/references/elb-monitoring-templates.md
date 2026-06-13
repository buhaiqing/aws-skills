# ELB Monitoring Templates — CloudWatch

_Latest update: 2026-06-13_

ELB-specific alarm and dashboard templates. **Pre-flight**: delegate to `aws-elb-ops` for LB/TG ARNs and health context before creating alarms here.

> **Bidirectional link**: [SKILL.md](../SKILL.md) → `## Scope` · [operation-index.md](operation-index.md)
> **Asset**: [assets/elb-aiops-dashboard.json](../assets/elb-aiops-dashboard.json) — 8-widget AIOps dashboard (health, latency, errors, traffic, LCU, WAF, NAT)

---

## Anomaly Detection — ALB Request Count

```bash
# Pre-flight: verify ≥ 2 weeks metric data
aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB --metric-name RequestCount \
  --statistics Sum --period 3600 \
  --dimensions Name=LoadBalancer,Value={{lb_arn}} \
  --start-time $(date -d '-30 days' -u +%Y-%m-%dT%H:%M:%SZ) --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --region {{user.region}} --output json | jq '.Datapoints | length'
```

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "{{lb_name}}-RequestCount-Anomaly" \
  --alarm-description "AIOps: Seasonal anomaly detection for ALB request count" \
  --metrics '[{"Id":"m1","MetricStat":{"Metric":{"Namespace":"AWS/ApplicationELB","MetricName":"RequestCount","Dimensions":[{"Name":"LoadBalancer","Value":"{{lb_arn}}"}]},"Period":300,"Stat":"Sum"}},{"Id":"ad","Expression":"ANOMALY_DETECTION_BAND(m1,2)"}]' \
  --threshold-metric-id "ad" \
  --comparison-operator "LessThanLowerOrGreaterThanUpperThreshold" \
  --evaluation-periods 2 \
  --alarm-actions "{{sns_arn}}" \
  --region {{user.region}} --output json
```

## Latency Alarm (p99)

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "{{lb_name}}-p99-Latency-High" \
  --alarm-description "AIOps: p99 latency exceeds 1000ms for 3 consecutive periods" \
  --namespace AWS/ApplicationELB \
  --metric-name TargetResponseTime \
  --dimensions Name=LoadBalancer,Value={{lb_arn}} \
  --statistic p99 --period 60 \
  --threshold 1000 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 3 \
  --alarm-actions "{{sns_arn}}" \
  --region {{user.region}} --output json
```

## Health Composite Alarm (ELB)

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "{{lb_name}}-HealthyHosts-Low" \
  --namespace AWS/ApplicationELB \
  --metric-name HealthyHostCount \
  --dimensions Name=TargetGroup,Value={{tg_arn}} \
  --statistic Minimum --period 60 \
  --threshold {{min_healthy}} \
  --comparison-operator LessThanThreshold \
  --evaluation-periods 2 \
  --region {{user.region}} --output json

aws cloudwatch put-metric-alarm \
  --alarm-name "{{lb_name}}-5XX-Errors" \
  --namespace AWS/ApplicationELB \
  --metric-name HTTPCode_Target_5XX \
  --dimensions Name=LoadBalancer,Value={{lb_arn}} \
  --statistic Sum --period 60 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --region {{user.region}} --output json

aws cloudwatch put-composite-alarm \
  --alarm-name "{{lb_name}}-Backend-Health-Composite" \
  --alarm-rule '(ALARM("{{lb_name}}-HealthyHosts-Low") OR ALARM("{{lb_name}}-5XX-Errors"))' \
  --alarm-actions "{{sns_arn}}" \
  --region {{user.region}} --output json
```

## ELB Health Dashboard Widget

```json
{
  "type": "metric",
  "properties": {
    "metrics": [
      ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", "{{lb_arn}}", {"stat": "p99"}],
      ["AWS/ApplicationELB", "HealthyHostCount", "TargetGroup", "{{tg_arn}}", {"stat": "Minimum"}],
      ["AWS/ApplicationELB", "HTTPCode_Target_5XX", "LoadBalancer", "{{lb_arn}}", {"stat": "Sum"}],
      [".", "RequestCount", ".", ".", {"stat": "Sum"}],
      ["AWS/ApplicationELB", "ActiveConnectionCount", "LoadBalancer", "{{lb_arn}}", {"stat": "Average"}]
    ],
    "period": 300,
    "stat": "Average",
    "region": "{{user.region}}",
    "title": "{{lb_name}} — Real-Time Health"
  }
}
```

## FORECAST — ELB Capacity Planning

```bash
aws cloudwatch get-metric-data \
  --metric-data-queries '[
    {"Id":"m1","MetricStat":{"Metric":{"Namespace":"AWS/ApplicationELB","MetricName":"ActiveConnectionCount","Dimensions":[{"Name":"LoadBalancer","Value":"{{lb_arn}}"}]},"Period":3600,"Stat":"Maximum"},"Label":"ActiveConnections"},
    {"Id":"fc","Expression":"FORECAST(m1, \"linear\", 168)","Label":"7-Day Forecast"}
  ]' \
  --start-time "$(date -d '-14 days' -u +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --region {{user.region}} --output json
```

## Cross-Module — ELB → EC2 Latency Correlation

```json
{
  "type": "metric",
  "properties": {
    "metrics": [
      ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", "{{lb_arn}}", {"stat": "p99", "label": "ALB Latency"}],
      ["AWS/EC2", "CPUUtilization", "InstanceId", "{{instance_id}}", {"stat": "Average", "label": "EC2 CPU", "yAxis": "right"}],
      ["AWS/EC2", "NetworkIn", "InstanceId", "{{instance_id}}", {"stat": "Average", "yAxis": "right"}]
    ],
    "period": 300,
    "title": "Latency Correlation: ELB → Backend EC2"
  }
}
```

## Full Dashboard from Asset

```bash
# Substitute {{lb_arn}}, {{tg_arn}}, {{lb_name}}, {{region}}, {{nat_gw_id}} then:
aws cloudwatch put-dashboard \
  --dashboard-name "ELB-AIOps-{{lb_name}}" \
  --dashboard-body file://assets/elb-aiops-dashboard.json \
  --region {{user.region}} --output json
```

Metric mapping and recommended alarm set: [core-concepts.md §ELB AIOps Metrics](core-concepts.md#elb-aiops-metrics-reference).
