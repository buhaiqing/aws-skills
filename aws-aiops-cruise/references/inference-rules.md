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

### ACM-EXP-01

ALB listener using cert expiring < 30d → TLS handshake failures masquerading as 502.

## Compute paths

### EC2 + ASG

**ASG-CAP-01**: desired ≥ 90% max → scale ceiling before traffic spike.

**CO-EC2-01**: Compute Optimizer UNDER_PROVISIONED → proactive scale-up before CPU breach.

### ECS

**ECS-TASK-01**: `runningCount < desiredCount` → task placement, Fargate limits, image pull, or CPU/mem.

### EKS

**EKS-NG-01**: nodegroup `health.issues` → ASG, subnet IP exhaustion, IAM, CNI.

### Serverless

**LAMBDA-THROTTLE-01** + **APIGW-5XX-01**: throttles correlate with API 5xx → concurrency / downstream RDS timeout.

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
