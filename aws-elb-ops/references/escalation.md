# SLA Breach Escalation — Auto-Heal Failure Auto-Notify

_Lastest update: 2026-05-31_

This document defines escalation rules when auto-heal actions fail or SLA targets are breached.

---

## Escalation Levels

| Level | Condition | Action | Response Time |
|-------|-----------|--------|---------------|
| L0 | Auto-heal success within SLA | Log only | — |
| L1 | Auto-heal success but exceeded SLA | Log + notify | 15 min |
| L2 | Auto-heal failed 1x | Retry once | 15 min |
| L3 | Auto-heal failed 2x | Create ticket | 30 min |
| L4 | All targets unhealthy in region | PagerDuty page | 5 min |

## Escalation Matrix

| Scenario | L1 | L2 | L3 | L4 |
|----------|----|----|----|----|
| AH-01 Target re-registration | ⚠️ Slow | ↩️ Retry | 🆘 Ticket | — |
| AH-03 Cross-zone enable | — | ↩️ Retry | 🆘 Ticket | — |
| RC-01 502 error | ⚠️ Warn | ↩️ Retry | 🆘 Ticket | 📟 Page |
| RC-03 Unhealthy target | ⚠️ Warn | ↩️ Retry | 🆘 Ticket | 📟 Page |
| AH-08 DDoS mitigation | — | ↩️ Retry | 🆘 Ticket | 📟 Page |

## PagerDuty Integration

```bash
# Trigger PagerDuty event on L4 escalation
curl -X POST https://events.pagerduty.com/v2/enqueue \
  -H 'Content-Type: application/json' \
  -d '{
    "routing_key": "{{pagerduty_key}}",
    "event_action": "trigger",
    "payload": {
      "summary": "AIOps: L4 Escalation - All LB targets unhealthy",
      "severity": "critical",
      "source": "aws-elb-ops",
      "custom_details": {
        "lb_arn": "{{lb_arn}}",
        "scenario": "RC-03",
        "failed_heal_count": 2
      }
    }
  }'
```

## Jira Ticket Template (L3)

```
Summary: [AIOps] Auto-Heal Failed 2x - {{lb_name}}
Description:
  AIOps auto-heal attempted and failed for {{lb_name}}.
  Last attempt: {{timestamp}}
  Scenario: {{scenario}}
  Root cause: {{rca}}
  Recommended action: {{recommendation}}

Labels: aiops, auto-heal-failure
Priority: P2
```

## SNS Notification (L1-L2)

```bash
aws sns publish \
  --topic-arn arn:aws:sns:region:account:aiops-alerts \
  --message "{\"level\":\"L2\",\"scenario\":\"AH-01\",\"message\":\"Auto-heal failed 1x, retrying...\"}"
```

## Auto-Escalation Flow

```
Trigger: Auto-heal action fails
  ↓
Check retry count
  ↓
[Retry 0]: Execute action → success → log only
[Retry 1]: Execute action → success → L1 notify
[Retry 2]: Execute action → success → L1 notify
[Retry 2]: Execute action → FAIL → L3 create ticket
[All targets down]: → L4 page immediately
```