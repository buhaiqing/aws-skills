# GCL Prompt Templates — `aws-cloudfront-ops`

> Specialization of the shared skeleton:
> [`aws-skill-generator/references/prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
>
> This file contains only the **service-specific deltas** for `aws-cloudfront-ops`:
> Hard rules (substituted into the Critic template's `{skill.hard_rules}`),
> Confirmation strings, and Variable Convention deltas. The three canonical
> templates (Generator / Critic / Orchestrator) are referenced from the
> skeleton file; do not duplicate them here.

## Skill metadata (used by skeleton `{skill.*}` placeholders)

| Placeholder | Value |
|---|---|
| `{{skill.name}}` | `aws-cloudfront-ops` |
| `{{skill.service}}` | `cloudfront` |
| `{{skill.aws_cli_svc}}` | `cloudfront` |
| `{{skill.max_iter}}` | `2` (from `metadata.gcl.max_iter` in SKILL.md frontmatter) |

## Hard rules (Critic template injection)

> These bullets are substituted into the Critic template's
> `{skill.hard_rules}` slot in `prompt-skeletons.md` §2.
> They run BEFORE the canonical generic Hard rules (A7 / A8 / A9 / A10).

```text
- Correctness = 0 if `delete-distribution` was called while
  `Enabled=true` (must disable first, poll for Deployed).
- Safety = 0 if `delete-distribution` was called without
  `confirm=DELETE_DISTRIBUTION <id>` in trace.
- Safety = 0 if `delete-distribution` was on prod-tagged
  distribution without `confirm=DELETE_PROD_DISTRIBUTION <id>`.
- Correctness = 0 if `delete-key-group` was called while any
  distribution references it.
- Correctness = 0 if `delete-origin-access-control` was called
  while any distribution uses it.
- Correctness = 0 if `delete-function` was called while any
  distribution associates it.
- Correctness = 0 if `update-distribution` was called without
  `If-Match` ETag (when the distribution already exists).
- Correctness = 0 if `create-invalidation` had `Paths.Quantity > 3000`
  or `Quantity=0`.
- Correctness = 0 if distribution id not echoed from
  `get-distribution` / `list-distributions` (rule A8).
- Correctness = 0 if `--region` is not `us-east-1` (rule A7;
  CloudFront is global).
```

## Variable Convention (skill-specific deltas)
> Common placeholders (`{{user.*}}`, `{{env.*}}`, `{{output.*}}`)
> are defined once in `prompt-skeletons.md` §Variable convention.
> Only entries unique to this skill are listed below.

| Placeholder | Resolved from | Notes |
|---|---|---|
| `{{user.request}}` | agent runtime | sanitized |
| `{{user.safety_confirm}}` | explicit user confirmation | required for destructive ops |
| `{{user.region}}` | user input or `{{env.AWS_DEFAULT_REGION}}` | CloudFront is global; canonical `us-east-1`; rule A7 |
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
| 1.0.0 | 2026-06-04 | Initial GCL prompt templates for `aws-cloudfront-ops` (Phase 1, required, not pilot) |

---

> See [`prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
> for the canonical Generator / Critic / Orchestrator templates and the
> shared Variable Convention table.
