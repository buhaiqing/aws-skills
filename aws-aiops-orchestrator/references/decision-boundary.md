# Decision Boundary & Detection Rules Summary

## Detection Rule Library (summary)

See [`detection-rules.md`](detection-rules.md) for the full library. Each rule has:
`(service, metric_or_event, condition, window, severity, default_decision)`.

Categories:
- **Fault** — error rate, latency, unhealthy target, connection exhaustion
- **Predictive** — quota exhaustion, cert expiry, capacity saturation
- **Cost** — service cost anomaly, idle resources, RI coverage drop
- **Security** — GuardDuty CRITICAL, Config non-compliance, public S3/port
- **Change** — config drift, unexpected tag mutation, IAM policy changes

Default thresholds are **baselines** — Layer 2 MUST adjust against the
30-day per-resource baseline (collected on first scan, refreshed weekly).

## Decision Boundary (inherited from README §AIOps Decision Types)

| Label | When | Orchestrator Behavior |
|-------|------|----------------------|
| `[AUTO_HEAL]` | Target re-register, EC2 reboot, cross-zone enable, cert renew, compliance fix | Execute via delegated skill without prompt, but log the action |
| `[AI_ASSIST]` | Health check tuning, capacity scaling, SG change, first-seen anomaly | Present plan + diff; require `confirm` |
| `[MANUAL]` | Data deletion, cross-account, cost > $100/mo, blast radius > 5 prod resources | Stop; full report only |

**Override**: if the user explicitly states `action_mode=auto-heal` but the
incident is in the `[MANUAL]` tier, the orchestrator MUST downgrade to
`[AI_ASSIST]` and ask for confirmation regardless.
