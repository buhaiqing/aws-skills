# GCL Prompt Templates — `aws-rds-ops`

> Specialization of the shared skeleton:
> [`aws-skill-generator/references/prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
>
> This file contains only the **service-specific deltas** for `aws-rds-ops`:
> Hard rules (substituted into the Critic template's `{skill.hard_rules}`),
> Confirmation strings, and Variable Convention deltas. The three canonical
> templates (Generator / Critic / Orchestrator) are referenced from the
> skeleton file; do not duplicate them here.

## Skill metadata (used by skeleton `{skill.*}` placeholders)

| Placeholder | Value |
|---|---|
| `{{skill.name}}` | `aws-rds-ops` |
| `{{skill.service}}` | `rds` |
| `{{skill.aws_cli_svc}}` | `rds` |
| `{{skill.max_iter}}` | `2` (from `metadata.gcl.max_iter` in SKILL.md frontmatter) |

## Hard rules (Critic template injection)

> These bullets are substituted into the Critic template's
> `{skill.hard_rules}` slot in `prompt-skeletons.md` §2.
> They run BEFORE the canonical generic Hard rules (A7 / A8 / A9 / A10).

```text
- Safety = 0 if `delete-db-instance` / `delete-db-cluster` was called
  with `--skip-final-snapshot` and no `DELETE_NO_SNAPSHOT <db-id>` literal
  in the trace (rule A5).
- Correctness = 0 if `delete-db-instance` was called while
  `DBInstanceStatus != "available"`.
- Safety = 0 if `delete-db-instance` was on a `env=prod`-tagged
  instance without `confirm=DELETE_PROD_DB <db-id>` in trace.
- Correctness = 0 if `delete-db-parameter-group` was called while any
  DB instance still references the group.
- Safety = 0 if `create-db-instance` / `create-db-cluster` had
  `MasterUserPassword` as a literal string instead of a Secrets
  Manager ARN (rule A9).
- Correctness = 0 if `restore-db-instance-to-point-in-time` had
  `RestoreTime` > `LatestRestorableTime`.
- Safety = 0 if `modify-db-instance` shrunk `AllocatedStorage` without
  `confirm=MODIFY_STORAGE_SHRINK <db-id>`.
- Correctness = 0 if `DBInstanceIdentifier` / `DBClusterIdentifier` /
  `DBSnapshotIdentifier` in the request was not echoed from a
  `describe-*` lookup (rule A8).
```

## Variable Convention (skill-specific deltas)
> Common placeholders (`{{user.*}}`, `{{env.*}}`, `{{output.*}}`)
> are defined once in `prompt-skeletons.md` §Variable convention.
> Only entries unique to this skill are listed below.

| Placeholder | Resolved from | Notes |
|---|---|---|
| `{{user.request}}` | agent runtime | sanitized; never includes secret env values |
| `{{user.safety_confirm}}` | explicit user confirmation | required for destructive ops; trace must record exact literal per operation |
| `{{user.region}}` | user input or `{{env.AWS_DEFAULT_REGION}}` | RDS is regional; mismatch → Correctness=0 (rule A7) |
| `{{user.password_secrets_manager_arn}}` | Secrets Manager ARN | required for `create-db-instance`; literal password refused (rule A9) |
| `{{env.AWS_ACCESS_KEY_ID}}` | runtime env | NEVER prompt user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | runtime env | NEVER log (rule A9) |
| `{{output.rubric}}` | `references/rubric.md` | injected as literal block |
| `{{output.generator_output}}` | previous Generator run | empty on iter 1 |
| `{{output.trace}}` | execution trace buffer | `command`, `args`, `exit_code`, `result` (masked), `post_state`, `errors` |
| `{{output.critic_scores}}` | previous Critic run | empty on iter 1 |
| `{{output.critic_blocking}}` | previous Critic run | empty on iter 1 |
| `{{output.iter}}` | Orchestrator counter | starts at 1 |
| `{{output.operation}}` | Orchestrator classification | one of the listed operation types |

## Changelog
| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Initial GCL prompt templates for `aws-rds-ops` (Phase 1, required, not pilot) |

---

> See [`prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
> for the canonical Generator / Critic / Orchestrator templates and the
> shared Variable Convention table.
