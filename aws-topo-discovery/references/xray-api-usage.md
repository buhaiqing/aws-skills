# X-Ray API Usage Reference

AWS X-Ray API for collecting trace topology and service dependency data.
Primary source: [X-Ray API Reference](https://docs.aws.amazon.com/xray/api/API_Reference/).

## Common JSON Paths

```
# get-service-graph Services:  .Services[].{Name,Type,ReferenceId}
# get-service-graph Edges:    .Edges[].{StartId,EndId,ResponseTimeHistogram}
# batch-get-traces-summaries:  .Traces[].{Id,Duration,HasError,HasFault}
# get-error-summaries:        .ErrorSummaries[].{Bucket,Count}
```

## get-service-graph

Collects the service graph (services + call-chain edges) for a time range.

```bash
aws xray get-service-graph \
  --start-time 1719000000 \
  --end-time 1719086400 \
  --time-range-type ABSOLUTE \
  --region "$AWS_DEFAULT_REGION" \
  --output json
```

**Key fields**:

| JSON Path | Meaning |
|-----------|---------|
| `.Services[].Name` | Service identifier (e.g. `api-gateway`, `ec2-app`) |
| `.Services[].Type` | AWS resource type (e.g. `AWS::API Gateway`) |
| `.Services[].ReferenceId` | Numeric node ID used in Edges |
| `.Edges[].StartId` | Source service ReferenceId |
| `.Edges[].EndId` | Target service ReferenceId |
| `.Edges[].ResponseTimeHistogram[].Value` | Response time bucket value (seconds) |

## batch-get-traces-summaries

Retrieves metadata (not full payloads) for a list of trace IDs.

```bash
aws xray batch-get-traces-summaries \
  --trace-ids "trace-id-1" "trace-id-2" \
  --region "$AWS_DEFAULT_REGION" \
  --output json
```

**Key fields**:

| JSON Path | Meaning |
|-----------|---------|
| `.Traces[].Id` | Trace ID |
| `.Traces[].Duration` | Total duration in seconds |
| `.Traces[].HasError` | True if any segment has an error |
| `.Traces[].HasFault` | True if any segment has a fault |
| `.Traces[].Segments[].service.name` | Service that produced the segment |
| `.Traces[].Segments[].subsegments[].name` | Downstream call name |
| `.Traces[].Segments[].subsegments[].has_error` | Subsegment error flag |

## get-error-summaries

Retrieves error distribution grouped by service and error type.

```bash
aws xray get-error-summaries \
  --group-name "default" \
  --start-time 1719000000 \
  --end-time 1719086400 \
  --region "$AWS_DEFAULT_REGION" \
  --output json
```

**Key fields**:

| JSON Path | Meaning |
|-----------|---------|
| `.ErrorSummaries[].Bucket` | Error category (e.g. `ClientError`, `ServerError`) |
| `.ErrorSummaries[].Count` | Number of occurrences |
| `.ErrorSummaries[].ErrorStatistics.TotalCount` | Total error count |

## Fallback: CloudWatch Contributor Insights

If X-Ray is not enabled, infer service dependencies from CloudWatch metrics:

```bash
aws insights get-insight-rule-results \
  --rule-name "causal-graph-service-latency" \
  --start-time "2026-07-18T00:00:00Z" \
  --end-time "2026-07-19T00:00:00Z" \
  --region "$AWS_DEFAULT_REGION" \
  --output json
```

## Permissions

Requires: `xray:GetServiceGraph`, `xray:BatchGetTraces`, `xray:GetErrorSummaries`, `cloudwatch:GetInsightRuleResults`.
