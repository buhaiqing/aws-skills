---
name: k8s-workload-ops
description: >-
  Use when operating or diagnosing Kubernetes workloads (Deployment / Pod /
  HPA / ReplicaSet) on production clusters — diagnose crashing/pending pods,
  inspect deployment specs, audit resource-governance compliance, scale,
  rollout-restart, or rollback — even when the user says "why is this pod
  restarting", "帮我看下这个服务的日志/内存", "扩容", "回滚发布", without saying
  "Kubernetes". Read/diagnose runs MCP-first (hdops_mcp); mutations run kubectl.
license: MIT
compatibility: >-
  MCP server hdops_mcp (read/observability), kubectl v1.26+ with a valid
  kubeconfig context (mutations). No cloud credentials handled by this skill.
metadata:
  author: aws-skills
  version: "0.1.0"
  last_updated: "2026-07-26"
  cli_applicability: mcp-first
  type: base
  provides:
    - diagnose-workload
    - inspect-deployment
    - governance-audit
    - scale-workload
    - rollout-restart
    - rollback-deployment
  environment:
    - KUBECONFIG
  destructive_ops_require_confirm: true
---

# Kubernetes Workload Operations Skill

> **One-liner**: Cloud-neutral L1 runbook for K8s workload diagnosis & governance.
> **Read/diagnose = MCP-first** (`hdops_mcp`), **mutations = kubectl-only** with a
> safety gate (hdops_mcp exposes no mutating tool). Pilot for SRE JD #2/#3.

## Layering Contract (type / provides)

`type: base` (L1). `provides` lists the 6 operations. This skill contains
service-level logic and holds **no** `delegate:` map. Any agent globs
`*-ops/SKILL.md`, reads frontmatter, and composes without a per-agent loader.

## Trigger & Scope

### SHOULD Use When
- Diagnose abnormal workloads: CrashLoopBackOff, Pending, OOMKilled, high restart count.
- Inspect a Deployment spec / image tag / requests-limits for one `app`.
- Audit workload governance compliance (requests/limits, replicas, probes, PDB, image tag).
- Scale / rollout-restart / rollback a Deployment (destructive — gated).

### SHOULD NOT Use When
- EKS cluster lifecycle (create/upgrade cluster, node groups) → `aws-eks-ops`.
- CD / GitOps / canary release orchestration → future `deploy-release-ops`.
- Cluster-wide log platform capacity/cost governance → future `log-platform-ops`.
- Node / infra metrics only, no workload intent → `aws-aiops-cruise`.

## Variable Convention

| Placeholder | Source | Agent Action |
|---|---|---|
| `{{user.k8s_cluster_name}}` | User input | Ask once (e.g. "爱婴室生产"); reuse; required for all MCP calls |
| `{{user.project}}` / `{{user.profile}}` / `{{user.app}}` | User input | Ask once; addresses hdops_mcp naming DB |
| `{{user.namespace}}` | User input | Default `default`; required for kubectl |
| `{{user.kubectl_context}}` | `kubectl config current-context` | Verify in Pre-flight; HALT if unset for mutations |
| `{{output.pod_name}}` / `{{output.deployment}}` | Last MCP/kubectl response | Parse; never invent |

**Credentials**: this skill holds no secrets. MCP auth lives in the MCP server;
kubectl auth lives in `KUBECONFIG`. Fail closed if neither path is available.

## Execution Flow Pattern

Every operation: **Pre-flight → Execute → Validate → Recover**.
MCP tool map: [`references/mcp-usage.md`](references/mcp-usage.md).
kubectl fallback + mutation gates: [`references/kubectl-usage.md`](references/kubectl-usage.md).

### Read operations (MCP-first)
`diagnose-workload` / `inspect-deployment` / `governance-audit`

- **Pre-flight**: resolve `{{user.k8s_cluster_name}}` via `get_k8s_clusters_from_naming`;
  confirm the `app`/`project`/`profile` exists via `get_naming_k8s_app_infos`.
- **Execute**: call the mapped MCP tools (see mcp-usage.md). If MCP unavailable
  after 1 retry, fall back to `kubectl get/describe/logs`.
- **Validate**: non-empty result; cross-check pod↔deployment ownership.
- **Recover**: MCP error → kubectl fallback; both fail → HALT with exact error.

### Mutation operations (kubectl-only, GATED)
`scale-workload` / `rollout-restart` / `rollback-deployment`

- **Pre-flight**: `kubectl config current-context` must be set AND match
  `{{user.k8s_cluster_name}}`; run `kubectl ... --dry-run=client` first.
- **Safety Gate** (MUST, per Charter + §15 runtime_safety): require explicit
  confirmation string before executing:
  - scale → `CONFIRM SCALE <deployment> <replicas>` (scale-to-0 requires it verbatim)
  - rollout-restart → `CONFIRM RESTART <deployment>`
  - rollback → `CONFIRM ROLLBACK <deployment>`
- **Execute**: run the kubectl mutation only after the token matches.
- **Validate**: `kubectl rollout status deploy/<name>` until complete or timeout.
- **Recover**: rollout stuck → surface events; offer `rollback-deployment`; never
  silently retry a mutation.

## Governance Standards

`governance-audit` compares live config against the workload checklist in
[`references/core-concepts.md`](references/core-concepts.md) (requests/limits
mandatory, prod replicas ≥ 2, readiness/liveness probes, image tag ≠ latest, PDB
present), emitting a violation list — JD #3 "统一运行规范" as code.

## Reference Files
- [MCP Usage — primary](references/mcp-usage.md) · [kubectl — fallback + gates](references/kubectl-usage.md)
- [Core Concepts & Governance Checklist](references/core-concepts.md) · [Troubleshooting](references/troubleshooting.md)

## Quality Gate & Token Efficiency
Destructive ops gated above; pipe tool calls through `scripts/runtime_safety.py`
(§15). Runnable check: `golden-scenarios.yaml` via `scripts/golden_eval.py` (§16).
TE-1…TE-6: no hardcoded return schemas; tool/param paths declared once in `mcp-usage.md`.

> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。
