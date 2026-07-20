# GCL Prompt Templates — aws-application-autoscaling-ops

> Specialization of the shared skeleton:
> [`references/prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
>
> This file contains only service-specific deltas.

## Skill metadata

| Placeholder | Value |
|---|---|
| `{{skill.name}}` | aws-application-autoscaling-ops |
| `{{skill.service}}` | Application Auto Scaling (cross-service scaler namespace) |
| `{{skill.aws_cli_svc}}` | application-autoscaling |
| `{{skill.max_iter}}` | 2 |
| `{{skill.type}}` | base |
| `{{skill.provides}}` | app-autoscaling-register-target, app-autoscaling-deregister-target, app-autoscaling-put-policy, app-autoscaling-delete-policy, app-autoscaling-tag-resource, app-autoscaling-describe |

## Hard rules (Critic template injection)

```text
- rule A10: sts get-caller-identity MUST be the first command in trace
- rule A7: --region MUST match {{output.requested_region}}
- rule A8: resource_id MUST be echoed back from describe-scalable-targets before deregister
- rule A8: policy_name MUST be echoed back from describe-scaling-policies before delete
- rule A9: tag values MUST be masked; never log raw Project/Environment strings
- rule A11: deregister-scalable-target MUST verify zero active scaling policies first
- rule A11: put-scaling-policy with TargetTracking MUST validate ECSServiceAverage* metric namespace
- rule A12: Cooldown bounds ≤ 3600s; reject otherwise
- delete-scaling-policy on production ECS service: MUST verify desiredCount >= 1 after the call
```

## Confirmation Strings

| Operation | Confirmation token |
|---|---|
| `deregister-scalable-target` | `confirm=DEREGISTER_SCALABLE_TARGET {{user.resource_id}}` |
| `delete-scaling-policy` | `confirm=DELETE_SCALING_POLICY {{user.policy_name}}` |

## Variable Convention (skill-specific deltas)

| Placeholder | Resolved from | Notes |
|---|---|---|
| `{{user.service_namespace}}` | User input / default `ecs` | ECS MVP; other namespaces deferred |
| `{{user.resource_id}}` | User input | Format: `service/<cluster>/<service>` for ECS |
| `{{user.scalable_dimension}}` | User input | Default `ecs:service:DesiredCount` |
| `{{user.policy_name}}` | User input | Unique within (namespace, resource_id, dimension) |
| `{{output.resource_arn}}` | Constructed locally | Application Auto Scaling doesn't expose ARN via describe; format: `arn:aws:application-autoscaling:<region>:<acct>:scalable-target/<hash>` |

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-07-21 | Initial GCL prompt templates (shared skeleton specialization, ECS-only MVP) |
