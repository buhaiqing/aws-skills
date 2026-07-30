# Design: aws-eventbridge-ops golden scenarios (L4 §16)

**Date:** 2026-07-30  
**Skill:** `aws-eventbridge-ops` v1.1.0  
**Scope:** Add `golden-scenarios.yaml` only — no SKILL.md / references edits.

## Gap

§16 requires every L1 skill to ship ≥5 golden scenarios. `aws-eventbridge-ops` has GCL rubric + prompts but **no** `golden-scenarios.yaml` (verified on disk). Peers `aws-ram-ops` / `aws-ec2-ops` already ship 6-scenario suites.

## Coverage matrix (minimum)

| Bucket | Min | This suite |
|--------|-----|------------|
| Read-only | ≥2 | list-rules, list-schedules |
| Confirmed destructive | ≥2 | delete-rule + confirm, delete-event-bus + confirm |
| Destructive missing confirm | ≥1 | delete-rule empty confirm → SAFETY_FAIL |
| Extra (pipes) | +1 | delete-pipe + confirm |

Tokens match SKILL Safety / rubric: `DELETE_RULE`, `DELETE_BUS`, `DELETE_PIPE`.

## Non-goals

- Fixing max_iter / Confirmation Strings / `put-event-bus` (separate P1 backlog)
- Real AWS execution (suite runs via `gcl_runner --self-test` stubs)
- Version bump / README sync (SKILL unchanged)

## Acceptance

1. File exists at `aws-eventbridge-ops/golden-scenarios.yaml` with ≥5 scenarios
2. `load_scenarios()` accepts all `expected_status` ∈ {PASS, SAFETY_FAIL, MAX_ITER}
3. `python3 scripts/golden_eval.py run --skill aws-eventbridge-ops ...` → 0 unmatched
