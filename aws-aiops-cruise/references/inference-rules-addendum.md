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
> **Deferred inference** (NOT added — would be dead code): OpenSearch,
> CloudFront, EKS, Athena, RAM, SecretsManager have **no PRODUCTS entry** in
> `_shared.py`, so `signals["<svc>"]` is never populated and any inference block
> for them could never fire. Their routing is wired (see table below); inference
> rules follow only after a metrics collector / PRODUCTS entry is added (out of
> the surgical scope of this change). `OS-HEAP-01`/`OS-SHARD-01` were briefly
> added then removed for this reason.

## Routing status (all 8 wired into cruise/orchestrator SKILL.md)

| Skill | Routing | Inference code in `_inference.py` |
|-------|---------|-----------------------------------|
| aws-dynamodb-ops | ✅ added | ✅ live (DYNAMO-THROTTLE-01 / DYNAMO-GSI-01) |
| aws-elasticache-ops | ✅ added | ✅ live (EC-MEM-01 / EC-FAILOVER-01 / CACHE-EVICT-01) |
| aws-opensearch-ops | ✅ added | ⏳ deferred (no `OpenSearch` PRODUCTS entry → signals never populated) |
| aws-cloudfront-ops | ✅ added | ⏳ deferred (no `CloudFront` PRODUCTS entry; `CF-*` only referenced in cross-links) |
| aws-eks-ops | ✅ added | ⏳ deferred (covered by `EKS-NG-01` collector, not `_inference.py`; no `EKS` PRODUCTS entry) |
| aws-athena-ops | ✅ added | ⏳ deferred (no `Athena` PRODUCTS entry) |
| aws-ram-ops | ✅ added | ⏳ deferred (no `RAM` PRODUCTS entry) |
| aws-secretsmanager-ops | ✅ added | ⏳ deferred (no `SecretsManager` PRODUCTS entry) |
| aws-opensearch-ops | ✅ added | ✅ exists (OS-HEAP-01 / OS-SHARD-01) |
| aws-cloudfront-ops | ✅ added | ✅ exists (CF-ORIGIN-01 / CF-EDGE-01 / CF-S3-01 …) |
| aws-eks-ops | ✅ added | ⏳ to be added (Phase 2) |
| aws-athena-ops | ✅ added | ⏳ to be added (Phase 2) |
| aws-ram-ops | ✅ added | ⏳ to be added (Phase 3) |
| aws-secretsmanager-ops | ✅ added | ⏳ to be added (Phase 3) |

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

### EKS-NODE-01 (Phase 2)
- Trigger: EKS node `NotReady` count > 0
- Logic: >0 WARNING
- Action: delegate `aws-eks-ops`

### EKS-OOM-01 (Phase 2)
- Trigger: pod OOM / eviction events > 0
- Logic: >0 CRITICAL
- Action: delegate `aws-eks-ops`

### CF-ORIGIN-02 (implemented, distinct from CF-ORIGIN-01)
- Trigger: CloudFront `OriginLatency` > 1000ms OR `OriginSuccessRate` < 0.99
- Action: delegate `aws-cloudfront-ops`

### CF-CACHE-01 (implemented)
- Trigger: `CacheHitRate` < 0.8
- Action: delegate `aws-cloudfront-ops`

### ATHENA-COST-01 (Phase 2)
- Trigger: Athena query `EstimatedBytesScanned` anomaly OR duration > 600s
- Action: delegate `aws-athena-ops`

### RAM-SHARE-01 (Phase 3)
- Trigger: RAM `ShareStatus` != ACTIVE OR principal association rejected
- Action: delegate `aws-ram-ops`

### SEC-ROTATE-01 (Phase 3)
- Trigger: SecretsManager `LastRotated` age > 90d
- Action: delegate `aws-secretsmanager-ops`
