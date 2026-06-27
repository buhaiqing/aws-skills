# GCL Prompt Templates — `aws-opensearch-ops`

> Specialization of the shared skeleton:
> [`aws-skill-generator/references/prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
>
> This file contains only the **service-specific deltas** for `aws-opensearch-ops`:
> Hard rules (substituted into the Critic template's `{skill.hard_rules}`),
> Confirmation strings, and Variable Convention deltas. The three canonical
> templates (Generator / Critic / Orchestrator) are referenced from the
> skeleton file; do not duplicate them here.

## Skill metadata (used by skeleton `{skill.*}` placeholders)

| Placeholder | Value |
|---|---|
| `{{skill.name}}` | `aws-opensearch-ops` |
| `{{skill.service}}` | `opensearch` |
| `{{skill.aws_cli_svc}}` | `opensearch` |
| `{{skill.max_iter}}` | `2` (from `metadata.gcl.max_iter` in SKILL.md frontmatter) |

## Hard rules (Critic template injection)

> These bullets are substituted into the Critic template's
> `{skill.hard_rules}` slot in `prompt-skeletons.md` §2.
> They run BEFORE the canonical generic Hard rules (A7 / A8 / A9 / A10).

```text
- Safety = 0 if `delete-domain` was called while `Processing=true`.
- Safety = 0 if `delete-domain` was on a `env=prod`-tagged domain without
  `confirm=DELETE_PROD_DOMAIN <domain-name>` in trace.
- Safety = 0 if `delete-ingestion` was called while `Status="RUNNING"` without
  `confirm=DELETE_RUNNING_INGESTION <pipeline-name>` in trace.
- Correctness = 0 if `upgrade-domain` target version not in
  `get-compatible-versions` list.
- Safety = 0 if `create-domain` had `MasterUserPassword` as a literal string
  in trace (rule A9).
- Correctness = 0 if `DomainName` / `PipelineName` / `VpcEndpointId` in the
  request was not echoed from a `describe-*` lookup (rule A8).
```

## Variable Convention (skill-specific deltas)
> Common placeholders (`{{user.*}}`, `{{env.*}}`, `{{output.*}}`)
> are defined once in `prompt-skeletons.md` §Variable convention.
> Only entries unique to this skill are listed below.

| Placeholder | Resolved from | Notes |
|---|---|---|
| `{{user.request}}` | agent runtime | sanitized; never includes secret env values |
| `{{user.safety_confirm}}` | explicit user confirmation | required for destructive ops; trace must record exact literal per operation |
| `{{user.region}}` | user input or `{{env.AWS_DEFAULT_REGION}}` | OpenSearch is regional; mismatch -> Correctness=0 (rule A7) |
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
| 1.0.0 | 2026-06-08 | Initial GCL prompt templates for `aws-opensearch-ops` (Phase 1, required, not pilot) |

---

> See [`prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
> for the canonical Generator / Critic / Orchestrator templates and the
> shared Variable Convention table.
