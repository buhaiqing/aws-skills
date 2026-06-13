---
runbook_id: "08"
scenario: "ElastiCache performance"
version: "1.0.0"
---

# ElastiCache Performance

Focus metrics: `DatabaseMemoryUsagePercentage`, `CurrConnections`, `CacheHits`/`CacheMisses`.

```bash
aws elasticache describe-cache-clusters --show-cache-node-info --output json
```

> **Script**: [`runbooks/scripts/redis-performance-diagnosis.py`](../scripts/redis-performance-diagnosis.py)
