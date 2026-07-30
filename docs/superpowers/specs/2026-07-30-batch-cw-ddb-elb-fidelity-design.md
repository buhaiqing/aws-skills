# Design: Batch CLI fidelity — cloudwatch / dynamodb / elb

**Date:** 2026-07-30  
**Pattern:** Same as aws-ram-ops + aws-ec2-ops (surgical P0/P1; no mass rewrite of 2k+ line refs).

## Skills

| Skill | Why |
|-------|-----|
| `aws-cloudwatch-ops` | TE backlog; 236-line prompt-examples; no golden |
| `aws-dynamodb-ops` | TE backlog; no golden |
| `aws-elb-ops` | 316-line prompt-examples; high AIOps duplication risk |

## Per-skill acceptance (same bar)

1. Confirm tokens: `confirm=<OP> <id>` in SKILL + prompt-templates Confirmation Strings + golden
2. No invented metrics/CLI flag misuse (spot-fix P0s)
3. `prompt-examples.md` ≤ ~120 lines if present (link to cli/troubleshooting)
4. `golden-scenarios.yaml` ≥5 (read / confirmed destructive / no-confirm)
5. `te_gate --skill <name> --strict` PASS; SKILL ≤120
6. Version: bump patch only if SKILL/safety contract changes; else keep + last_updated

## Non-goals

Full TE trim of 2k+ reference trees; README mass sync unless version bumps.
