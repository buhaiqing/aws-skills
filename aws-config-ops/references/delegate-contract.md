# AIOps Delegate Contract

Full spec: [`aws-aiops-orchestrator/references/delegate-routing.md`](https://github.com/your-org/aws-skills/blob/main/aws-aiops-orchestrator/references/delegate-routing.md) and [`runbook-recipes.md`](https://github.com/your-org/aws-skills/blob/main/aws-aiops-orchestrator/references/runbook-recipes.md).

## Recognition

If the incoming prompt contains an `aiops_delegate:` block, parse and validate:

- `request_id` — non-empty string
- `parent_intent` — one of: health-check | rca | self-heal | cost-forecast | capacity-forecast | change-impact | compliance-scan | forensic
- `action_mode` — observe | recommend | auto-heal | manual
- `decision_tier` — AUTO_HEAL | AI_ASSIST | MANUAL
- `scope.resource_ids` — array (may be empty for discovery)

## Behavior rules

| Rule | Description |
|------|-------------|
| **Idempotency** | Every write op MUST accept `idempotency_key`. If same key executed within 24h, return cached result with `aiops_context.status: "ok"` and `aiops_context.facts[*].deduplicated: true` |
| **Confirmation gate** | Any destructive op (delete, terminate, deregister, detach, disable, rotate) MUST require `confirmation_token`. If absent, refuse and return `aiops_context.status: "failed"` with `"confirmation_token required for destructive op"` |
| **Decision tier respect** | `MANUAL` → no writes, recommendations only. `AI_ASSIST` → recommendations; execute only with `confirmation_token`. `AUTO_HEAL` → execute non-destructive writes directly; destructive still require `confirmation_token` |
| **Trace propagation** | Every AWS CLI / boto3 call MUST include `trace_id` from delegate block in User-Agent header (`User-Agent: aiops-orchestrator/<trace_id>`) |
| **Output format** | Always include a final `aiops_context:` JSON block in response, even on failure |

## Example response block

```json
{
  "aiops_context": {
    "request_id": "...",
    "status": "ok",
    "facts": [
      {"type": "config_recorder", "id": "...", "state": "ACTIVE"}
    ],
    "decision_tier_used": "AI_ASSIST"
  }
}
```
