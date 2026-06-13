# Orchestrator Integration — Producer Contract

`aws-aiops-cruise` is a **producer** of patrol findings. `aws-aiops-orchestrator` is the **consumer** for escalation.

## When to escalate

| Condition | Action |
|-----------|--------|
| ≥ 3 CRITICAL incidents | Set `aiops_context.next_skill = aws-aiops-orchestrator` |
| Emergency + cross-service symptom | User loads orchestrator with `parent_intent=rca` |
| Pre-launch FAIL | Manual review; do not auto-heal |

## Output envelope

Every patrol script prints and persists:

```json
{
  "aiops_context": {
    "skill": "aws-aiops-cruise",
    "request_id": "<run_id>",
    "trace_id": "<12-char>",
    "status": "ok | partial | failed",
    "summary": "...",
    "facts": [{ "kind": "finding", "subject": "...", ... }],
    "facts_info": [{ "kind": "finding", "severity": "info", ... }],
    "anomalies": [{ "rule_id": "...", "confidence": 0.85 }],
    "recommendations": [{ "tier": "AI_ASSIST | MANUAL", "action": "..." }],
    "next_skill": "aws-aiops-orchestrator | null"
  }
}
```

Schema aligns with [`aws-aiops-orchestrator/references/delegate-routing.md`](../../aws-aiops-orchestrator/references/delegate-routing.md) §2.2 and §8 (cross-product skills).

## Orchestrator → Cruise (future)

Orchestrator may invoke cruise via delegate block:

```yaml
aiops_delegate:
  parent_intent: health-check
  target_skill: aws-aiops-cruise
  action_mode: observe
  scope:
    region: us-east-1
    tags: { Environment: production }
  parameters:
    scenario: daily_check
```

Cruise MUST honor `action_mode=observe` (never write).

## Incident → Fact mapping

| incident field | fact field |
|----------------|------------|
| `resource_id` | `subject` |
| `rule_id` | `name` |
| `current_value` | `value` |
| `level` | `severity` (lowercase) |

Built by `runbooks/scripts/_report.py` → `build_aiops_context()`.

- **`facts`**: WARNING and CRITICAL only (orchestrator escalation signal).
- **`facts_info`**: INFO-level findings, capped at 50 (audit trail without noise in `facts`).
