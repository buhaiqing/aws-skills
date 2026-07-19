# Capacity Forecast Rules

> 14-day trend prediction rules for proactive capacity management.

## Rule Index

| Rule ID | Service | Metric | Warning Threshold | Critical Threshold | Action |
|---------|---------|--------|-------------------|-------------------|--------|
| CAP-FC-01 | EC2 | CPUUtilization | 7d avg > 70% | 7d avg > 85% | Proactive resize to larger instance type |
| CAP-FC-02 | ECS | CPUUtilization | cluster avg > 70% | cluster avg > 85% | Scale out ASG |
| CAP-FC-03 | RDS | DatabaseConnections | > 80% of max_conn | > 95% of max_conn | Scale DB instance class |
| CAP-FC-04 | ElastiCache | DatabaseMemoryUsagePercentage | > 75% | > 90% | Scale cluster or add replica |
| CAP-FC-05 | ALB | ActiveConnectionCount | 7d trend + 30% of capacity | > 80% of capacity | Scale ASG or enable connection draining |
| CAP-FC-06 | Lambda | ProvisionedConcurrencyUtilization | > 70% | > 90% | Increase provisioned concurrency |

## Rule Detail

### CAP-FC-01: EC2 CPUUtilization

**Namespace**: `AWS/EC2`
**Metric**: `CPUUtilization`
**Period**: 3600 (1 hour)
**History**: 14 days minimum

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value={{instance_id}} \
  --statistics Average \
  --period 3600 \
  --start-time $(date -d '-14 days' -u +%Y-%m-%dT00:00:00Z) \
  --end-time $(date -u +%Y-%m-%dT00:00:00Z) \
  --region {{user.region}} --output json
```

**Alert Levels**:
- `WARNING`: 7-day forecast average > 70%
- `CRITICAL`: 7-day forecast average > 85%

**Recommendation Templates**:
- WARNING → `Proactive resize: consider upgrading to {{next_instance_type}}`
- CRITICAL → `Immediate action: current instance type insufficient for projected load`

---

### CAP-FC-02: ECS CPUUtilization

**Namespace**: `AWS/ECS`
**Metric**: `CPUUtilization`
**Period**: 300 (5 minutes)
**History**: 14 days minimum
**Dimensions**: `ClusterName`, `ServiceName`

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ClusterName,Value={{cluster_name}} \
  --statistics Average \
  --period 300 \
  --start-time $(date -d '-14 days' -u +%Y-%m-%dT00:00:00Z) \
  --end-time $(date -u +%Y-%m-%dT00:00:00Z) \
  --region {{user.region}} --output json
```

**Alert Levels**:
- `WARNING`: cluster average > 70%
- `CRITICAL`: cluster average > 85%

**Recommendation**: Scale out ASG — `aws autoscaling set-desired-capacity --desired-capacity <N>`

---

### CAP-FC-03: RDS DatabaseConnections

**Namespace**: `AWS/RDS`
**Metric**: `DatabaseConnections`
**Period**: 300 (5 minutes)
**History**: 14 days minimum
**Dimensions**: `DBInstanceIdentifier`

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name DatabaseConnections \
  --dimensions Name=DBInstanceIdentifier,Value={{db_instance_id}} \
  --statistics Average \
  --period 300 \
  --start-time $(date -d '-14 days' -u +%Y-%m-%dT00:00:00Z) \
  --end-time $(date -u +%Y-%m-%dT00:00:00Z) \
  --region {{user.region}} --output json
```

**Alert Levels** (relative to `max_connections`):
- `WARNING`: forecast > 80% of `max_connections`
- `CRITICAL`: forecast > 95% of `max_connections`

**Recommendation**: Scale DB instance or enable RDS Proxy to pool connections

---

### CAP-FC-04: ElastiCache DatabaseMemoryUsagePercentage

**Namespace**: `AWS/ElastiCache`
**Metric**: `DatabaseMemoryUsagePercentage`
**Period**: 300 (5 minutes)
**History**: 14 days minimum
**Dimensions**: `ReplicationGroupId`, `ClusterId`

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/ElastiCache \
  --metric-name DatabaseMemoryUsagePercentage \
  --dimensions Name=ReplicationGroupId,Value={{replication_group_id}} \
  --statistics Average \
  --period 300 \
  --start-time $(date -d '-14 days' -u +%Y-%m-%dT00:00:00Z) \
  --end-time $(date -u +%Y-%m-%dT00:00:00Z) \
  --region {{user.region}} --output json
```

**Alert Levels**:
- `WARNING`: > 75%
- `CRITICAL`: > 90%

**Recommendation**: Scale cluster node type or add replica nodes

---

### CAP-FC-05: ALB ActiveConnectionCount

**Namespace**: `AWS/ApplicationELB`
**Metric**: `ActiveConnectionCount`
**Period**: 60 (1 minute)
**History**: 14 days minimum
**Dimensions**: `LoadBalancer`, `TargetGroup`

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name ActiveConnectionCount \
  --dimensions Name=LoadBalancer,Value={{alb_arn}} \
  --statistics Average \
  --period 60 \
  --start-time $(date -d '-14 days' -u +%Y-%m-%dT00:00:00Z) \
  --end-time $(date -u +%Y-%m-%dT00:00:00Z) \
  --region {{user.region}} --output json
```

**Alert Levels**:
- `WARNING`: 7-day trend shows +30% of current capacity
- `CRITICAL`: projected > 80% of ALB connection limit

**Recommendation**: Scale ASG behind ALB or enable connection draining

---

### CAP-FC-06: Lambda ProvisionedConcurrencyUtilization

**Namespace**: `AWS/Lambda`
**Metric**: `ProvisionedConcurrencyUtilization`
**Period**: 60 (1 minute)
**History**: 7 days minimum (Lambda metrics have shorter retention)
**Dimensions**: `FunctionName`

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name ProvisionedConcurrencyUtilization \
  --dimensions Name=FunctionName,Value={{function_name}} \
  --statistics Average \
  --period 60 \
  --start-time $(date -d '-7 days' -u +%Y-%m-%dT00:00:00Z) \
  --end-time $(date -u +%Y-%m-%dT00:00:00Z) \
  --region {{user.region}} --output json
```

**Alert Levels**:
- `WARNING`: > 70%
- `CRITICAL`: > 90%

**Recommendation**: Increase provisioned concurrency allocation

---

## Confidence Scoring

| Data Points | Confidence |
|-------------|------------|
| ≥ 336 (14 days × 24h) | high |
| ≥ 168 (7 days × 24h) | medium |
| < 168 | low |

## Forecast Algorithm

Linear regression on hourly averages from 14-day history.
See `scripts/capacity_forecast.py` — `predict_capacity()` function.
