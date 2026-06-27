# GCL Prompt Templates — `aws-dynamodb-ops`

> Specialization of the shared skeleton:
> [`aws-skill-generator/references/prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
>
> This file contains only the **service-specific deltas** for `aws-dynamodb-ops`:
> Hard rules (substituted into the Critic template's `{skill.hard_rules}`),
> Confirmation strings, and Variable Convention deltas. The three canonical
> templates (Generator / Critic / Orchestrator) are referenced from the
> skeleton file; do not duplicate them here.

## Skill metadata (used by skeleton `{skill.*}` placeholders)

| Placeholder | Value |
|---|---|
| `{{skill.name}}` | `aws-dynamodb-ops` |
| `{{skill.service}}` | `dynamodb` |
| `{{skill.aws_cli_svc}}` | `dynamodb` |
| `{{skill.max_iter}}` | `2` (from `metadata.gcl.max_iter` in SKILL.md frontmatter) |

## Hard rules (Critic template injection)

> These bullets are substituted into the Critic template's
> `{skill.hard_rules}` slot in `prompt-skeletons.md` §2.
> They run BEFORE the canonical generic Hard rules (A7 / A8 / A9 / A10).

```text
- Safety = 0 if `delete-table` was called without
  `confirm=DELETE_TABLE <table-name>` in trace.
- Correctness = 0 if `delete-table` was called while
  `TableStatus != "ACTIVE"`.
- Correctness = 0 if `delete-table` was called while
  `list-event-source-mappings` (Streams consumers) returned non-empty
  without `confirm=DELETE_TABLE_WITH_TRIGGERS <table>`.
- Correctness = 0 if `delete-table` was called while the table has
  GSIs/LSIs (rubric demands pre-flight index deletion).
- Safety = 0 if `update-table` had `GlobalSecondaryIndexUpdates: REMOVE`
  without `confirm=DELETE_GSI <table>:<index>`.
- Safety = 0 if `update-time-to-live` (enable) without
  `confirm=ENABLE_TTL <table>:<attr>`.
- Correctness = 0 if `update-time-to-live` (enable) had TTL attribute
  not of `Number` type.
- Safety = 0 if `put-item` / `update-item` had literal secrets in
  secret-named attributes (rule A9).
- Correctness = 0 if `TableName` / `IndexName` not echoed from a
  `describe-table` / `list-tables` lookup (rule A8).
```

## Variable Convention (skill-specific deltas)
> Common placeholders (`{{user.*}}`, `{{env.*}}`, `{{output.*}}`)
> are defined once in `prompt-skeletons.md` §Variable convention.
> Only entries unique to this skill are listed below.

| Placeholder | Resolved from | Notes |
|---|---|---|
| `{{user.request}}` | agent runtime | sanitized |
| `{{user.safety_confirm}}` | explicit user confirmation | required for destructive ops |
| `{{user.region}}` | user input or `{{env.AWS_DEFAULT_REGION}}` | DynamoDB is regional; rule A7 |
| `{{env.AWS_ACCESS_KEY_ID}}` | runtime env | NEVER prompt user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | runtime env | NEVER log (rule A9) |
| `{{output.rubric}}` | `references/rubric.md` | injected as literal block |
| `{{output.generator_output}}` | previous Generator run | empty on iter 1 |
| `{{output.trace}}` | execution trace buffer | masked |
| `{{output.critic_scores}}` | previous Critic run | empty on iter 1 |
| `{{output.critic_blocking}}` | previous Critic run | empty on iter 1 |
| `{{output.iter}}` | Orchestrator counter | starts at 1 |
| `{{output.operation}}` | Orchestrator classification | one of the listed operation types |

## Changelog
| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Initial GCL prompt templates for `aws-dynamodb-ops` (Phase 1, required, not pilot) |

---

> See [`prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
> for the canonical Generator / Critic / Orchestrator templates and the
> shared Variable Convention table.
