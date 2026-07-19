# CloudWatch ServiceLens API Usage Reference

CloudWatch ServiceLens integrates X-Ray traces with CloudWatch metrics and logs
for end-to-end visibility into service performance.

Primary source: [ServiceLens documentation](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring-ServiceLens.html).

## get-insight-rules

Lists CloudWatch Contributor Insights rules for service-level latency/error analysis.

```bash
aws insights list-insight-rules \
  --region "$AWS_DEFAULT_REGION" \
  --output json
```

**Key fields**:

| JSON Path | Meaning |
|-----------|---------|
| `.InsightRules[].RuleName` | Rule identifier |
| `.InsightRules[].RuleState` | `ENABLED` or `DISABLED` |

## get-insight-rule-results

Retrieves aggregated Contributor Insights data for a specific rule.

```bash
aws insights get-insight-rule-results \
  --rule-name "causal-graph-service-latency" \
  --start-time "2026-07-18T00:00:00Z" \
  --end-time "2026-07-19T00:00:00Z" \
  --region "$AWS_DEFAULT_REGION" \
  --output json
```

**Key fields**:

| JSON Path | Meaning |
|-----------|---------|
| `.Results[].Keys[]` | Service/dimension names |
| `.Results[].AggregatedValue.Count` | Hit count for this combination |
| `.Results[].AggregatedValue latency_p99` | p99 latency if projected |

## ServiceLens + X-Ray Integration

ServiceLens automatically associates CloudWatch metrics with X-Ray traces when
X-Ray SDK is instrumented. For causal graph purposes:

1. X-Ray `get-service-graph` provides the **topology** (who calls whom).
2. CloudWatch metrics provide the **baseline** (normal latency/error levels).
3. Combined → `detect_anomalies()` compares current trace latency vs baseline.

## Permissions

Requires: `cloudwatch:ListInsightRules`, `cloudwatch:GetInsightRuleResults`.
