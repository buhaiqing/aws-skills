---
runbook_id: "05"
scenario: "Slow query diagnosis"
version: "1.0.0"
---

# Slow Query Diagnosis

Data-layer patrol: RDS Performance Insights + CloudWatch `ReadLatency`/`WriteLatency`.

```bash
aws pi get-resource-metrics --service-type RDS --identifier db-XXX --output json
```

> **Script**: [`runbooks/scripts/slow-query-diagnosis.py`](../scripts/slow-query-diagnosis.py)
