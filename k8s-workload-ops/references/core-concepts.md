# Core Concepts & Workload Governance Checklist

> This checklist encodes JD #3 "统一应用部署、发布及运行规范" as machine-checkable
> rules. `governance-audit` compares live config (`get_naming_k8s_app_infos` +
> `get_k8s_app_deployment_spec`) against each rule and emits violations.

## Governance rules (audit target)

| ID | Rule | Severity | Why |
|---|---|---|---|
| G-RES-1 | Every container sets CPU+memory `requests` AND `limits` | P0 | No limits → node OOM / noisy-neighbor; scheduler can't bin-pack |
| G-REP-1 | Prod Deployment `replicas ≥ 2` | P1 | Single replica = no HA during node drain / rollout |
| G-PROBE-1 | Both `readinessProbe` and `livenessProbe` defined | P1 | Missing readiness → traffic to un-ready pods during rollout |
| G-IMG-1 | Image tag is pinned, not `:latest` | P1 | `:latest` breaks reproducibility & rollback |
| G-PDB-1 | A PodDisruptionBudget covers the workload | P2 | Prevents all replicas evicted at once during drain |
| G-UTIL-1 | Sustained CPU/mem usage < 85% of `limits` | P2 | Headroom for spikes; else raise limits or scale |

Output format: `[VIOLATION] G-RES-1: app=<app> container=<c> missing memory.limits`.

## Key K8s workload concepts (agent primer)

- **Deployment → ReplicaSet → Pod**: mutations act on Deployment; each spec change
  creates a new ReplicaSet (enables `rollout undo`).
- **QoS class**: `Guaranteed` (requests==limits) > `Burstable` > `BestEffort`
  (no requests). BestEffort pods are evicted first under pressure.
- **Common failure states**: `CrashLoopBackOff` (app exits repeatedly),
  `Pending` (unschedulable — check requests vs node capacity / taints),
  `OOMKilled` (exceeded memory limit → raise limit or fix leak),
  `ImagePullBackOff` (bad tag / registry auth).
- **Rollout safety**: `maxUnavailable` / `maxSurge` control capacity during
  updates; `progressDeadlineSeconds` marks a stuck rollout.

## Quotas / limits (query live, don't hardcode)

Cluster resource capacity and per-namespace `ResourceQuota` vary by environment
— read them live via `get_naming_k8s_app_infos` / `kubectl get resourcequota`,
never hardcode a table (TE-1).
