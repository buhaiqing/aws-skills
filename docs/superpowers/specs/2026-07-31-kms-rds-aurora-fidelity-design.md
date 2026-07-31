# Design: kms / rds / aurora — golden + CS + pe trim

**Date:** 2026-07-31  
**Skills:** `aws-kms-ops`, `aws-rds-ops`, `aws-aurora-ops`

## Scope

1. `golden-scenarios.yaml` ≥6 each  
2. `## Confirmation Strings` from rubric (keep KMS `PERMANENTLY DELETE` and RDS/Aurora `DELETE_NO_SNAPSHOT` literals as-is — A4/A14)  
3. SKILL Safety column: prefer `confirm=` where rubric uses it; keep special literals  
4. Compress `prompt-examples.md` ≤120 (link to cli/troubleshooting)  
5. last_updated 2026-07-31; keep versions; te_gate + golden_eval PASS  

## Non-goals

gcl-spec rewrite; README bumps; mass refs TE.
