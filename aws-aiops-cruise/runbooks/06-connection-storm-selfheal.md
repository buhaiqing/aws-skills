---
runbook_id: "06"
scenario: "DB connection storm"
version: "1.0.0"
---

# Database Connection Storm

Trigger: `DatabaseConnections` > 85% of max.

1. CloudWatch 1h window on RDS connections
2. Inference rule `RDS-CONN-01`
3. CloudTrail: recent `ModifyDBInstance` / parameter changes
4. Recommend pool tuning — no `modify-db-instance` from this skill

> **Script**: [`runbooks/scripts/connection-storm.py`](../scripts/connection-storm.py)

Escalate to `aws-aiops-orchestrator` if combined with ALB 5xx.
