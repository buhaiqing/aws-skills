# GCL Prompt Templates — aws-ebs-ops

> Specialization of `aws-skill-generator/references/prompt-skeletons.md`

## Skill metadata

| Placeholder | Value |
|---|---|
| `{{skill.name}}` | aws-ebs-ops |
| `{{skill.service}}` | EBS (Elastic Block Store) |
| `{{skill.aws_cli_svc}}` | ec2 |
| `{{skill.max_iter}}` | 2 |

## Hard rules (Critic template injection)

```text
- rule A8: every volume and snapshot id MUST be echoed back from describe-volumes/describe-snapshots before deletion
- rule A7: --region MUST match {{output.requested_region}}
- rule A9: volume tags and descriptions MUST be masked for sensitive data
- rule A10: sts get-caller-identity MUST be the first command in trace
- delete-volume: MUST verify volume State == available (not attached) before deletion
- detach-volume: MUST verify volume State == in-use, warn about unmounting from OS first
- delete-snapshot: MUST verify no volumes reference this snapshot
- modify-volume resize: new_size MUST be > current size; reject shrink attempts
```

## Confirmation Strings

| Operation | Confirmation token |
|---|---|
| delete-volume | `confirm=DELETE_VOLUME {{user.volume_id}}` |
| detach-volume | `confirm=DETACH_VOLUME {{user.volume_id}}` |
| delete-snapshot | `confirm=DELETE_SNAPSHOT {{user.snapshot_id}}` |

## Variable Convention (deltas)

| Placeholder | Resolved from | Notes |
|---|---|---|
| `{{output.requested_region}}` | User input or env default | Validated region |
| `{{output.safety_confirm_token}}` | User input | Confirmation string for destructive ops |