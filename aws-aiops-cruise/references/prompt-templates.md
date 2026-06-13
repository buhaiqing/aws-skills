# GCL Prompt Templates — aws-aiops-cruise

## Generator (G)

```
You execute aws-aiops-cruise read-only patrol.
Scope: {{user.resource_group}} or tag {{user.tag_key}}={{user.tag_value}}
Region: {{user.region}}
Scenario: {{user.scenario}}

Rules:
- First command: aws sts get-caller-identity --output json
- Only Describe/List/Get/lookup-events/get-metric-statistics
- Emit incidents per references/incident-schema.md
- Apply references/inference-rules.md in Phase 3
- Write JSON to audit-results/cruise-<run_id>.json

Do NOT self-score.
```

## Critic (C)

```
Audit a completed aws-aiops-cruise patrol trace.
User request is HIDDEN — judge rubric only.

Rubric: references/rubric.md
Trace: {{output.gcl_trace}}

Score each dimension 0 / 0.5 / 1.
If any write API in trace → Safety = 0 → ABORT.
If missing level/rule_id/dedup_key on incidents → Traceability ≤ 0.5.
```

## Orchestrator (O)

```
Terminate when:
- PASS: all dimensions meet threshold AND Safety = 1
- SAFETY_FAIL: Safety = 0
- MAX_ITER: iteration >= {{max_iter}} → return best-so-far

Persist: audit-results/gcl-trace-YYYYMMDD-HHMMSS.json
```
