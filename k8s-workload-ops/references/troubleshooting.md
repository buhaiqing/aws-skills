# Troubleshooting (Compact)

| Symptom | Likely cause | First check | Action |
|---|---|---|---|
| CrashLoopBackOff | app startup error / bad config | `logs --previous` (MCP `get_loki_query_range` ERROR) | fix config; if bad release → `rollback-deployment` |
| Pending (unschedulable) | insufficient CPU/mem / taint | events (`get_naming_k8s_pod_events`) + requests | lower requests or add capacity |
| OOMKilled | memory limit too low / leak | `get_k8s_pod_jvm_heap_memory_usage_by_pod` | raise memory.limits or fix leak |
| ImagePullBackOff | wrong tag / registry auth | `describe pod` events | fix image tag (G-IMG-1) / registry secret |
| High restart count | flapping liveness probe | restart stats + probe config | tune probe thresholds |
| Rollout stuck | progress deadline exceeded | `rollout status` + events | surface events; offer rollback |
| MCP tool error/empty | env drift / auth | retry once | fall back to kubectl (log `[MCP-FALLBACK]`) |
| kubectl forbidden | RBAC | `auth can-i` | HALT; report; never escalate |
