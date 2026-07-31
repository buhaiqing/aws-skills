# GCL Prompt Templates — `aws-eventbridge-ops`

> Specialization of the shared skeleton:
> [`aws-skill-generator/references/prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
>
> This file contains only the **service-specific deltas** for `aws-eventbridge-ops`:
> Hard rules (substituted into the Critic template's `{{skill.hard_rules}}`),
> Confirmation strings, and Variable Convention deltas. The three canonical
> templates (Generator / Critic / Orchestrator) are referenced from the
> skeleton file; do not duplicate them here.

## Skill metadata (used by skeleton `{{skill.*}}` placeholders)

| Placeholder | Value |
|---|---|
| `{{skill.name}}` | `aws-eventbridge-ops` |
| `{{skill.service}}` | `eventbridge` |
| `{{skill.aws_cli_svc}}` | `events|scheduler|pipes` |
| `{{skill.max_iter}}` | `3` (from `metadata.gcl.max_iter` in SKILL.md frontmatter) |

## Hard rules (Critic template injection)

> These bullets are substituted into the Critic template's
> `{{skill.hard_rules}}` slot in `prompt-skeletons.md` §2.
> They run BEFORE the canonical generic Hard rules (A7 / A8 / A9 / A10).

```text
- Safety = 0 if missing `confirm=` for destructive ops (see Confirmation Strings)
- Safety = 0 if `delete-rule` without `list-targets-by-rule` + `remove-targets` first (EB1)
- Safety = 0 if `delete-event-bus` with remaining rules (EB2)
- Safety = 0 if `delete-connection` while API destinations reference it (EB3)
- Safety = 0 if active schedule delete without `DELETE_SCHEDULE_ACTIVE` (EB4)
- Safety = 0 if pipe delete/source-target change without token (EB5)
- Safety = 0 if `delete-archive` without token (EB6)
- Safety = 0 if `put-permission` Principal=* without `BUS_PERMISSION_PUBLIC` (EB7)
- Correctness = 0 if delete/disable ManagedBy rule (EB8)
- Correctness = 0 if no describe/list echo-back (A8) or region mismatch (A7)
- Safety = 0 if ApiKeyValue/Password/ClientSecret unmasked (A9); Traceability = 0 if sts not first (A10)
```

## Variable Convention (skill-specific deltas)
> Common placeholders (`{{user.*}}`, `{{env.*}}`, `{{output.*}}`)
> are defined once in `prompt-skeletons.md` §Variable convention.
> Only entries unique to this skill are listed below.

| Placeholder | Source | Notes |
|---|---|---|
| `{{user.safety_confirm}}` | user | `confirm=<OP> <id>` (EB tokens) |
| `{{user.region}}` | user or env | A7 |

---

## Confirmation Strings

| Operation | Confirmation token |
|---|---|
| `delete-rule` | `confirm=DELETE_RULE <name>` |
| `remove-targets` | `confirm=REMOVE_TARGETS <rule>` |
| `put-rule` (modify pattern on active) | `confirm=MODIFY_RULE <name>` |
| `delete-event-bus` | `confirm=DELETE_BUS <name>` |
| `delete-schedule` | `confirm=DELETE_SCHEDULE <name>` |
| `delete-schedule` (invoked last hour) | `confirm=DELETE_SCHEDULE_ACTIVE <name>` |
| `delete-pipe` | `confirm=DELETE_PIPE <name>` |
| `update-pipe` (Source/Target) | `confirm=UPDATE_PIPE <name>` |
| `delete-archive` | `confirm=DELETE_ARCHIVE <name>` |
| `delete-api-destination` | `confirm=DELETE_API_DEST <name>` |
| `delete-connection` | `confirm=DELETE_CONNECTION <name>` |
| `put-permission` Principal `*` | `confirm=BUS_PERMISSION_PUBLIC <bus>` |

> See [`prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
> for the canonical Generator / Critic / Orchestrator templates and the
> shared Variable Convention table.
