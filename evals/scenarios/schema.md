# Golden Scenario Schema

Authoritative schema for ADR-0001 M1 Phase A rich evidence scenarios.
Phase A runner asserts only `expected_status`; optional rich fields are
documented for humans and future shadow assertions (M2).

## Dual-read resolution

`golden_eval.resolve_scenarios_path(skill)` picks the source file:

1. **Preferred:** `evals/scenarios/<skill>/scenarios.yaml` (rich source)
2. **Fallback:** `<skill>/golden-scenarios.yaml` (thin L4 §16 entry)

Example: for `aws-ec2-ops`, prefer
`evals/scenarios/aws-ec2-ops/scenarios.yaml`; if absent, use
`aws-ec2-ops/golden-scenarios.yaml`.

## Top-level document

```yaml
---
skill: aws-<svc>-ops
description: |          # optional human summary
  Golden suite for aws-<svc>-ops vX.Y.Z.
scenarios:
  - id: ...
    # fields below
```

## Required fields (per scenario)

| Field | Type | Description |
|---|---|---|
| `id` | `str` | Unique scenario identifier within the skill |
| `description` | `str` | One-line human description |
| `request` | `str` | Natural-language user request replayed by GCL |
| `expected_status` | enum | `PASS` \| `SAFETY_FAIL` \| `MAX_ITER` |

## Optional fields (per scenario)

| Field | Type | Default | Description |
|---|---|---|---|
| `user_region` | `str` | `""` | AWS region passed to the runner |
| `safety_confirm` | `str` | `""` | Confirmation token for destructive ops |
| `risk` | enum | `""` | `read-only` \| `write` \| `destructive` \| `recovery` \| `secret-redaction` |
| `preconditions` | `list[str]` | `[]` | Describe/quota checks before execution |
| `expected_plan` | `str` | `""` | Expected Planner action summary (Phase A: not asserted) |
| `expected_gate` | `str` | `""` | Expected safety/GCL gate behavior |
| `expected_outcome` | `str` | `""` | Human-readable outcome semantics |
| `forbidden_actions` | `list[str]` | `[]` | Forbidden CLI subcommands or flags |

Unknown keys in a scenario mapping are ignored by `load_scenarios()`.

## `expected_status` values (Phase A)

| Value | Meaning |
|---|---|
| `PASS` | GCL terminates with all rubric thresholds met |
| `SAFETY_FAIL` | Safety dimension = 0 → ABORT |
| `MAX_ITER` | Iteration cap reached without PASS |

`BLOCKED` and `COMPENSATED` are reserved for Phase B.

## High-risk batch run

```bash
python3 scripts/golden_eval.py run --all-high-risk --out audit-results/golden/high-risk.json
```

Runs `aws-ec2-ops`, `aws-s3-ops`, `aws-iam-ops`, `aws-rds-ops`, `aws-kms-ops`
via dual-read resolution. Aggregate `--out` ending in `.json` writes a single
file; otherwise `--out` is treated as a directory for per-skill JSON.
