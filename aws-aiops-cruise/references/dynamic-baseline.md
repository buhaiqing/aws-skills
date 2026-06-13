# Dynamic Baseline — aws-aiops-cruise

## v1.1 approach (pragmatic)

Without a long-lived metrics store, dynamic baseline uses:

1. **Week-over-week (WoW)** — same 6h window vs 7 days ago (`get_wow_change()` in `_shared.py`)
2. **7-day linear trend** — capacity runbook (`capacity-planning.py`) estimates `days_to_critical`
3. **Topo baseline** — config drift via `aws-topo-discovery/scripts/baseline-manager.py`

## WoW escalation

| WoW % | Effect |
|-------|--------|
| > 30% | Bump finding to WARNING if static threshold not yet breached |
| > 50% | Adds +0.15 to `risk_score` |

Disable WoW: `daily-health-check.py --no-wow`

## Future (v1.2+)

- Persist rolling 30d metric snapshots under `.runtime/aws-aiops-cruise/metrics/`
- Z-score vs local baseline per resource/metric
- Integrate CloudWatch Anomaly Detection alarms as external baseline

## Retention

| Artifact | Path | Retention |
|----------|------|-----------|
| Patrol JSON | `audit-results/cruise-*.json` | 30 days (manual/cron cleanup) |
| Topo baseline | `infra-baseline/` (topo-discovery) | 90 days |

Cron cleanup example:

```bash
find audit-results -name 'cruise-*.json' -mtime +30 -delete
```
