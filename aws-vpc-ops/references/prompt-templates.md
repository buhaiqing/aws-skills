# GCL Prompt Templates — `aws-vpc-ops`

> Specialization of the shared skeleton:
> [`aws-skill-generator/references/prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
>
> This file contains only the **service-specific deltas** for `aws-vpc-ops`:
> Hard rules (substituted into the Critic template's `{skill.hard_rules}`),
> Confirmation strings, and Variable Convention deltas. The three canonical
> templates (Generator / Critic / Orchestrator) are referenced from the
> skeleton file; do not duplicate them here.

## Skill metadata (used by skeleton `{skill.*}` placeholders)

| Placeholder | Value |
|---|---|
| `{{skill.name}}` | `aws-vpc-ops` |
| `{{skill.service}}` | `vpc` |
| `{{skill.aws_cli_svc}}` | `ec2` |
| `{{skill.max_iter}}` | `2` (from `metadata.gcl.max_iter` in SKILL.md frontmatter) |

## Hard rules (Critic template injection)

> These bullets are substituted into the Critic template's
> `{skill.hard_rules}` slot in `prompt-skeletons.md` §2.
> They run BEFORE the canonical generic Hard rules (A7 / A8 / A9 / A10).

```text
- Correctness=0 if: `delete-vpc` called while any 8 pre-flight commands returned non-empty (rule A13)
- Correctness=0 if: `delete-security-group` called while `describe-network-interfaces` returned non-empty, or on default SG while instances exist in VPC
- Correctness=0 if: `delete-route-table` on **main** RT, `delete-internet-gateway` while attached, `delete-nat-gateway` while `State != "deleted"`, `delete-subnet` while any ENI exists
- Safety=0 if: `authorize-security-group-ingress` added `0.0.0.0/0` on a sensitive port without `confirm=AUTHORIZE_SG_PUBLIC`
- Safety=0 if: prod-tagged resource without matching `confirm=DELETE_PROD_*`
- Correctness=0 if: resource id not echoed from `describe-*` (rule A8)
- Correctness=0 if: `--region` mismatch (rule A7)
- Traceability=0 if: `sts get-caller-identity` not first (rule A10)
- Spec Compliance=0 if: malformed CIDR
- Missing fields → score 0 with justification
```

## Variable Convention (skill-specific deltas)
> Common placeholders (`{{user.*}}`, `{{env.*}}`, `{{output.*}}`)
> are defined once in `prompt-skeletons.md` §Variable convention.
> Only entries unique to this skill are listed below.

| Placeholder | Source | Notes |
|---|---|---|
| `{{user.request}}` | agent runtime | sanitized |
| `{{user.safety_confirm}}` | user confirmation | required for destructive ops |
| `{{user.region}}` | user input or `{{env.AWS_DEFAULT_REGION}}` | rule A7 |
| `{{env.AWS_ACCESS_KEY_ID}}` | runtime env | NEVER prompt user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | runtime env | NEVER log (rule A9) |
| `{{output.rubric}}` | `references/rubric.md` | injected as literal block |
| `{{output.generator_output}}` | previous Generator run | empty on iter 1 |
| `{{output.trace}}` | execution trace buffer | masked |
| `{{output.critic_scores}}` | previous Critic run | empty on iter 1 |
| `{{output.critic_blocking}}` | previous Critic run | empty on iter 1 |
| `{{output.iter}}` | Orchestrator counter | starts at 1 |
| `{{output.operation}}` | Orchestrator classification | one of listed types |

---

> See [`prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
> for the canonical Generator / Critic / Orchestrator templates and the
> shared Variable Convention table.
