# GCL Rubric (Phase 2 — Placeholder)

This rubric is a **placeholder** for full GCL §11 integration.
The 5 standard dimensions from AGENTS.md §11.3 apply:

| Dimension | Scale | Default Threshold |
|-----------|-------|-------------------|
| Correctness | 0/0.5/1 | >= 0.5 |
| Safety | 0/1 | = 1 |
| Idempotency | 0/0.5/1 | >= 0.5 |
| Traceability | 0/0.5/1 | >= 0.5 |
| Spec Compliance | 0/0.5/1 | >= 0.5 |

## Per Sub-Mode

| Sub-Mode | Correctness | Safety | Idempotency | Traceability | Spec Compliance |
|----------|-------------|--------|-------------|--------------|-----------------|
| scan-topo | Verify output format | Read-only gate | Same input -> same output | CLI cmds captured | Field coverage |
| export-hcl | Field mapping accuracy | No sensitive leak | ID stability | manifest.json complete | Schema compliance |
| baseline | Directory structure | No data deletion | Overwrite idempotent | manifest per baseline | Retention policy |
| baseline-diff | Diff accuracy | Read-only diff | Same diff per input | Report includes timestamps | Risk rating |

## AWS-Specific Safety Rules

| Rule | Check | On Fail |
|------|-------|---------|
| S1 | No `create-*`, `delete-*`, `modify-*` in trace | Safety = 0 |
| S2 | `AKIA*` / Secret Key never in output | Safety = 0 |
| S3 | `sts get-caller-identity` as first command | Traceability = 0 |
| S4 | `--region` matches `{{env.AWS_DEFAULT_REGION}}` | Correctness -= 0.5 |
| S5 | Resource IDs echoed back from `describe-*` | Correctness -= 0.5 |

> **TODO**: Integrate with `scripts/gcl_runner.py` per AGENTS.md §11 workflow.
