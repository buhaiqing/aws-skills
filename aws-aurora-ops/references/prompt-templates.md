# GCL Prompt Templates — `aws-aurora-ops`

> Specialization of the shared skeleton:
> [`aws-skill-generator/references/prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
>
> This file contains only the **service-specific deltas** for `aws-aurora-ops`:
> Hard rules (substituted into the Critic template's `{skill.hard_rules}`),
> Confirmation strings, and Variable Convention deltas. The three canonical
> templates (Generator / Critic / Orchestrator) are referenced from the
> skeleton file; do not duplicate them here.

## Skill metadata (used by skeleton `{skill.*}` placeholders)

| Placeholder | Value |
|---|---|
| `{{skill.name}}` | `aws-aurora-ops` |
| `{{skill.service}}` | `aurora` |
| `{{skill.aws_cli_svc}}` | `aurora` |
| `{{skill.max_iter}}` | `2` (from `metadata.gcl.max_iter` in SKILL.md frontmatter) |

## Hard rules (Critic template injection)

> These bullets are substituted into the Critic template's
> `{skill.hard_rules}` slot in `prompt-skeletons.md` §2.
> They run BEFORE the canonical generic Hard rules (A7 / A8 / A9 / A10).

```text
- Safety = 0 if delete-db-cluster skip snapshot without DELETE_NO_SNAPSHOT (A5)
- Safety = 0 if failover/backtrack without confirmation
- Safety = 0 if literal MasterUserPassword in trace (A9)
- Correctness = 0 if DBClusterIdentifier not from describe-* (A8)
- Correctness = 0 if region mismatch (A7)
- Traceability = 0 if sts not first command (A10)
```

## Variable Convention (skill-specific deltas)
> Common placeholders (`{{user.*}}`, `{{env.*}}`, `{{output.*}}`)
> are defined once in `prompt-skeletons.md` §Variable convention.
> Only entries unique to this skill are listed below.

| Placeholder | Source | Notes |
|---|---|---|
| `{{user.request}}` | agent runtime | sanitized |
| `{{user.safety_confirm}}` | user confirmation | required for destructive ops |
| `{{user.region}}` | user or `{{env.AWS_DEFAULT_REGION}}` | rule A7 |
| `{{user.password_secrets_manager_arn}}` | Secrets Manager | required for create-db-cluster |
| `{{env.AWS_ACCESS_KEY_ID}}` | runtime env | fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | runtime env | never log |
| `{{output.*}}` | GCL loop | rubric, trace, scores |

## Changelog
| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-13 | Initial templates for `aws-aurora-ops` |

---

> See [`prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
> for the canonical Generator / Critic / Orchestrator templates and the
> shared Variable Convention table.
