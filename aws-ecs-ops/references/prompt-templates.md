# GCL Prompt Templates — aws-ecs-ops

> Specialization of `aws-skill-generator/references/prompt-skeletons.md`

## Skill metadata

| Placeholder | Value |
|---|---|
| `{{skill.name}}` | aws-ecs-ops |
| `{{skill.service}}` | ECS (Elastic Container Service) |
| `{{skill.aws_cli_svc}}` | ecs |
| `{{skill.max_iter}}` | 2 |

## Hard rules (Critic template injection)

```text
- rule A16: delete-service MUST scale desired-count to 0 before deletion, then wait for services-stable
- rule A16: delete-cluster MUST verify no services exist before deletion
- rule A8: every resource ARN (cluster, service, task definition, task) MUST be echoed back from a describe-* call before deletion
- rule A7: --region MUST match {{output.requested_region}}
- rule A9: container environment variables and secrets MUST be masked
- rule A10: sts get-caller-identity MUST be the first command in trace
- delete-cluster with running services: MUST refuse; scale all services to 0 first
- Fargate task with missing subnets: MUST verify network configuration parameters
```

## Confirmation Strings

| Operation | Confirmation token |
|---|---|
| delete-service | `confirm=DELETE {{user.service_name}}` |
| delete-cluster | `confirm=DELETE_CLUSTER {{user.cluster_name}}` |

## Variable Convention (deltas)

| Placeholder | Resolved from | Notes |
|---|---|---|
| `{{output.requested_region}}` | User input or env default | Validated region |
| `{{output.safety_confirm_token}}` | User input | Confirmation string for destructive ops |