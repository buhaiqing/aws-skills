# GCL Prompt Templates — `aws-guardduty-ops`

> Specialization of the shared skeleton:
> [`aws-skill-generator/references/prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
>
> This file contains only the **service-specific deltas** for `aws-guardduty-ops`:
> Hard rules (substituted into the Critic template's `{skill.hard_rules}`),
> Confirmation strings, and Variable Convention deltas. The three canonical
> templates (Generator / Critic / Orchestrator) are referenced from the
> skeleton file; do not duplicate them here.

## Skill metadata (used by skeleton `{skill.*}` placeholders)

| Placeholder | Value |
|---|---|
| `{{skill.name}}` | `aws-guardduty-ops` |
| `{{skill.service}}` | `guardduty` |
| `{{skill.aws_cli_svc}}` | `guardduty` |
| `{{skill.max_iter}}` | `2` (from `metadata.gcl.max_iter` in SKILL.md frontmatter) |

## Hard rules (Critic template injection)

> These bullets are substituted into the Critic template's
> `{skill.hard_rules}` slot in `prompt-skeletons.md` §2.
> They run BEFORE the canonical generic Hard rules (A7 / A8 / A9 / A10).

```text
- Safety = 0 if any destructive `delete-*` op is missing the literal
  `confirm=DELETE_GUARDDUTY_<RESOURCE> <id>` token in the trace, OR
  if {{output.safety_confirm_token}} is empty.
- Safety = 0 if `disable-guardduty` is missing `confirm=DISABLE_GUARDDUTY <detector-id>`.
```

## Supported Operations (Generator reference)
- list-detectors, describe-detector
- create-filter, list-filters, get-filter, delete-filter
- create-ip-set, list-ip-sets, get-ip-set, delete-ip-set
- create-threat-intel-set, list-threat-intel-sets, get-threat-intel-set,
  delete-threat-intel-set
- list-findings, get-findings
- enable-guardduty, disable-guardduty
- create-member, list-members, delete-member
- create-admin, delete-admin

## Confirmation Strings
- `delete-filter`:           `confirm=DELETE_GUARDDUTY_FILTER <name>`
- `delete-detector`:         `confirm=DELETE_GUARDDUTY_DETECTOR <detector-id>`
- `delete-ip-set`:           `confirm=DELETE_GUARDDUTY_IPSET <ip-set-id>`
- `delete-threat-intel-set`: `confirm=DELETE_GUARDDUTY_THREATINTELSET <threat-intel-set-id>`
- `delete-member`:           `confirm=DELETE_GUARDDUTY_MEMBER <account-id>`
- `delete-admin`:            `confirm=DELETE_GUARDDUTY_ADMIN <account-id>`
- `disable-guardduty`:       `confirm=DISABLE_GUARDDUTY <detector-id>`

## Variable Convention (skill-specific deltas)
> Common placeholders (`{{user.*}}`, `{{env.*}}`, `{{output.*}}`)
> are defined once in `prompt-skeletons.md` §Variable convention.
> Only entries unique to this skill are listed below.

| Placeholder | Resolved from | Notes |
|---|---|---|
| `{{user.request}}` | agent runtime | sanitized; never includes secret env values |
| `{{user.region}}` | user input or `{{env.AWS_DEFAULT_REGION}}` | routed to Critic as `{{output.requested_region}}` (see §7.1) |
| `{{user.safety_confirm}}` | explicit user confirmation | routed to Critic as `{{output.safety_confirm_token}}`; required for destructive ops |
| `{{user.detector_id}}` | user input | GuardDuty detector UUID |
| `{{user.resource_name}}` | user input | filter / ip-set / threat-intel-set name |
| `{{user.ip_set_id}}` | user input | ip-set UUID |
| `{{user.threat_intel_set_id}}` | user input | threat-intel-set UUID |
| `{{user.finding_ids}}` | user input | list of finding IDs |
| `{{env.AWS_ACCESS_KEY_ID}}` | runtime env | NEVER prompt user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | runtime env | NEVER prompt user; NEVER log (rule A9) |
| `{{env.AWS_DEFAULT_REGION}}` | runtime env | fallback for `{{user.region}}` |
| `{{output.rubric}}` | `references/rubric.md` of active skill | injected as literal block |
| `{{output.generator_output}}` | previous Generator run | empty on iter 1 |
| `{{output.trace}}` | execution trace buffer | command/args/exit_code/result/errors |
| `{{output.critic_scores}}` | previous Critic run | empty on iter 1 |
| `{{output.critic_blocking}}` | previous Critic run | empty on iter 1 |
| `{{output.iter}}` | Orchestrator counter | starts at 1 |
| `{{output.operation}}` | Orchestrator classification | one of the listed operation types |
| `{{output.cli_command}}` | Generator-resolved CLI invocation | for self-test or template render |
| `{{output.boto3_code}}` | Generator-resolved boto3 invocation | for fallback path |
| `{{output.requested_region}}` | Orchestrator from `{{user.region}}` | Critic region-check target (rule A7) |
| `{{output.safety_confirm_token}}` | Orchestrator from user confirmation | Critic Safety-gate target |

## Changelog
| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-12 | Initial GuardDuty prompt templates (Group 5 rollout). |
| 1.1.0 | 2026-06-27 | Migrated bare `{{cli_command}}` / `{{boto3_code}}` / `{{generator_output}}` to spec-compliant `{{output.*}}` namespaces (gcl-spec v1.11.0 §7.1). Added explicit Critic isolation guarantee; added `{{output.requested_region}}` and `{{output.safety_confirm_token}}` placeholders for rule A7 + Safety gate. Renamed section headers to match the canonical Generator/Critic/Orchestrator pattern used by the other 30 skills. |

---

> See [`prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
> for the canonical Generator / Critic / Orchestrator templates and the
> shared Variable Convention table.
