# Troubleshooting — CloudWatch

_Latest update: 2026-05-28_

## Common Error Codes

| Error Code | HTTP | Meaning | Agent Action |
|------------|------|---------|--------------|
| InvalidParameterValue | 400 | Invalid threshold/operator/period | Fix per AWS API docs |
| ResourceNotFound | 404 | Metric or namespace not found | Verify namespace/metric via list-metrics |
| LimitExceeded | 403 | Too many alarms/queries | Delete unused alarms; request quota increase |
| ThrottlingException | 429 | Too many API calls | Backoff; retry 3x |
| InternalError | 500 | AWS service issue | Retry 3x; HALT if persists |
| DashboardNotFound | 404 | Dashboard doesn't exist | Verify dashboard name |
| ConcurrentModification | 400 | Dashboard modified by another | Re-read and retry |
| MalformedQueryException | 400 | Logs Insights query syntax error | Fix query per syntax docs |
| QueryTimeout | - | Logs query exceeded 15 min run time | Split time range, reduce scope |

## Diagnostic Order

1. **Verify credentials**: `aws sts get-caller-identity`
2. **Verify metric exists**: `aws cloudwatch list-metrics --namespace NAME`
3. **Check alarm state**: `aws cloudwatch describe-alarms --alarm-names NAME`
4. **Review metric data**: `aws cloudwatch get-metric-statistics`
5. **Check IAM permissions**: Verify `cloudwatch:*` or specific actions (see Permissions Required below)
6. **Verify log group** (for logs issues): `aws logs describe-log-groups --log-group-name-prefix NAME`
7. **Check query status** (for Logs Insights): `aws logs get-query-results --query-id ID`

## Common Issues

### Alarm Not Triggering

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Alarm stays OK | Threshold too high | Lower threshold |
| Alarm stays INSUFFICIENT_DATA | No metric data | Verify namespace/metric/dimensions |
| Alarm not alerting | Missing alarm-actions | Add SNS topic ARN to AlarmActions |
| Anomaly alarm band too wide | Deviation factor too high | Reduce factor (2→1.5) |
| Anomaly alarm always ALARM | Insufficient training data | Anomaly Detection needs ≥ 2 weeks of data |

### Metric Not Found

| Symptom | Cause | Resolution |
|---------|-------|------------|
| ResourceNotFound | Wrong namespace | Verify service namespace (AWS/EC2 vs CWAgent) |
| Wrong dimensions | Instance ID mismatch | Verify dimension values |
| Custom metric missing | Not published yet | Use put-metric-data to create |

### No Metric Data

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Empty datapoints | Time range wrong | Adjust start/end time |
| INSUFFICIENT_DATA alarm | Period mismatch | Use metric's publication period |
| No custom metrics | Not yet published | Call put-metric-data |

### Dashboard Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| DashboardNotFound | Name mismatch | Verify dashboard name |
| Invalid DashboardBody | JSON malformed | Validate JSON structure |
| ConcurrentModification | Race condition | Re-read current dashboard and retry |

### Logs Insights Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| No results returned | Time range too narrow | Extend start/end time |
| Query timeout | Too much data scanned | Narrow time range or add more filters |
| MalformedQueryException | Syntax error | Use `stats`, `filter`, `fields` correctly |
| Empty results with correct syntax | Log group name wrong | Verify log group via `aws logs describe-log-groups` |
| Rate limit exceeded | >5 concurrent queries | Wait and retry |

### Contributor Insights Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Rule created but no insights | No matching logs | Verify filter matches log schema in log group |
| "Invalid rule definition" | Schema mismatch | Check CloudWatchLogRule schema v1 |

## Permissions Required

| Action | Minimum IAM Permissions |
|--------|-------------------------|
| Create alarm | `cloudwatch:PutMetricAlarm` |
| Create composite alarm | `cloudwatch:PutCompositeAlarm` |
| View alarms | `cloudwatch:DescribeAlarms` |
| Delete alarm | `cloudwatch:DeleteAlarms` |
| Get metrics | `cloudwatch:GetMetricStatistics`, `cloudwatch:GetMetricData` |
| List metrics | `cloudwatch:ListMetrics` |
| Put custom metric | `cloudwatch:PutMetricData` |
| Manage dashboards | `cloudwatch:PutDashboard`, `cloudwatch:GetDashboard`, `cloudwatch:ListDashboards`, `cloudwatch:DeleteDashboards` |
| Start Logs Insights query | `logs:StartQuery` |
| Get query results | `logs:GetQueryResults` |
| Log group operations | `logs:DescribeLogGroups` |
| Manage Contributor Insights | `cloudwatch:PutInsightRule`, `cloudwatch:ListInsightRules`, `cloudwatch:DeleteInsightRules` |

## Alarm State Verification

```bash
# Check alarm state
aws cloudwatch describe-alarms --alarm-names MyAlarm --output json | jq '.MetricAlarms[0].StateValue'

# Check alarm history
aws cloudwatch describe-alarm-history --alarm-name MyAlarm --output json
```

## Metric Availability Check

```bash
# Check if metric exists
aws cloudwatch list-metrics --namespace AWS/EC2 --metric-name CPUUtilization --output json

# Get recent datapoints
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-xxx \
  --statistics Average \
  --period 60 \
  --start-time $(date -u -d '-15 minutes' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --output json
```

## Recovery Actions

| Error | Max Retries | Action |
|-------|-------------|--------|
| 5xx InternalError | 3 | Backoff 2s, 4s, 8s; HALT after 3 |
| 429 ThrottlingException | 3 | Exponential backoff |
| 400 InvalidParameterValue | 1 | Fix; retry once |
| 404 ResourceNotFound | 0 | HALT; verify namespace/metric |
| 403 LimitExceeded | 0 | HALT; delete unused alarms or request quota |
| MalformedQueryException | 1 | Fix Logs Insights query syntax; retry once |
| QueryTimeout | 0 | HALT; split time range, reduce query scope |

## Testing Alarms

```bash
# Force alarm state change (testing only)
aws cloudwatch set-alarm-state --alarm-name MyAlarm --state-value ALARM --state-reason "Testing" --output json
```