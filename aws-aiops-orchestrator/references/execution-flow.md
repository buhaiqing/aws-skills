# Execution Flow — Pre-flight → Execute → Validate → Recover

The orchestrator follows the standard **Pre-flight → Execute → Validate →
Recover** pattern at the *orchestration* level, while each delegated skill
runs the same pattern at the *operation* level.

## Step 1 — Pre-flight

1. Parse user intent → identify scope, time window, action mode.
2. Resolve scope graph (which AWS resources are in scope).
3. Validate credentials via `{{env.*}}` checks; fail closed if missing.
4. Verify required `aws-*-ops` skills are available in runtime.
5. Decide **delegate plan**: ordered list of (skill, intent, params) tuples.
6. Surface assumptions to user before any read-heavy scan.

## Step 2 — Execute (Layered)

```
Intent → Layer 0 Routing
        ↓
        Layer 1 Data Collection (delegated read-only calls)
        ↓
        Layer 2 Detection (this skill analyzes collected data)
        ↓
        Layer 3 RCA (this skill correlates across services)
        ↓
        Layer 4 Decision (this skill chooses action tier)
        ↓
        Layer 5 Action (delegated write calls if AUTO_HEAL/confirmed)
        ↓
        Layer 6 Feedback (record outcome, update knowledge)
```

For each delegated call, use the dual-path pattern:
**AWS CLI** (`aws <svc> <cmd> --output json`) → fall back to **boto3** after
3 failures. Every command MUST use `--output json` (per CLAUDE.md).

## Step 3 — Validate

- Verify each delegated call returned expected shape (see delegate contract).
- Cross-check: do the collected signals agree? If not, escalate to
  `[AI_ASSIST]` instead of guessing.
- For any AUTO_HEAL action: confirm post-state matches expected state via
  a read-back call.

## Step 4 — Recover

| Error Type | Action |
|------------|--------|
| InvalidParameter (400) | Fix args; retry once |
| QuotaExceeded | HALT; report to user |
| Throttling (429) | Exponential backoff; max 3 retries |
| 5xx Internal | Retry 3x; then HALT |
| Cross-skill inconsistency | `[AI_ASSIST]`; present both findings |
| AUTO_HEAL fails 2x | Degrade to `[MANUAL]` (per README boundary) |
| Data deletion in scope | Block; force `[MANUAL]` |

## Human Confirmation (mandatory before destructive actions)

Per repo policy (Charter C5): any action in the `{delete, terminate,
deregister, detach, disable}` set requires explicit user confirmation,
even if the orchestrator classifies it as AUTO_HEAL. The orchestrator
MUST present the proposed action and wait for `confirm` before invoking
the delegated destructive skill call.

## Variable Convention Notes

- `{{u.action_mode}}` defaults:
  - `observe`  — read-only, no recommendations offered
  - `recommend` — analyze + suggest; no writes
  - `auto-heal` — execute `[AUTO_HEAL]` tier only; confirm before
    `[AI_ASSIST]` and `[MANUAL]`
  - `manual` — never auto-execute; full report only

- All output IDs use the standard formats:
  - Instance: `i-xxxxxxxxxxxxxxxxx`
  - ALB ARN: `arn:aws:elasticloadbalancing:...`
  - DB identifier: `db-XXXXXXXXXXXXXXXXXXXXXXXXXX`
  - Lambda: `arn:aws:lambda:...:function:<name>:<ver>`
