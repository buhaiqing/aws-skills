# Inference Rules Addendum (Coverage Gap Closure)

Supplements `aws-aiops-cruise` / `aws-aiops-orchestrator` routing for the 8
`aws-<svc>-ops` skills previously absent from the cross-skill reference tables.

All rules are **detect + recommend + delegate only** — they never auto-execute
mutating AWS calls (consistent with GCL fail-closed).

> **Provenance (Phase 1)**: `DYNAMO-THROTTLE-01` and `EC-MEM-01` already existed
> in HEAD `_inference.py` (Phase 1 aligned EC-MEM-01 to design doc §4:
> `>=80 WARN / >=95 CRIT`). `DYNAMO-GSI-01` and `EC-FAILOVER-01` were added as
> live rules (DynamoDB + ElastiCache both have PRODUCTS entries in `_shared.py`,
> so their `signals` keys are populated in production).
>
> **Deferred inference** (was NOT added — would be dead code): OpenSearch,
> CloudFront, Athena, RAM, SecretsManager had **no PRODUCTS entry** in
> `_shared.py`, so `signals["<svc>"]` was never populated and any inference
> block for them could never fire. This was closed on 2026-07-19 (Task #10,
> Phase-2/3): each service now has a **native collector** that populates its
> `signals` key, making the rules live. `OS-HEAP-01`/`OS-SHARD-01` were
> briefly added then removed for this reason — now re-added via collector.
>
> **EKS is the exception**: it has no PRODUCTS entry, but `audit_eks_nodes`
> (native collector) populates `signals["EKS"]` with per-nodegroup scalingConfig
> metrics, so `EKS-NG-02` fires at runtime; the EKS_NODE layer (CloudWatch
> Container Insights) drives `EKS-NODE-01` / `EKS-OOM-01`. Implemented as live rules.

## Routing status (all 8 wired into cruise/orchestrator SKILL.md)

| Skill | Routing | Inference code in `_inference.py` |
|-------|---------|-----------------------------------|
| aws-dynamodb-ops | ✅ added | ✅ live (DYNAMO-THROTTLE-01 / DYNAMO-GSI-01) |
| aws-elasticache-ops | ✅ added | ✅ live (EC-MEM-01 / EC-FAILOVER-01 / CACHE-EVICT-01) |
| aws-opensearch-ops | ✅ added | ✅ live (OS-HEAP-01 / OS-SHARD-01 / **OS-MASTER-01 / OS-SNAP-01** via `signals["OpenSearch"]` from `audit_opensearch_health`) |
| aws-cloudfront-ops | ✅ added | ✅ live (CF-ORIGIN-02 / CF-CACHE-01 via `signals["CloudFront"]` from `audit_cloudfront_signals`; CF-ORIGIN-01 / CF-EDGE-01 / CF-S3-01 from cross-links) |
| aws-eks-ops | ✅ added | ✅ live (EKS-NG-02 via `signals["EKS"]`; EKS-NODE-01 / EKS-OOM-01 via `signals["EKS_NODE"]` from Container Insights) |
| aws-athena-ops | ✅ added | ✅ live (ATHENA-COST-01 via `signals["Athena"]` from `audit_athena_cost`) |
| aws-ram-ops | ✅ added | ✅ live (RAM-SHARE-01 via `signals["RAM"]` from `audit_ram_shares`) |
| aws-secretsmanager-ops | ✅ added | ✅ live (SEC-ROTATE-01 via `signals["SecretsManager"]` from `audit_secrets_rotation`) |

## Rule semantics (full 8, independent of code status)

### DYNAMO-THROTTLE-01 (implemented)
- Trigger: DynamoDB `ThrottledRequests` >= 1
- Action: delegate `aws-dynamodb-ops`

### DYNAMO-GSI-01 (implemented)
- Trigger: `GSIWriteThrottleEvents` / `GSIReadThrottleEvents` >= 1
- Action: delegate `aws-dynamodb-ops`

### EC-MEM-01 (implemented)
- Trigger: ElastiCache `DatabaseMemoryUsagePercentage` >= 80 (>=95 CRITICAL)
- Action: delegate `aws-elasticache-ops`

### EC-FAILOVER-01 (implemented)
- Trigger: `FailoverInProgress` present
- Action: delegate `aws-elasticache-ops`

### OS-HEAP-01 (implemented)
- Trigger: OpenSearch `JVMMemoryPressure` >= 80 (>=95 CRITICAL)
- Action: delegate `aws-opensearch-ops`

### OS-SHARD-01 (implemented)
- Trigger: `ClusterIndexWritesBlocked` = true OR `UnassignedShards` > 0
- Action: delegate `aws-opensearch-ops`

### OS-MASTER-01 (Phase 1 OS-signals) — ✅ live
- Trigger: OpenSearch `MasterReachableFromNode` == 0 (master not reachable from node)
- Guard: skip when metric is absent (None)
- Action: delegate `aws-opensearch-ops`
- Source: `audit_opensearch_health` (collector) → `signals["OpenSearch"]`

### OS-SNAP-01 (Phase 1 OS-signals) — ✅ live
- Trigger: OpenSearch `AutomatedSnapshotFailure` > 0
- Action: delegate `aws-opensearch-ops`
- Source: `audit_opensearch_health` (collector) → `signals["OpenSearch"]`

### EKS-NODE-01 (implemented)
- Trigger: EKS node `NotReady` (CloudWatch Container Insights `node_status_condition_ready`, summarized as `NodeNotReadyMin`) < 1.0
- Logic: min ready < 1.0 → WARNING
- Action: delegate `aws-eks-ops`

### EKS-OOM-01 (implemented)
- Trigger: pod OOM-killed events (Container Insights `pod_container_status_terminated_reason_oom_killed`, summarized as `PodOOMKilledSum`) > 0
- Logic: sum > 0 → CRITICAL
- Action: delegate `aws-eks-ops`

### EKS-NG-02 (implemented)
- Trigger: per-nodegroup scalingConfig — `NodesCurrent < NodesDesired` (CRITICAL, nodes not ready) or `NodesCurrent >= NodesMax and NodesDesired >= NodesMax` (WARNING, at max capacity with pending scale-up)
- Action: delegate `aws-eks-ops`

### Telemetry source alternatives (EKS-NODE-01 / EKS-OOM-01)

Both rules consume the summarized signal keys `NodeNotReadyMin` / `PodOOMKilledSum`; the
collector that populates them is swappable. The shipped `audit_eks_nodes` collector uses
CloudWatch Container Insights (`EKS/ContainerInsights`). Equivalent alternative backends:

| Source | Node NotReady signal | Pod OOM-kill signal |
|--------|---------------------|---------------------|
| CloudWatch Container Insights (shipped) | `node_status_condition_ready` (dim `ClusterName`, stat `Minimum`) | `pod_container_status_terminated_reason_oom_killed` (dim `ClusterName`, stat `Sum`) |
| kube-state-metrics / Prometheus | `kube_node_status_condition{condition="Ready",status="true"}` gauge → min over cluster | `kube_pod_container_status_terminated_reason{reason="OOMKilled"}` counter → sum over window |

Swap-in requires only a different `audit_eks_nodes` collector; the inference rules are unchanged.

### CF-ORIGIN-02 (implemented, distinct from CF-ORIGIN-01)
- Trigger: CloudFront `OriginLatency` > 1000ms OR `OriginSuccessRate` < 0.99
- Action: delegate `aws-cloudfront-ops`

### CF-CACHE-01 (implemented)
- Trigger: `CacheHitRate` < 0.8
- Action: delegate `aws-cloudfront-ops`

### ATHENA-COST-01 (Phase 2) — ✅ implemented 2026-07-19
- Trigger: Athena workgroup `ProcessedBytes` over 6h window >= 5e9 (WARN) / >= 2e10 (CRITICAL)
- Action: delegate `aws-athena-ops`
- Source: `audit_athena_cost` (collector) → `signals["Athena"]`

### RAM-SHARE-01 (Phase 3) — ✅ implemented 2026-07-19
- Trigger: RAM `ShareStatus` != ACTIVE OR principal association rejected (FAILED)
- Action: delegate `aws-ram-ops`
- Source: `audit_ram_shares` (collector) → `signals["RAM"]`

### SEC-ROTATE-01 (Phase 3) — ✅ implemented 2026-07-19
- Trigger: SecretsManager `LastRotated` age > 90d (WARN) / > 180d or rotation disabled (CRITICAL)
- Action: delegate `aws-secretsmanager-ops`
- Source: `audit_secrets_rotation` (collector) → `signals["SecretsManager"]`

## CloudWatch Alarm Definitions

The inference rules above detect conditions via periodic patrol. To also receive
push-based alerts between patrol cycles, deploy CloudWatch metric alarms for the
threshold-based rules listed below.

Alarm definitions: [`assets/alarms/cruise-inference-alarms.yaml`](../assets/alarms/cruise-inference-alarms.yaml)
Deploy: `aws cloudwatch put-metric-alarm --cli-input-json "$(yq -o=json '.alarm_key' < alarms.yaml)"`

### Alarmable rules

| Rule ID | Namespace | Metric | WARN | CRIT | Stat | Period | Comparison | Notes |
|---|---|---|---|---|---|---|---|---|
| RDS-CONN-01 | AWS/RDS | DatabaseConnections | 70% max_conn | 85% max_conn | Average | 300s | > Threshold | Dynamic — user fills `_max_connections` |
| RDS-LAT-01 | AWS/RDS | ReadLatency | 0.02 | 0.1 | p95 | 300s | > Threshold | |
| AURORA-LAG-01 | AWS/RDS | AuroraReplicaLag | 1000 | 30000 | Maximum | 60s | > Threshold | |
| AURORA-CACHE-01 | AWS/RDS | BufferCacheHitRatio | 99 | 95 | Average | 300s | < Threshold | Lower is worse |
| XRAY-FAULT-01 | AWS/XRay | FaultRate | 5 | 10 | Average | 300s | > Threshold | |
| NLB-TRAFFIC-01 | AWS/NetworkELB | ActiveFlowCount | 10000 | 50000 | Average | 60s | > Threshold | |
| NLB-TRAFFIC-02 | AWS/NetworkELB | ProcessedBytes | 1 GB | 5 GB | Sum | 300s | > Threshold | |
| EC-CPU-01 | AWS/ElastiCache | CPUUtilization | 70 | 85 | Average | 60s | > Threshold | |
| EC-MEM-01 | AWS/ElastiCache | DatabaseMemoryUsagePercentage | 80 | 95 | Average | 60s | > Threshold | |
| EC2-MEM-01 | CWAgent | mem_used_percent | 80 | 90 | Average | 300s | > Threshold | Requires CW Agent; inference code uses `MemoryUtilization` |
| DYNAMO-THROTTLE-01 | AWS/DynamoDB | ThrottledRequests | 1 | 10 | Sum | 300s | > Threshold | |
| CACHE-EVICT-01 | AWS/ElastiCache | Evictions | 100 | 1000 | Sum | 300s | > Threshold | |
| ATHENA-COST-01 | AWS/Athena | ProcessedBytes | 5 GB | 20 GB | Sum | 6h | > Threshold | |
| CF-ORIGIN-02 | AWS/CloudFront | OriginLatency | 1000ms | 3000ms | Average | 60s | > Threshold | |
| OS-HEAP-01 | AWS/ES | JVMMemoryPressure | 80 | 95 | Maximum | 60s | > Threshold | |
| SEC-ROTATE-01 | — | RotationAgeDays | 90d | 180d | — | — | — | Computed value, no direct CW alarm |

### Exclusion rationale

Rules **not** alarmable and why:

- **Binary/presence rules** (ALB-EC2-01/02, RDS-PROXY-02, NAT-PORT-01, LAMBDA-THROTTLE-01, APIGW-5XX-01, etc.): fire on presence of ANY occurrence → covered by cruise patrol, no static threshold needed.
- **Composite/multi-metric rules** (WAF-ALB-01, EC2-IO-01/02, EC2-NET-02): require multi-variable logic → better suited to inference engine.
- **Non-CloudWatch services** (DevOps Guru DG-INSIGHT-01, Container Insights EKS-*): not CloudWatch-native metrics.
- **Dynamic-percentage rules** (RDS-PROXY-01, EC-CONN-01, EC2-NET-01): threshold is % of a runtime-determined limit → documented but user fills the actual value.

### Deployment note

Deploy alarms per-resource after identifying the resource ID. The YAML uses
`{{user.*}}` placeholders for resource-specific values and `{{env.*}}` for environment
values. Replace before deployment or use the skill's variable substitution flow.
See `aws-cloudwatch-ops/assets/example-config.yaml` for FinOps cost tips
($0.10/alarm/month; composite alarms reduce count).
