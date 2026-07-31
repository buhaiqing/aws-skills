# Design: High-risk identity/storage — golden + Confirmation Strings

**Date:** 2026-07-31  
**Skills:** `aws-iam-ops`, `aws-s3-ops`, `aws-vpc-ops`, `aws-lambda-ops`

## Scope (surgical)

1. Add `golden-scenarios.yaml` ≥6 each (2 read, ≥2 confirmed destructive, ≥1 no-confirm SAFETY_FAIL, ≥1 idempotent).
2. Add `## Confirmation Strings` to each `prompt-templates.md` from rubric literals.
3. Align SKILL.md Safety/Operations confirmation column to `confirm=<OP> <id>` where bare tokens exist.
4. `last_updated: 2026-07-31`; keep versions; SKILL ≤120; te_gate + golden_eval PASS.

## Non-goals

Mass pe/refs TE rewrite; gcl-spec edits; README version bumps unless required.
