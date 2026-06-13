---
runbook_id: "03"
scenario: "Capacity planning"
version: "1.0.0"
---

# Capacity Planning

Weekly patrol: CloudWatch 30-day trends + Compute Optimizer recommendations (read-only).

```bash
python3 runbooks/scripts/daily-health-check.py --resource-group $RG --region $REGION
aws cloudwatch get-metric-data --output json  # FORECAST where enabled
aws compute-optimizer get-ec2-instance-recommendations --output json
```

Delegate forecast orchestration to `aws-aiops-orchestrator` for cross-service view.
