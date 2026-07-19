# GCL Prompt Templates — `aws-security-copilot`

> Specialization of the shared skeleton:
> [`aws-skill-generator/references/prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
>
> This file contains only the **service-specific deltas** for `aws-security-copilot`.
> Hard rules (Critic template injection), Confirmation strings, and Variable
> Convention deltas. The three canonical templates (Generator / Critic /
> Orchestrator) are referenced from the skeleton file.

## Skill metadata

| Placeholder | Value |
|---|---|
| `{{skill.name}}` | `aws-security-copilot` |
| `{{skill.service}}` | `security-copilot` |
| `{{skill.max_iter}}` | `3` |

## Hard rules (Critic template injection)

> Substituted into the Critic template's `{skill.hard_rules}` slot.

```text
- Safety = 0 if any CRITICAL finding lacks a HALT annotation + notify_user() call.
- Safety = 0 if any CRITICAL finding is auto-remediated before explicit user confirm.
- Safety = 0 if CRITICAL finding lacks `confirm=HALT <finding-id>` pattern.
- Correctness = 0 if any of the 7 required delegate dirs is missing from disk:
  aws-guardduty-ops, aws-securityhub-ops, aws-config-ops, aws-iam-ops,
  aws-secretsmanager-ops, aws-kms-ops, aws-cloudtrail-ops.
- Correctness = 0 if a finding is routed to the wrong delegate skill per
  playbook-routes.md.
```

## Supported Operations

- security-posture-summary
- finding-investigation
- incident-response
- compliance-check

## Confirmation Strings

| Severity | Pattern | Example |
|----------|---------|---------|
| CRITICAL | `confirm=HALT <finding-id>` | `confirm=HALT F01-CRED-EXPOSED` |
| HIGH | `confirm=<action> <resource-id>` | `confirm=restrict-sg sg-0123456789abcdef0` |
| MEDIUM | Pre-approved playbook | No explicit confirm |
| LOW | Log only | No action |

## Variable Convention (skill-specific deltas)

| Placeholder | Notes |
|---|---|
| `{{user.region}}` | Default region |
| `{{user.security_posture_request}}` | User request for posture summary |
| `{{output.finding_ids}}` | Combined finding IDs from all sources |
| `{{output.security_posture}}` | Merged posture JSON |
| `{{output.requested_region}}` | Critic region-check target (rule A7) |
| `{{output.safety_confirm_token}}` | Critic Safety-gate target |
| `{{output.critical_findings[]}}` | CRITICAL findings list (must have HALT marker) |
| `{{output.delegate_routing}}` | Mapping of finding → delegate skill per playbook-routes.md |

> Common placeholders (`{{user.*}}`, `{{env.*}}`, `{{output.*}}`) are defined
> once in `prompt-skeletons.md` §Variable convention.

---

> See [`prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
> for the canonical Generator / Critic / Orchestrator templates.
