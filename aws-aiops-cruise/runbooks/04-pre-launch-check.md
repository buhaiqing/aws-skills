---
runbook_id: "04"
scenario: "Pre-launch check"
version: "1.0.0"
---

# Pre-Launch Check

Before traffic events: run daily health + 3× projected load review (manual checklist).

1. Phase 1: TopoScan + ConfigDrift (no drift in 7d)
2. Phase 2: ALB/RDS/NAT headroom vs [`threshold-definitions.md`](../references/threshold-definitions.md)
3. Phase 3: ASG desired/max review — delegate `aws-autoscaling-ops` for changes (user confirm)

```bash
bash scripts/agents/perceive/__init__.sh all --resource-group $RG
```
