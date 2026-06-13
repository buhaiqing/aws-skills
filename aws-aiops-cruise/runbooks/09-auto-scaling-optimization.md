---
runbook_id: "09"
scenario: "Auto Scaling optimization"
version: "1.0.0"
---

# Auto Scaling Optimization

Read-only review of ASG metrics vs capacity:

```bash
aws autoscaling describe-auto-scaling-groups --output json
aws cloudwatch get-metric-statistics --namespace AWS/EC2 --metric-name CPUUtilization ...
```

> **Script**: [`runbooks/scripts/auto-scaling-optimization.py`](../scripts/auto-scaling-optimization.py)

Recommendations only; scaling actions via `aws-autoscaling-ops` with human confirmation.
