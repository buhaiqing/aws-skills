# MCP Usage (Primary Path) — hdops_mcp

> Read/diagnose runs **MCP-first**. All tools live on server `user-hdops_mcp`.
> Invoke via `GetMcpTools(user-hdops_mcp, <name>)` for the live schema, then
> `CallMcpTool`. Tool names below verified against `GetMcpTools` on 2026-07-26.
> Do **not** hardcode return schemas (TE-1) — parse the live JSON.

## Addressing model

hdops_mcp addresses by **cluster name + naming keys**, not kubeconfig context:

- `{{user.k8s_cluster_name}}` — human name, e.g. `爱婴室生产`, `海鼎生产青岛`.
- `{{user.project}}` / `{{user.profile}}` / `{{user.stack}}` / `{{user.app}}` — naming DB keys.

Resolve first: `get_k8s_clusters_from_naming` (list clusters) →
`get_naming_k8s_app_infos(project, profile)` (confirm app + its requests/limits).

## Operation → tool map

### diagnose-workload (read-only)
| Step | Tool | Key params |
|---|---|---|
| Find broken pods | `get_k8s_exception_pod` | `k8s_cluster_name`, `start_time`, `end_time` |
| Pod base info (node/project/stack) | `get_k8s_pod_info` | `k8s_cluster_name`, `pod_name` |
| Pod CPU/mem usage | `get_k8s_pod_resource_usage` | `k8s_cluster_name`, `pod_name`, time range |
| Pod lifecycle events | `get_naming_k8s_pod_events` | `project`, time range |
| Restart stats | `get_ka_erp_container_restart_stats` | `project`, time range |
| Error logs | `get_loki_query_range` | `k8s_cluster_name`, `query='{service_name="<app>"} |~ "ERROR"'` |
| JVM OOM/GC (Java apps) | `get_k8s_pod_jvm_gc_max_by_app`, `get_k8s_pod_jvm_heap_memory_usage_by_pod` | `k8s_cluster_name`, `app_name`/`pod_name` |
| Current alerts | `get_k8s_current_alert` | `k8s_cluster_name`, time range |

### inspect-deployment (read-only)
| Step | Tool | Key params |
|---|---|---|
| Deployment YAML | `get_k8s_app_deployment_spec` | `project`, `profile`, `stack`, `app` |
| App infos (requests/limits/replicas) | `get_naming_k8s_app_infos` | `project`, `profile` |
| Latest git commits (change corr.) | `get_k8s_app_latest_git_commits` | `project`, `profile`, `stack`, `app` |

### governance-audit (read-only)
Pull `get_naming_k8s_app_infos` + `get_k8s_app_deployment_spec`, then compare
against the checklist in `core-concepts.md`. Emit `[VIOLATION] <rule>: <app>`.

## Fallback trigger

If a tool call errors or returns empty after **1 retry**, fall back to the
matching `kubectl` command in `kubectl-usage.md`. Log
`[MCP-FALLBACK] <tool> → kubectl <cmd>` so the trace shows the switch.

## Mutations are NOT here

hdops_mcp exposes **no mutating K8s tool**. `scale-workload`, `rollout-restart`,
`rollback-deployment` are kubectl-only — see `kubectl-usage.md`. Never fabricate
a mutation via a read tool.
