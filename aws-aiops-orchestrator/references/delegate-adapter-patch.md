# AIOps Delegate Adapter Patch — v0.1

This document is the **canonical patch** applied to each `aws-*-ops` skill
to make it orchestrator-aware. Apply it verbatim; do not invent local
variants.

## 1. Why this patch exists

`aws-aiops-orchestrator` (this repo) routes cross-service intents to
specific `aws-*-ops` skills via a standardized envelope
(`aiops_delegate` → `aiops_context`). For a skill to be a
first-class delegate target, it must:

1. Recognize the `aiops_delegate:` block in incoming prompts.
2. Honor `idempotency_key` and `confirmation_token` on writes.
3. Always return an `aiops_context:` JSON block in its final response.
4. Tag any `references/` file extensions with
   `orchestrator_aware: true`.

## 2. The patch — drop-in section for every `SKILL.md`

Add the following section **at the end of `SKILL.md`**, just before the
`## Reference Index` section (or, if there is no such section, just
before the last `---` separator). Title it exactly:
`## AIOps Delegate Contract`.

```markdown
## AIOps Delegate Contract

This skill is orchestrator-aware. When invoked by
`aws-aiops-orchestrator`, it MUST honor the delegate contract.

### Recognition

If the incoming prompt contains an `aiops_delegate:` block (see
[aws-aiops-orchestrator/references/delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md)),
parse it and validate:

- `request_id` — non-empty string
- `parent_intent` — one of: health-check | rca | self-heal
  | cost-forecast | capacity-forecast | change-impact
  | compliance-scan | forensic
- `action_mode` — observe | recommend | auto-heal | manual
- `decision_tier` — AUTO_HEAL | AI_ASSIST | MANUAL
- `scope.resource_ids` — array (may be empty for discovery)

### Behavior rules

1. **Idempotency**: every write operation MUST accept an
   `idempotency_key` parameter. If the same key was executed within
   the last 24h, return the cached result with
   `aiops_context.status: "ok"` and
   `aiops_context.facts[*].deduplicated: true`.
2. **Confirmation gate**: any destructive operation (delete, terminate,
   deregister, detach, disable, rotate) MUST require a
   `confirmation_token`. If absent, refuse the operation and return:
   ```json
   {"aiops_context": {"status": "failed",
     "summary": "confirmation_token required for destructive op"}}
   ```
3. **Decision tier respect**:
   - `decision_tier: MANUAL` → never execute writes, return recommendations only.
   - `decision_tier: AI_ASSIST` → return recommendations; execute only
     if `confirmation_token` is present.
   - `decision_tier: AUTO_HEAL` → execute non-destructive writes
     directly; for destructive ones still require `confirmation_token`.
4. **Trace propagation**: every AWS CLI / boto3 call MUST include the
   `trace_id` from the delegate block in the User-Agent header
   (`User-Agent: aiops-orchestrator/<trace_id>`).
5. **Output format**: always include a final `aiops_context:` block in
   the response, even on failure. See Section 3 for schema.

### Frontmatter addition

Add the following keys to your `SKILL.md` YAML frontmatter (preserve
existing keys; add new ones):

```yaml
metadata:
  orchestrator_aware: true
  orchestrator_compat: ">=0.1.0"
  delegate:
    accepts: ["health-check", "rca", "self-heal", "change-impact"]
    produces_facts: ["metric", "log", "event", "config", "state", "finding"]
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true
```

### Cross-reference

This skill participates in the orchestrator's runbook library. See
[aws-aiops-orchestrator/references/runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md)
for which runbooks invoke this skill.
```

## 3. `aiops_context` schema (response side)

```json
{
  "aiops_context": {
    "skill": "<this skill name, e.g., aws-rds-ops>",
    "skill_version": "<from frontmatter metadata.version>",
    "request_id": "<echo from request>",
    "trace_id": "<echo from request>",
    "status": "ok | partial | failed",
    "summary": "<one-sentence headline>",
    "facts": [
      {
        "kind": "metric | log | event | config | state | cost | finding",
        "subject": "<resource id or arn>",
        "name": "<metric/event name>",
        "value": "<number | string | object>",
        "window": "<time window the value applies to>",
        "severity": "info | low | medium | high | critical",
        "tags": { "...": "..." },
        "deduplicated": false
      }
    ],
    "anomalies": [
      {
        "rule_id": "<CODE-NN>",
        "subject": "<resource id>",
        "description": "<human readable>",
        "first_seen": "<ISO-8601>",
        "confidence": 0.0
      }
    ],
    "recommendations": [
      {
        "tier": "AUTO_HEAL | AI_ASSIST | MANUAL",
        "action": "<verb phrase>",
        "rationale": "<why>",
        "blast_radius": ["<resource id>", "..."],
        "estimated_cost_delta_usd": 0.0,
        "rollback": "<how to undo>",
        "requires_confirm": true
      }
    ],
    "next_skill": "<optional>",
    "errors": [
      {"code": "<string>", "message": "<string>", "retryable": false}
    ]
  }
}
```

## 4. Per-skill `delegate:` block quick reference

Each skill's `metadata.delegate` block declares what it accepts and
produces. The orchestrator uses this to route without parsing SKILL.md.

| Skill | accepts | produces_facts | idempotency_ttl |
|-------|---------|----------------|-----------------|
| aws-elb-ops | health-check, rca, self-heal | metric, log, event, state | PT24H |
| aws-cloudwatch-ops | health-check, rca, capacity-forecast | metric, log | PT24H |
| aws-ec2-ops | health-check, rca, self-heal, change-impact | metric, state, event | PT24H |
| aws-rds-ops | health-check, rca, self-heal, change-impact | metric, state, event | PT24H |
| aws-vpc-ops | health-check, rca, change-impact | metric, log, config | PT24H |
| aws-acm-ops | health-check, self-heal | state, event | PT24H |
| aws-route53-ops | health-check, self-heal, change-impact | state | PT24H |
| aws-waf-ops | health-check, rca, self-heal | metric, log, config | PT24H |
| aws-autoscaling-ops | self-heal, capacity-forecast | state, metric | PT24H |
| aws-kms-ops | compliance-scan, change-impact | state, event | PT24H |
| aws-iam-ops | compliance-scan, change-impact | state, event | PT24H |
| aws-guardduty-ops | health-check, compliance-scan | finding | PT24H |
| aws-securityhub-ops | health-check, compliance-scan | finding | PT24H |
| aws-cloudtrail-ops | rca, change-impact, forensic | event | PT24H |
| aws-s3-ops | compliance-scan, change-impact, cost-forecast | config, state, cost | PT24H |
| aws-config-ops | compliance-scan, change-impact | config | PT24H |

## 5. Migration order

Apply the patch in this order to keep `git diff` reviewable:

1. P0 (core delegate targets): aws-cloudwatch-ops → aws-elb-ops →
   aws-ec2-ops → aws-rds-ops → aws-vpc-ops → aws-acm-ops →
   aws-route53-ops → aws-waf-ops
2. P1 (data sources & secondary executors): aws-cloudtrail-ops →
   aws-config-ops → aws-autoscaling-ops → aws-kms-ops → aws-iam-ops →
   aws-guardduty-ops → aws-securityhub-ops → aws-s3-ops
3. P2 (optional, on demand): the remaining skills.

Each skill: one PR, scoped to the SKILL.md change + frontmatter key
addition. No `references/` rewrite required for the basic contract.

## 6. Testing the patch

Smoke test per skill (can be run as an agent loop):

```
1. Invoke the skill with:
   aiops_delegate:
     request_id: test-001
     trace_id: smoke
     parent_intent: health-check
     action_mode: observe
     decision_tier: AI_ASSIST
     scope: { resource_ids: [], tags: { Env: dev } }
2. Verify response contains aiops_context block with status: "ok".
3. Invoke the skill with a destructive op but no confirmation_token;
   verify status: "failed" with the expected error.
4. Invoke with confirmation_token; verify write succeeds and the
   idempotency_key is logged in aiops_context.facts[*].tags.
```

## 7. Compatibility & versioning

- The orchestrator accepts any skill declaring
  `orchestrator_compat: ">=0.1.0"`. Higher versions must remain
  backward-compatible unless a major bump is negotiated.
- Breaking changes to the contract require:
  - Bumping `orchestrator_compat` major version.
  - Updating this document.
  - Notifying all `aws-*-ops` maintainers via the project's standard
    communication channel.
```

---

## Apply the patch

To apply this patch to a target skill:

1. Read its current `SKILL.md`.
2. Add the frontmatter keys (Section 2, "Frontmatter addition") to the
   `metadata:` block. Preserve all existing keys.
3. Append the `## AIOps Delegate Contract` section (Section 2) just
   before `## Reference Index` (or before the trailing `---`).
4. Update the skill's row in Section 4 above.
5. Run the smoke test (Section 6).

No `references/` changes are required for the basic contract. Skills
that need richer integration (e.g., publishing custom anomaly rules)
additionally add a `references/aiops-delegate.md` file, but that is
optional.