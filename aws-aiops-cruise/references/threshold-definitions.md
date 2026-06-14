# Threshold Definitions — AWS AIOps Cruise

> Default Warning (W) / Critical (C) thresholds. Override via runbook args when documented.
> Thresholds below are per-service; see `inference-rules.md` for cross-signal chain patterns.

## EC2 (`AWS/EC2`)

| Metric | W | C |
|--------|---|---|
| CPUUtilization | 70 | 85 |
| StatusCheckFailed | 0.5 | 1 |
| Memory % Used (CW Agent) | 80 | 90 |
| NetworkIn / NetworkOut (% of type limit) | 70 | 85 |
| NetworkPacketsIn/Out drop rate | 0.5% | 1% |

## EBS (`AWS/EBS`)

| Metric | W | C |
|--------|---|---|
| VolumeQueueLength | 32 | 64 |
| BurstBalance (%) | 50 | 20 |
| ReadLatency / WriteLatency (ms, p95) | 15 | 25 |
| VolumeReadOps / VolumeWriteOps (% of IOPS) | 70 | 85 |

## Application Load Balancer (`AWS/ApplicationELB`)

| Metric | W | C |
|--------|---|---|
| UnHealthyHostCount | 1 | 3 |
| TargetResponseTime (s) | 1.0 | 3.0 |
| HTTPCode_Target_5XX_Count (sum/5m) | 10 | 50 |

## RDS (`AWS/RDS`)

| Metric | W | C |
|--------|---|---|
| CPUUtilization | 75 | 85 |
| DatabaseConnections | 70% of max | 85% of max |
| FreeStorageSpace (bytes) | 5 GB | 2 GB |
| ReadLatency / WriteLatency (ms) | 20 | 100 |

## ElastiCache (`AWS/ElastiCache`)

| Metric | W | C |
|--------|---|---|
| CPUUtilization | 70 | 85 |
| DatabaseMemoryUsagePercentage | 75 | 90 |
| CurrConnections | 70% max | 85% max |

## NAT Gateway (`AWS/NATGateway`)

| Metric | W | C |
|--------|---|---|
| ActiveConnectionCount | 70% spec | 85% spec |
| ErrorPortAllocation | 0 | 1 |

## Security (rule-based, no CloudWatch)

| Check | Level |
|-------|-------|
| SG 0.0.0.0/0 on 22, 3389, 3306, 5432, 6379 | CRITICAL |
| GuardDuty HIGH/CRITICAL unarchived | CRITICAL |
| ACM cert expires < 30 days | WARNING |

Fetch instance max connections from `describe-db-instances` / parameter groups when available; do not hardcode engine limits in SKILL.md (TE-1).
