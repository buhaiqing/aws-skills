# aws-finops-core GCL Prompt Templates

> Thin specialization of the canonical shared skeleton.
> See `aws-skill-generator/references/prompt-skeletons.md` for the full
> Generator / Critic / Orchestrator templates. Only finops-specific additions below.

## Skill Metadata

| Field | Value |
|---|---|
| `skill.name` | `aws-finops-core` |
| `skill.type` | composite |
| `skill.aws_cli_svc` | `ce` (Cost Explorer) + delegated base skills |
| `skill.max_iter` | 3 |
| `skill.gcl_tier` | recommended |

## Variable Convention Deltas

| Placeholder | Source | Default | Description |
|---|---|---|---|
| `{{user.cost_period}}` | user input | `LAST_30_DAYS` | Analysis window |
| `{{user.threshold_pct}}` | user input | `130` | Anomaly threshold % of 7-day baseline |
| `{{user.idle_days}}` | user input | `7` | Days of zero activity before marking idle |

## Hard Rules (service-specific)

- **HF1**: All `aws ce` commands must use `--output json` after the subcommand
- **HF2**: Time periods must be valid ISO 8601 dates (`YYYY-MM-DD` format)
- **HF3**: Anomaly ratio computed as `cost / baseline`, threshold at `{{user.threshold_pct}} / 100`
- **HF4**: Idle detection must cover all 5 resource types (ALB/NLB, EBS Volume, EBS Snapshot, Lambda, RDS)
- **HF5**: Report must include: top anomaly services, idle resources list, tag compliance %, RI/SP coverage %

## Confirmation Strings

N/A — aws-finops-core is read-only; no destructive operations.

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-07-19 | Initial prompt templates for aws-finops-core |
