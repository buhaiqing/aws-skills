# AWS-Native Inference Rules — aws-aiops-cruise

> Chain patterns using **AWS product combinations**, not Aliyun equivalents.

## Edge: Route53 → CloudFront → WAF → ALB

### R53-ALB-01: Health check failing, ALB targets healthy

| Symptoms | Route53 HC failure + ALB UnHealthyHostCount = 0 |
| Inference | DNS mispoint, cert mismatch on CloudFront, or regional endpoint issue |
| Fix path | `route53 list-resource-record-sets`; verify alias to ALB; ACM on listener |

### WAF-ALB-01: WAF blocks spike + ALB 403/502 pattern

| Symptoms | WAF `BlockedRequests` high; client sees 403 |
| Inference | Rate rule / geo block / false positive on API path |
| Fix path | `wafv2 get-sampled-requests`; tune rule; aws-waf-ops |

### CF-EDGE-01 / CF-ORIGIN-01

| Symptoms | CloudFront `5xxErrorRate` or `OriginLatency` elevated |
| Inference | Origin (ALB/API/S3) unhealthy vs edge cache issue |
| Metrics | Namespace `AWS/CloudFront`, dim `DistributionId` + `Region=Global` |

### CF-ALB-01 (composite)

CloudFront origin latency + ALB `TargetResponseTime` / 5xx → fix origin path first.

### CF-S3-01 / S3-PAB-01

| Symptoms | S3 origin without OAC/OAI; incomplete Block Public Access on bucket |
| Inference | CloudFront 403/502 on static assets; direct S3 exposure risk |
| Fix path | Attach OAC; bucket policy `cloudfront.amazonaws.com`; enable full PAB |

### CF-S3 composite

CloudFront `5xxErrorRate` + **CF-S3-01** → fix S3 origin access before tuning cache behaviors.

### CF-APIGW-01 / CF-LAMBDA-URL-01 (composite)

| Pattern | Symptoms | Inference |
|---------|----------|-------------|
| CF-APIGW-01 | CF origin latency + API GW 5xx/throttle | Stage deployment, integration timeout, edge WAF |
| CF-LAMBDA-URL-01 | CF origin latency + Lambda errors | Function URL auth (AWS_IAM vs NONE), timeout, cold start |

Mermaid edge labels: `default` (DefaultCacheBehavior), path pattern (e.g. `/api/*`), `group:{id}` (origin group primary), or `origin`.

**CF-ORIGIN-GROUP-01**: Origin Group configured — primary origin unhealthy triggers failover on HTTP status codes listed in distribution config; verify secondary origin health in same patrol window.

**apigw_v2**: HTTP API (API Gateway v2) distinguished from REST API v1 via `apigatewayv2 get-apis` at collect time.

**S3-4XX-01** / **S3-5XX-01**: S3 bucket `4xxErrors` / `5xxErrors` (CloudWatch `AWS/S3`, 1h Sum) for CloudFront static origins — OAC/policy/path issues vs origin 5xx.

**S3-METRICS-01** (INFO): No S3 request metric datapoints and `list-metrics` empty — degrade to CloudFront `5xxErrorRate` or enable bucket request metrics.

## Entry: ALB/NLB + ACM

### ALB-EC2-01 / ALB-TGT-01

See existing ALB → EC2 network path rules. Use **target group stickiness + health check matcher** (HTTP code) when debugging.

### ALB-5XX-01: Target 5XX without unhealthy count

| Symptoms | `HTTPCode_Target_5XX_Count` high, `UnHealthyHostCount` low |
| Inference | App returns 500 while passing TCP/HTTP shallow check |
| Fix path | Deepen health check path; app logs; X-Ray trace if enabled |

### NLB-TRAFFIC-01: Active flows near connection limit

| Symptoms | `ActiveFlowCount` ≥ 50,000 (threshold: Warning 10K, Critical 50K) |
| Inference | NLB approaching its connection capacity per AZ |
| Fix path | Distribute across AZs or increase NLB count via `aws-elb-ops` |

### NLB-TRAFFIC-02: Traffic surge detected

| Symptoms | `ProcessedBytes` ≥ 5 GB (threshold: Warning 1 GB, Critical 5 GB) |
| Inference | NLB experiencing elevated traffic volume |
| Fix path | Review traffic patterns; delegate `aws-elb-ops` for scaling analysis |

### ACM-EXP-01

ALB listener using cert expiring < 30d → TLS handshake failures masquerading as 502.

### ECS-TASK-01: ECS service task deficit

| Symptoms | desiredCount > 0, runningCount < desiredCount |
| Inference | Task failed to start due to capacity, image error, or health check |
| Metrics | AWS/ECS namespace — Service.{RunningTaskCount,DesiredTaskCount} |
| Fix path | `aws-ecs-ops` — check stopped tasks, ECS events, service events |

### APIGW-5XX-01: API Gateway elevated 5XX errors

| Symptoms | `5XXError` metric > 0 or throttling (4XXClientErrors spike) |
| Inference | Integration timeout, upstream failure, or misconfigured backend |
| Metrics | AWS/APIGateway or AWS/APIGatewayV2 namespace — 5XXError, ThrottleRate |
| Fix path | `aws-apigateway-ops` — check stage, deployment, integration config |

### APIGW-DEPLOY-01: API Gateway no active deployment

| Symptoms | API exists but has no active stages |
| Inference | API created but never deployed — not accessible |
| Fix path | `aws-apigateway-ops` — create deployment and stage |

### EBS-VOL-01: Orphan EBS volume (> 30 days available)

| Symptoms | Volume in `available` state > 30 days without attachment |
| Inference | Failed deployment or manual detach — potential orphan cost |
| Metrics | AWS/EC2 — VolumeState = available |
| Fix path | `aws-ebs-ops` — review for reattachment or deletion |

### EBS-VOL-02: EBS volume queue depth elevated

| Symptoms | VolumeQueueLength > 0 for sustained period (I/O bottleneck) |
| Inference | EBS-optimized instance or volume throughput exhausted |
| Metrics | AWS/EBS — VolumeQueueLength |
| Fix path | `aws-ebs-ops` — upgrade volume type, enable Provisioned IOPS |

## Compute paths

### EC2 + ASG

**ASG-CAP-01**: desired ≥ 90% max → scale ceiling before traffic spike.

**CO-EC2-01**: Compute Optimizer UNDER_PROVISIONED → proactive scale-up before CPU breach.

### EC2 Memory & IO (AIOps)

**EC2-MEM-01**: CloudWatch Agent memory > 85% sustained + OOM kills in `/var/log/messages` or `dmesg` (requires CloudWatch Agent installed on instance)
- **Inference**: Memory leak or undersized instance. Check process-level memory via `ps aux --sort=-%mem`.
- **Fix path**: Identify top memory consumer process; consider instance resize or application memory tuning. Delegate `aws-ec2-ops`.

**EC2-IO-01**: `VolumeQueueLength` > 64 + `BurstBalance` < 20%
- **Inference**: EBS IOPS/throughput exhaustion. gp2/st1/sc1 burst bucket depleted.
- **Fix path**: Upgrade to gp3/io1/io2 with provisioned IOPS/throughput. Check `describe-volume-types` for limits. Delegate `aws-ec2-ops`.

**EC2-IO-02**: `ReadLatency`/`WriteLatency` p95 > 20ms + `VolumeQueueLength` > 32
- **Inference**: EBS latency caused by queue depth. Application experiencing slow disk reads/writes.
- **Fix path**: Reduce concurrent I/O threads, increase EBS IOPS, or migrate to io1/io2. Delegate `aws-ec2-ops`.

**EC2-NET-01**: `NetworkOut` > 80% instance type network limit + retransmits in TCP stats
- **Inference**: Network bandwidth saturation. Instance type too small for traffic volume.
- **Fix path**: Resize to higher network capacity instance (e.g., m5.large → m5.xlarge). Check `describe-instance-types` for NetworkPerformance. Delegate `aws-ec2-ops`.

**EC2-NET-02**: `NetworkPacketsIn`/`Out` drop rate > 1% + VPC Flow Logs `REJECT` entries
- **Inference**: Packet drops from security group rules or ENI limits.
- **Fix path**: Review SG inbound/outbound rules; check instance ENI limits. Delegate `aws-vpc-ops` + `aws-ec2-ops`.

### ECS

**ECS-TASK-01**: `runningCount < desiredCount` → task placement, Fargate limits, image pull, or CPU/mem.

### EKS

**EKS-NG-01**: nodegroup `health.issues` → ASG, subnet IP exhaustion, IAM, CNI.

### Serverless

**LAMBDA-THROTTLE-01** + **APIGW-5XX-01**: throttles correlate with API 5xx → concurrency / downstream RDS timeout.

## Application Auto Scaling

### PD-AUTOSCALING-01: ECS Service at max capacity (no scaling headroom)

| Symptoms | `runningCount == MaxCapacity` 持续 ≥ 10m,target tracking active |
| Inference | Target tracking 已 saturate 上限,业务增长前需主动 raise MaxCapacity |
| Metrics | Namespace `AWS/ECS` — dimension `ClusterName` + `ServiceName`; metric `RunningTaskCount` |
| Fix path | delegate `aws-application-autoscaling-ops` — `register-scalable-target --max-capacity <new>`. Runbook `RB-AUTOSCALING-01` |

### CO-AUTOSCALING-01: ECS Service scaled to ceiling (0 headroom)

| Symptoms | `MinCapacity == MaxCapacity`,target tracking active |
| Inference | 无安全 headroom,无法 scale-down 节省费用 |
| Metrics | Compare `MinCapacity` vs `MaxCapacity` on `describe-scalable-targets` |
| Fix path | delegate `aws-application-autoscaling-ops` — `register-scalable-target --min-capacity <lower>` (keep ≥ desiredCount). Runbook `RB-AUTOSCALING-01` |

### CO-AUTOSCALING-02: TargetTracking ScaleInCooldown > 600s (cost risk)

| Symptoms | `describe-scaling-policies` shows `ScaleInCooldown > 600` for ECS target tracking |
| Inference | 缩容反应慢,非高峰期持续 billing → cost risk |
| Metrics | Application Auto Scaling API (not CloudWatch) |
| Fix path | delegate `aws-application-autoscaling-ops` — `put-scaling-policy` with `ScaleInCooldown=300`. Inform `aws-finops-core` |

### FD-AUTOSCALING-01: ECS service deficit + active scaling policy not firing

| Symptoms | `runningCount < desiredCount` 持续 + active target tracking 不扩容 |
| Inference | Target tracking not responding to metric spike (wrong metric namespace, alarm misconfig) |
| Metrics | `RunningTaskCount`/`DesiredTaskCount` (AWS/ECS) + `ECSServiceAverageCPUUtilization` (Container Insights) |
| Fix path | Verify `PredefinedMetricSpecification` in `describe-scaling-policies`; verify CloudWatch metric has data; delegate `aws-application-autoscaling-ops` to recreate policy |

## Data layer

### RDS + Performance Insights

**RDS-PI-01**: `db.load.avg` elevated → top wait via `pi get-resource-metrics` / dimension keys.

**RDS-CONN-01**: connections vs `max_connections` parameter → pool storm; consider **RDS Proxy**.

**RDS-LAT-01**: Read/WriteLatency CloudWatch + PI SQL.

**RDS-PROXY-01**: `ClientConnections` ≥ **80%** of pool limit (`max_connections` × proxy `MaxConnectionsPercent`) — not raw connection count.

**RDS-PROXY-02**: `DatabaseConnectionsSetupFailed` — auth, SG, or target RDS unavailable.

**RDS-PROXY-CONN-01** (composite): Proxy findings + `RDS-CONN-01` — tune proxy max % + app pool.

**RDS-PROXY-TGT-01**: `describe-db-proxy-targets` TargetHealth ≠ AVAILABLE.

**RDS-PROXY-AURORA-01**: Proxy `TRACKED_CLUSTER` target + Aurora `Status` ≠ available.

**RDS-PROXY-AURORA-02**: Aurora `DatabaseConnections` (cluster dim) high while proxy in path — scale ACUs; delegate **`aws-aurora-ops`**; runbook 06.

### Aurora cluster (AIOps)

**AURORA-LAG-01**: `AuroraReplicaLag` > threshold → add reader or scale writer; **`aws-aurora-ops`**.

**AURORA-SLV2-01**: `ServerlessDatabaseCapacity` ≥ 90% Max → raise MaxCapacity (AUTO_HEAL, capped).

**AURORA-GDB-01**: `AuroraGlobalDBReplicationLag` elevated → MANUAL DR review.

**AURORA-CACHE-01**: `BufferCacheHitRatio` < 99% → scale class or tune buffer params.

### ElastiCache

**CACHE-MEM-01 / Evictions**: memory pressure → cluster scale, TTL, hot key.

### DynamoDB

**METRIC-DynamoDB-ThrottledRequests**: on-demand throttle or RCU/WCU saturation → auto scaling policy.

## Egress

**NAT-PORT-01**: `ErrorPortAllocation` → add NAT GW per AZ or reduce outbound fan-out.

## Distributed tracing

**XRAY-FAULT-01**: Service node fault/error rate ≥ 5% in `get-service-graph` window.

**XRAY-LAMBDA-01** (composite): X-Ray hot node + Lambda `Errors` — trace cold start / timeout chain.

Enable with `daily-health-check.py --enable-xray` or emergency run for latency/502.

## Observability-native

**CW-ALARM-01**: Any alarm already in `ALARM` → customer signal overrides generic thresholds.

**DG-INSIGHT-01**: DevOps Guru ONGOING insight on RDS/Lambda → follow recommendation narrative.

**CFG-NC-01**: Config NON_COMPLIANT → security/compliance drift (SG, S3 public, etc.).

**SH-CRIT-01**: Security Hub CRITICAL → map to ASFF control; delegate aws-securityhub-ops.

**GD-HIGH-01**: GuardDuty HIGH+ → threat correlation before dismissing as metric noise.
