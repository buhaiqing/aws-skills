# GCL Prompt Templates — aws-apigateway-ops

> Specialization of `aws-skill-generator/references/prompt-skeletons.md`

## Skill metadata

| Placeholder | Value |
|---|---|
| `{{skill.name}}` | aws-apigateway-ops |
| `{{skill.service}}` | API Gateway (REST API) |
| `{{skill.aws_cli_svc}}` | apigateway |
| `{{skill.max_iter}}` | 2 |

## Hard rules (Critic template injection)

```text
- rule A8: every REST API id MUST be echoed back from get-rest-apis before deletion
- rule A7: --region MUST match {{output.requested_region}}
- rule A9: API keys and secrets (in keys, Lambda env vars) MUST be masked
- rule A10: sts get-caller-identity MUST be the first command in trace
- delete-rest-api with active deployment: MUST list stages first and warn about production traffic
- Lambda integration before creation: MUST verify Lambda function exists via describe-function
- Custom domain: MUST verify ACM certificate exists and Route53 record is configured
```

## Confirmation Strings

| Operation | Confirmation token |
|---|---|
| delete-rest-api | `confirm=DELETE_REST_API {{user.rest_api_id}}` |
| delete-stage | `confirm=DELETE_STAGE {{user.stage_name}}` |

## Variable Convention (deltas)

| Placeholder | Resolved from | Notes |
|---|---|---|
| `{{output.requested_region}}` | User input or env default | Validated region |
| `{{output.safety_confirm_token}}` | User input | Confirmation string for destructive ops |