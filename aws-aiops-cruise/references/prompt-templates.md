# GCL Prompt Templates — `aws-aiops-cruise`

> Specialization of the shared skeleton:
> [`aws-skill-generator/references/prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
>
> This file contains only the **service-specific deltas** for `aws-aiops-cruise`:
> Hard rules (substituted into the Critic template's `{{skill.hard_rules}}`),
> and Variable Convention deltas. The three canonical templates (Generator /
> Critic / Orchestrator) are referenced from the skeleton file; do not
> duplicate them here.
>
> **Read-only skill** — no destructive operations, no Confirmation Strings table.

## Skill metadata (used by skeleton `{{skill.*}}` placeholders)

| Placeholder | Value |
|---|---|
| `{{skill.name}}` | `aws-aiops-cruise` |
| `{{skill.service}}` | `aws-aiops-cruise` (cross-product read-only patrol) |
| `{{skill.aws_cli_svc}}` | `ec2`, `elbv2`, `rds`, `cloudwatch`, `resourcegroupstaggingapi`, `cloudtrail` (multi-service) |
| `{{skill.max_iter}}` | `3` (from `metadata.gcl.max_iter` in SKILL.md frontmatter) |

## Hard rules (Critic template injection)

> These bullets are substituted into the Critic template's
> `{{skill.hard_rules}}` slot in `prompt-skeletons.md` §2.
> They run BEFORE the canonical generic Hard rules (A7 / A8 / A9 / A10).

```text
- Safety = 0 if any `create|delete|terminate|stop|start|authorize|revoke|modify|put|update`
  API call appears in the trace (read-only skill; rule A3/A9).
- Safety = 0 if scope is empty/omitted unless `scope=full` explicitly confirmed
  via `{{output.safety_confirm_token}}`.
- Correctness = 0 if incidents in trace do not match the schema in
  `references/incident-schema.md` (missing `level`, `rule_id`, `dedup_key`).
- Correctness = 0 if `aws sts get-caller-identity` is not the first command
  in the trace (rule A10).
```

## Variable Convention (skill-specific deltas)

> Common placeholders (`{{user.*}}`, `{{env.*}}`, `{{output.*}}`)
> are defined once in `prompt-skeletons.md` §Variable convention.
> Only entries unique to this skill are listed below.

| Placeholder | Resolved from | Notes |
|---|---|---|
| `{{user.scope_name}}` | User input | Workload label (customer / app name) |
| `{{user.tag_key}}` | User input | Resource tag key for scope filtering |
| `{{user.tag_value}}` | User input | Resource tag value for scope filtering |
| `{{user.resource_group}}` | User input | AWS Resource Group name (preferred scope) |
| `{{user.scenario}}` | User input | `daily_check` / `emergency` / `capacity` / `pre_launch` / `slow_query` / `connection_storm` / `bottleneck` / `redis_perf` / `asg_opt` |
| `{{user.enable_ssm}}` | User input | Y/N — SSM Run Command deep checks |
| `{{user.enable_pi}}` | User input | Y/N — RDS Performance Insights (default Y) |
| `{{user.enable_guru}}` | User input | Y/N — DevOps Guru insights (default Y) |
| `{{user.assume_role_arn}}` | User input | Cross-account STS role ARN |
| `{{user.regions}}` | User input | Comma-separated regions |
| `{{user.enable_xray}}` | User input | Y/N — X-Ray service graph (502/latency) |
| `{{output.topology}}` | TopoScan / topo-discovery | JSON manifest |
| `{{output.metrics}}` | CloudWatch aggregation | JSON |
| `{{output.chain_inference}}` | Phase 3 inference | Markdown |

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-07-04 | Migrated to shared skeleton architecture (GCL v1.12.0). Self-contained templates replaced by thin specialization referencing `prompt-skeletons.md`. |

---

> See [`prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
> for the canonical Generator / Critic / Orchestrator templates and the
> shared Variable Convention table.