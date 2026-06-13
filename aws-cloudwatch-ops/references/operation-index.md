# Operation Index — CloudWatch

_Latest update: 2026-06-13_

Full operation map for `aws-cloudwatch-ops`. SKILL.md `## Scope` is the safety-gate summary; this file is the routing table.

> **Bidirectional link**: [SKILL.md](../SKILL.md) → `## Scope`

## Index

| Operation | CLI / API | Safety Gate | Orchestrator | Detail |
|-----------|-----------|-------------|--------------|--------|
| Create Alarm | `put-metric-alarm` | Warn if no `--alarm-actions` | health-check | [aws-cli-usage.md](aws-cli-usage.md) |
| Composite Alarm | `put-composite-alarm` | — | health-check | [aws-cli-usage.md](aws-cli-usage.md) |
| Anomaly Detection | `put-metric-alarm` + band | ≥14d data pre-flight | rca | [aws-cli-usage.md](aws-cli-usage.md) |
| Metric Math Alarm | `put-metric-alarm` + `--metrics` | Warn if no actions | rca | [aws-cli-usage.md §Metric Math](aws-cli-usage.md#metric-math-alarm-aiops-error-rate-) |
| Delete Alarm | `delete-alarms` | **confirm** `DELETE_ALARMS <names>` | — | [aws-cli-usage.md](aws-cli-usage.md) |
| List Metrics / Alarms | `list-metrics`, `describe-alarms` | — | health-check | [aws-cli-usage.md](aws-cli-usage.md) |
| Get Metric Data | `get-metric-data` | — | rca | [aws-cli-usage.md](aws-cli-usage.md) |
| FORECAST | `get-metric-data` + `FORECAST()` | — | capacity-forecast | [aiops-scenarios.md](aiops-scenarios.md) |
| Logs Insights | `logs start-query` + poll | — | rca | [aws-cli-usage.md](aws-cli-usage.md) |
| Contributor Insights | `put-insight-rule` | — | rca | [aws-cli-usage.md](aws-cli-usage.md) |
| Delete Insight Rule | `delete-insight-rules` | **confirm** | — | [aws-cli-usage.md](aws-cli-usage.md) |
| Create Dashboard | `put-dashboard` | — | health-check | [aws-cli-usage.md](aws-cli-usage.md) |
| Delete Dashboard | `delete-dashboards` | **confirm** `DELETE_DASHBOARD <name>` | — | [aws-cli-usage.md](aws-cli-usage.md) |
| Set Log Retention | `put-retention-policy` | **confirm** (data loss) | — | [aws-cli-usage.md](aws-cli-usage.md) |
| Synthetics Canary | `synthetics create-canary` | delete: **confirm** | health-check | [aws-cli-usage.md](aws-cli-usage.md) |
| Diagnose Alarm | `describe-alarms` + history | — | rca | [troubleshooting.md](troubleshooting.md) |
| ELB Alarm Templates | templates | delegate ELB ARNs first | rca, capacity-forecast | [elb-monitoring-templates.md](elb-monitoring-templates.md) |
| ELB AIOps Dashboard | `put-dashboard` + asset | — | health-check | [../assets/elb-aiops-dashboard.json](../assets/elb-aiops-dashboard.json) |
| Cost / RCA Scenarios | billing + correlate | — | rca, capacity-forecast | [aiops-scenarios.md](aiops-scenarios.md) |
| Auto-Heal Feedback | `logs put-log-events` | — | — | [feedback-loop.md](feedback-loop.md) |

FinOps pricing: [core-concepts.md §FinOps](core-concepts.md#finops-cost-management).
