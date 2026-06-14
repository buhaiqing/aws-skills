# Detection Rules Library

## 1. Rule Schema

Every detection rule follows this tuple:

```yaml
rule:
  id: <CODE-NN>                     # unique stable ID
  domain: <fault | predictive | cost | security | change>
  name: <short human name>
  description: <one-line>
  signal_source: <cw-metric | cw-anomaly | log-insight | cloudtrail
                  | config-rule | cost-explorer | guardduty | securityhub
                  | acm | service-quota | custom>
  metric_or_event: <path>
  condition: <comparison expression>
  window: <ISO-8601 duration, e.g., PT5M, PT1H, P7D>
  baseline: <static | adaptive:30d | seasonal:weekly>
  default_severity: <info | low | medium | high | critical>
  default_decision: <AUTO_HEAL | AI_ASSIST | MANUAL>
  applies_to: [<resource type filter>]
  false_positive_notes: <free text>
```

## 2. Fault Detection (FD)

### FD-01 — Target health flapping (LB)

- **domain**: fault
- **signal_source**: cw-metric
- **metric_or_event**: `AWS/ApplicationELB.UnHealthyHostCount`
- **condition**: state changes ≥ 3 within window
- **window**: PT5M
- **baseline**: static (configurable per TG)
- **default_severity**: high
- **default_decision**: AUTO_HEAL (deregister + new instance via ASG)
- **applies_to**: ALB target groups
- **false_positive_notes**: app deploy with rolling restart; correlate
  with CodeDeploy / ECS events before triggering.

### FD-02 — Latency spike (ALB/NLB)

- **domain**: fault
- **signal_source**: cw-metric
- **metric_or_event**: `AWS/ApplicationELB.TargetResponseTime` (p99)
- **condition**: p99 > adaptive_baseline * 2.0
- **window**: PT15M
- **baseline**: adaptive:30d
- **default_severity**: medium
- **default_decision**: AI_ASSIST
- **applies_to**: ALB
- **false_positive_notes**: cache cold start, scheduled batch jobs.

### FD-03 — 5xx error surge (ALB)

- **domain**: fault
- **signal_source**: cw-metric
- **metric_or_event**: `AWS/ApplicationELB.HTTPCode_Target_5XX_Count`
- **condition**: rate > 1% of total requests
- **window**: PT5M
- **baseline**: adaptive:30d
- **default_severity**: critical
- **default_decision**: AUTO_HEAL (drain unhealthy, scale out) — but
  see FD-10 (if ALL targets unhealthy, downgrade to AI_ASSIST)
- **applies_to**: ALB
- **false_positive_notes**: deployment in progress; check CodeDeploy stage.

### FD-04 — Connection exhaustion (NLB)

- **domain**: fault
- **signal_source**: cw-metric
- **metric_or_event**: `AWS/NetworkELB.ActiveFlowCount` / `TCP_ELB_Reset_Count`
- **condition**: ActiveFlowCount > 80% of TG's instance limit
- **window**: PT10M
- **baseline**: static
- **default_severity**: high
- **default_decision**: AI_ASSIST (scale out, or fix keep-alive)
- **applies_to**: NLB

### FD-05 — Cross-AZ imbalance (ALB)

- **domain**: fault
- **signal_source**: cw-metric
- **metric_or_event**: `AWS/ApplicationELB.RequestCount` per AZ
- **condition**: max(AZ_requests) / mean(AZ_requests) > 1.5
- **window**: PT30M
- **baseline**: static
- **default_severity**: medium
- **default_decision**: AI_ASSIST (enable cross-zone LB)
- **applies_to**: ALB

### FD-06 — EC2 status check failure

- **domain**: fault
- **signal_source**: cw-metric
- **metric_or_event**: `AWS/EC2.StatusCheckFailed`
- **condition**: any value > 0
- **window**: PT5M
- **baseline**: static
- **default_severity**: high
- **default_decision**: AUTO_HEAL (reboot if System check; replace if
  Instance check)
- **applies_to**: EC2 instances
- **false_positive_notes**: AWS-initiated maintenance — verify with
  AWS Health Dashboard before reboot.

### FD-07 — EC2 CPU saturation

- **domain**: fault
- **signal_source**: cw-metric
- **metric_or_event**: `AWS/EC2.CPUUtilization`
- **condition**: avg > 90% sustained
- **window**: PT15M
- **baseline**: adaptive:30d
- **default_severity**: high
- **default_decision**: AI_ASSIST (scale out or resize)
- **applies_to**: EC2 instances
- **false_positive_notes**: Transient spike during batch jobs; correlate with ASG scaling events.

### FD-07a — EC2 memory pressure

- **domain**: fault
- **signal_source**: cw-metric
- **metric_or_event**: `CWAgent.Memory % Used` (custom metric via CloudWatch Agent)
- **condition**: avg > 85% sustained
- **window**: PT15M
- **baseline**: adaptive:30d
- **default_severity**: high
- **default_decision**: AI_ASSIST (identify leak or resize)
- **applies_to**: EC2 instances with CloudWatch Agent installed
- **false_positive_notes**: Requires CW Agent with memory metrics. Verify agent via SSM before resize.

### FD-07b — EC2 EBS IOPS saturation

- **domain**: fault
- **signal_source**: cw-metric
- **metric_or_event**: `AWS/EBS.VolumeQueueLength`
- **condition**: avg > 64 sustained
- **window**: PT10M
- **baseline**: adaptive:30d
- **default_severity**: high
- **default_decision**: AI_ASSIST (upgrade EBS type or add IOPS)
- **applies_to**: EC2 instances with EBS volumes
- **false_positive_notes**: Transient burst I/O on gp3/io2 baseline; correlate with BurstBalance.

### FD-07c — EC2 EBS throughput exhaustion

- **domain**: fault
- **signal_source**: cw-metric
- **metric_or_event**: `AWS/EBS.BurstBalance`
- **condition**: < 20%
- **window**: PT10M
- **baseline**: static
- **default_severity**: high
- **default_decision**: AI_ASSIST (upgrade to io1/io2/gp3 with provisioned throughput)
- **applies_to**: EC2 instances with gp2/st1/sc1 volumes
- **false_positive_notes**: gp3/io2 with provisioned throughput do not use burst balance.

### FD-07d — EC2 EBS read/write latency

- **domain**: fault
- **signal_source**: cw-metric
- **metric_or_event**: `AWS/EBS.ReadLatency` / `AWS/EBS.WriteLatency`
- **condition**: p95 > 20ms sustained
- **window**: PT15M
- **baseline**: adaptive:30d
- **default_severity**: medium
- **default_decision**: AI_ASSIST (investigate EBS type, queue depth, or instance EBS bandwidth)
- **applies_to**: EC2 instances with EBS volumes
- **false_positive_notes**: Transient spikes during snapshot creation; correlate with VolumeQueueLength.

### FD-07e — EC2 network bandwidth saturation

- **domain**: fault
- **signal_source**: cw-metric
- **metric_or_event**: `AWS/EC2.NetworkIn` / `AWS/EC2.NetworkOut`
- **condition**: avg > 80% of instance type network limit
- **window**: PT15M
- **baseline**: adaptive:30d
- **default_severity**: high
- **default_decision**: AI_ASSIST (resize to higher network capacity instance type)
- **applies_to**: EC2 instances
- **false_positive_notes**: Network limit varies by instance type. Fetch via `describe-instance-types`.

### FD-07f — EC2 network packet drops

- **domain**: fault
- **signal_source**: cw-metric
- **metric_or_event**: `AWS/EC2.NetworkPacketsIn` / `AWS/EC2.NetworkPacketsOut`
- **condition**: drop rate > 1% (requires VPC Flow Logs or agent-level metrics)
- **window**: PT15M
- **baseline**: adaptive:30d
- **default_severity**: medium
- **default_decision**: AI_ASSIST (check ENI limits, SG rules, or instance network driver)
- **applies_to**: EC2 instances
- **false_positive_notes**: Packet drops can be legitimate (ICMP reject, firewall). Correlate with Flow Logs.

### FD-08 — RDS high CPU / connections

- **domain**: fault
- **signal_source**: cw-metric
- **metric_or_event**: `AWS/RDS.CPUUtilization` or `DatabaseConnections`
- **condition**: > 85% of `max_connections` (PG/MySQL) or CPU > 90%
- **window**: PT10M
- **baseline**: adaptive:30d
- **default_severity**: high
- **default_decision**: AI_ASSIST

### FD-09 — RDS replication lag

- **domain**: fault
- **signal_source**: cw-metric
- **metric_or_event**: `AWS/RDS.ReplicaLag`
- **condition**: > 30s
- **window**: PT10M
- **baseline**: static
- **default_severity**: medium
- **default_decision**: AI_ASSIST
- **applies_to**: RDS read replicas (non-Aurora). Aurora → **FD-15**.

### FD-15 — Aurora replica lag

- **domain**: fault
- **signal_source**: cw-metric
- **metric_or_event**: `AWS/RDS.AuroraReplicaLag`
- **dimensions**: `DBClusterIdentifier`
- **condition**: > {{user.replica_lag_threshold_ms}} (default 1000ms)
- **window**: PT15M
- **baseline**: static
- **default_severity**: high
- **default_decision**: AI_ASSIST
- **runbook**: RB-023

### FD-16 — Aurora writer unhealthy

- **domain**: fault
- **signal_source**: rds-api + cw-metric
- **metric_or_event**: writer `DBInstanceStatus` != `available` OR cluster `Status` != `available`
- **window**: PT5M
- **default_severity**: critical
- **default_decision**: MANUAL
- **runbook**: RB-025

### FD-10 — ALL targets unhealthy

- **domain**: fault
- **signal_source**: derived
- **condition**: `UnHealthyHostCount == RegisteredTargets AND > 0`
- **window**: PT2M
- **baseline**: static
- **default_severity**: critical
- **default_decision**: **AI_ASSIST** (forced downgrade from AUTO_HEAL
  per README §Auto-Heal Boundary Conditions — may indicate app outage
  rather than infra issue)
- **applies_to**: ALB

### FD-11 — Lambda throttling

- **domain**: fault
- **signal_source**: cw-metric
- **metric_or_event**: `AWS/Lambda.Throttles`
- **condition**: any value > 0
- **window**: PT5M
- **default_severity**: high
- **default_decision**: AI_ASSIST (raise concurrency)

### FD-12 — Lambda iterator age (stream sources)

- **domain**: fault
- **signal_source**: cw-metric
- **metric_or_event**: `AWS/Lambda.IteratorAge`
- **condition**: > 60s
- **window**: PT10M
- **default_severity**: high
- **default_decision**: AI_ASSIST

### FD-13 — NAT GW packet drop

- **domain**: fault
- **signal_source**: cw-metric
- **metric_or_event**: `AWS/NATGateway.PacketsDropCount`
- **condition**: rate > 0
- **window**: PT10M
- **default_severity**: high
- **default_decision**: AI_ASSIST (split NAT GWs across AZs)

### FD-14 — OpenSearch cluster red

- **domain**: fault
- **signal_source**: cw-metric
- **metric_or_event**: `AWS/ES.ClusterStatus.red`
- **condition**: any value > 0
- **window**: PT2M
- **default_severity**: critical
- **default_decision**: AI_ASSIST

## 3. Predictive Analysis (PD)

### PD-01 — Cert expiry (30/14/7 day warnings)

- **domain**: predictive
- **signal_source**: acm
- **metric_or_event**: `NotAfter`
- **condition**: days_remaining ≤ {30, 14, 7}
- **default_severity**: low (30d) / medium (14d) / high (7d)
- **default_decision**: AUTO_HEAL (renew + validate)
- **applies_to**: ACM certificates in use

### PD-02 — EBS volume > 85% full

- **domain**: predictive
- **signal_source**: cw-metric
- **metric_or_event**: `AWS/EBS.VolumeQueueLength` no, use
  `disk_used_percent` from CW Agent
- **condition**: > 85%
- **window**: PT1H
- **default_severity**: medium
- **default_decision**: AI_ASSIST (resize or clean up)

### PD-03 — RDS storage < 10% free

- **domain**: predictive
- **signal_source**: cw-metric
- **metric_or_event**: `AWS/RDS.FreeStorageSpace`
- **condition**: < 10% of allocated
- **window**: PT1H
- **default_severity**: high
- **default_decision**: AI_ASSIST (enable storage autoscaling or grow)

### PD-04 — RDS connections approaching max

- **domain**: predictive
- **signal_source**: cw-metric
- **metric_or_event**: `AWS/RDS.DatabaseConnections`
- **condition**: > 80% of engine max
- **window**: PT30M
- **default_severity**: high
- **default_decision**: AI_ASSIST
- **note**: Aurora cluster behind proxy → delegate **`aws-aurora-ops`** (RB-027)

### PD-08 — Aurora Serverless v2 at capacity ceiling

- **domain**: predictive
- **signal_source**: cw-metric
- **metric_or_event**: `AWS/RDS.ServerlessDatabaseCapacity`
- **condition**: ≥ 90% of configured MaxCapacity
- **window**: PT15M
- **default_severity**: high
- **default_decision**: AUTO_HEAL
- **runbook**: RB-024

### PD-09 — Aurora Global DB replication lag

- **domain**: predictive
- **signal_source**: cw-metric
- **metric_or_event**: `AWS/RDS.AuroraGlobalDBReplicationLag`
- **condition**: > 1000ms sustained
- **window**: PT30M
- **default_severity**: high
- **default_decision**: MANUAL
- **runbook**: RB-026

### PD-05 — LCU saturation forecast (ALB)

- **domain**: predictive
- **signal_source**: cw-forecast
- **metric_or_event**: `AWS/ApplicationELB.ConsumedLCUs`
- **condition**: forecast in 7d > 90% of LCU reservation
- **window**: P7D forecast
- **default_severity**: medium
- **default_decision**: AI_ASSIST (request quota increase or scale down)

### PD-06 — Quota exhaustion (Service Quotas)

- **domain**: predictive
- **signal_source**: service-quota + trend
- **condition**: usage > 80% of quota AND trend is upward
- **default_severity**: medium
- **default_decision**: AI_ASSIST (request quota increase)

### PD-07 — Cost overrun forecast

- **domain**: predictive
- **signal_source**: cost-explorer
- **condition**: forecast next 30d > 1.2 * current month-to-date
- **default_severity**: medium
- **default_decision**: MANUAL (recommend cost review)

## 4. Cost Optimization (CO)

### CO-01 — Idle ALB

- **domain**: cost
- **signal_source**: cw-metric
- **metric_or_event**: `AWS/ApplicationELB.ConsumedLCUs` avg over 14d
- **condition**: < 0.05
- **default_severity**: low
- **default_decision**: MANUAL (recommend delete)

### CO-02 — Idle NLB

- **domain**: cost
- **signal_source**: cw-metric
- **metric_or_event**: `AWS/NetworkELB.ProcessedBytes` avg over 14d
- **condition**: < 1 KB/s
- **default_severity**: low
- **default_decision**: MANUAL

### CO-03 — Idle NAT Gateway

- **domain**: cost
- **signal_source**: cw-metric
- **metric_or_event**: `AWS/NATGateway.BytesOutToDestination` sum over 30d
- **condition**: < 1 GB total
- **default_severity**: low
- **default_decision**: MANUAL

### CO-04 — Unattached EBS volume

- **domain**: cost
- **signal_source**: ec2 describe
- **condition**: state == `available` for > 7 days
- **default_severity**: low
- **default_decision**: MANUAL (snapshot + delete)

### CO-05 — Unassociated Elastic IP

- **domain**: cost
- **signal_source**: ec2 describe
- **condition**: not associated for > 24h
- **default_severity**: low
- **default_decision**: MANUAL

### CO-06 — S3 bucket without lifecycle rule

- **domain**: cost
- **signal_source**: s3 describe
- **condition**: no lifecycle config AND bucket age > 90d AND size > 100 GB
- **default_severity**: low
- **default_decision**: MANUAL

### CO-07 — RDS over-provisioned

- **domain**: cost
- **signal_source**: cw-metric + compute-optimizer
- **metric_or_event**: `AWS/RDS.CPUUtilization` avg over 14d
- **condition**: < 10%
- **default_severity**: low
- **default_decision**: MANUAL (recommend downsizing per Compute Optimizer)

### CO-08 — EC2 rightsizing recommendation

- **domain**: cost
- **signal_source**: compute-optimizer
- **condition**: `Finding` == `OVER_PROVISIONED` with savings > $20/mo
- **default_severity**: low
- **default_decision**: MANUAL

### CO-09 — Cost anomaly (sudden spike)

- **domain**: cost
- **signal_source**: cost-explorer anomaly detection
- **condition**: anomaly score > 80 AND impact > $100/day
- **default_severity**: high
- **default_decision**: MANUAL (require human investigation; cost
  alerts aren't safe to auto-remediate)

## 5. Security Detection (SD)

### SD-01 — GuardDuty CRITICAL finding

- **domain**: security
- **signal_source**: guardduty
- **condition**: severity >= 7.0 AND not archived
- **default_severity**: critical
- **default_decision**: MANUAL (security findings → human review;
  legal/compliance implications)

### SD-02 — S3 bucket public

- **domain**: security
- **signal_source**: s3 describe + config rule
- **condition**: `PublicAccessBlockConfiguration` not fully on
- **default_severity**: high
- **default_decision**: AI_ASSIST (enable Block Public Access)

### SD-03 — Security group 0.0.0.0/0 ingress

- **domain**: security
- **signal_source**: ec2 describe + config rule
- **condition**: SG has rule with `CidrIp == 0.0.0.0/0` AND port in
  {22, 3389, 3306, 5432, 6379, 27017}
- **default_severity**: critical
- **default_decision**: MANUAL (revoking open ingress is risky)

### SD-04 — IAM credential leaked (via GuardDuty)

- **domain**: security
- **signal_source**: guardduty finding type `CredentialAccess`
- **default_severity**: critical
- **default_decision**: MANUAL (rotate keys + investigate)

### SD-05 — KMS key scheduled for deletion

- **domain**: security
- **signal_source**: kms describe
- **condition**: `KeyState == PendingDeletion`
- **default_severity**: medium
- **default_decision**: MANUAL (cancel deletion if unexpected)

### SD-06 — Security Hub score drop

- **domain**: security
- **signal_source**: securityhub
- **condition**: score delta > 5% week-over-week
- **default_severity**: medium
- **default_decision**: MANUAL

### SD-07 — Root account usage

- **domain**: security
- **signal_source**: cloudtrail
- **condition**: any `userIdentity.type == Root` event
- **default_severity**: critical
- **default_decision**: MANUAL

## 6. Change Detection (CD)

### CD-01 — Security group drift

- **domain**: change
- **signal_source**: config rule
- **condition**: SG rules differ from last approved baseline
- **default_severity**: medium
- **default_decision**: AI_ASSIST (diff + option to revert)

### CD-02 — IAM policy attachment unexpected

- **domain**: change
- **signal_source**: cloudtrail
- **condition**: `AttachUserPolicy` / `AttachRolePolicy` event by
  non-admin principal
- **default_severity**: high
- **default_decision**: MANUAL

### CD-03 — Tag mutation outside change window

- **domain**: change
- **signal_source**: cloudtrail
- **condition**: `TagResource` event on prod-tagged resource outside
  configured change window
- **default_severity**: medium
- **default_decision**: AI_ASSIST

### CD-04 — RDS deletion outside change window

- **domain**: change
- **signal_source**: cloudtrail
- **condition**: `DeleteDBInstance` event on prod-tagged RDS
- **default_severity**: critical
- **default_decision**: MANUAL

### CD-05 — Pre-change baseline capture

- **domain**: change
- **signal_source**: orchestrated
- **condition**: triggered by orchestrator before any write
- **default_severity**: n/a
- **default_decision**: n/a (this is a guard, not a detection)

## 7. Threshold Calibration

### Baseline computation

- First scan of a resource: collect 30 days of historical metrics
  (`get-metric-statistics --start-time -30d --end-time now`).
- Compute baseline per (metric, hour-of-day, day-of-week) bucket.
- Cache baseline in orchestrator state (`aiops_baselines` table).

### Adaptive threshold

- For each new data point: compare to baseline bucket.
- Anomaly = |value − baseline| > N * stddev (N defaults to 2.5, configurable).
- Suppress detection if value falls within baseline variance but is
  still flagged by static threshold (avoid alert storms).

### Threshold overrides

Users can override any rule's threshold at runtime:

```
{{u.threshold_overrides}}:
  FD-03:
    rate_threshold: 0.5%   # was 1%
    decision: AI_ASSIST    # was AUTO_HEAL
```

## 8. Rule Implementation Status

| Domain | Rules | Implementation |
|--------|-------|----------------|
| Fault Detection | 14 | All baseline — Layer 2 |
| Predictive | 7 | All baseline — Layer 2 |
| Cost Optimization | 9 | Mostly recommend-only (MANUAL/AI_ASSIST) |
| Security | 7 | Detection only — MANUAL on confirm |
| Change | 5 | Detection + audit trail |

Rules marked **baseline** work with default thresholds. Rules with
**adaptive:30d** need at least 30 days of history before they produce
reliable detections; before that, they fall back to static thresholds.