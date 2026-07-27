# kubectl Usage — Read Fallback + Mutation Gates

> kubectl is the **fallback** for reads and the **only** path for mutations
> (hdops_mcp has no mutating tool). Requires a valid `KUBECONFIG` context.

## Pre-flight (mutations)

```bash
kubectl config current-context           # MUST be set; HALT if empty
kubectl -n "$NS" get deploy "$DEPLOY" -o wide   # confirm target exists
```

Verify the current context matches `{{user.k8s_cluster_name}}` (avoid acting on
the wrong cluster). If mismatch or unset → HALT, ask user to switch context.

## Read fallback map

| Intent | Command |
|---|---|
| Broken pods | `kubectl -n "$NS" get pods --field-selector=status.phase!=Running` |
| Describe pod | `kubectl -n "$NS" describe pod "$POD"` |
| Logs (with previous crash) | `kubectl -n "$NS" logs "$POD" --previous --tail=200` |
| Deployment spec | `kubectl -n "$NS" get deploy "$DEPLOY" -o yaml` |
| Rollout history | `kubectl -n "$NS" rollout history deploy/"$DEPLOY"` |

## Mutations — GATED

Each mutation MUST (1) pass `--dry-run=client` preview, (2) match its literal
confirmation string, (3) validate via `rollout status`. Never silently retry.

### scale-workload
Confirmation: `CONFIRM SCALE <deployment> <replicas>` (scale-to-0 requires it verbatim).
```bash
kubectl -n "$NS" scale deploy/"$DEPLOY" --replicas="$N" --dry-run=client -o yaml   # preview
kubectl -n "$NS" scale deploy/"$DEPLOY" --replicas="$N"                            # after confirm
kubectl -n "$NS" rollout status deploy/"$DEPLOY" --timeout=180s                    # validate
```

### rollout-restart
Confirmation: `CONFIRM RESTART <deployment>` (restarts all replicas → brief capacity dip).
```bash
kubectl -n "$NS" rollout restart deploy/"$DEPLOY"
kubectl -n "$NS" rollout status deploy/"$DEPLOY" --timeout=180s
```

### rollback-deployment
Confirmation: `CONFIRM ROLLBACK <deployment>` (optionally `--to-revision=<r>`).
```bash
kubectl -n "$NS" rollout history deploy/"$DEPLOY"        # pick revision first
kubectl -n "$NS" rollout undo deploy/"$DEPLOY" [--to-revision=R]
kubectl -n "$NS" rollout status deploy/"$DEPLOY" --timeout=180s
```

## Recover

| Error | Action |
|---|---|
| context unset / mismatch | HALT; ask user to `kubectl config use-context` |
| deployment not found | HALT; re-confirm `{{user.app}}`/namespace |
| rollout stuck (progress deadline) | surface `kubectl describe`/events; offer rollback |
| forbidden (RBAC) | HALT; report; do not escalate privileges |
