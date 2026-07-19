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
| aws-opensearch-ops | ✅ added | ✅ live (OS-HEAP-01 / OS-SHARD-01 via `signals["OpenSearch"]` from `audit_opensearch_health`) |
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
