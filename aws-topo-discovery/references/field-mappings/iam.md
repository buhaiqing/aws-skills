# IAM Role Field Mapping

**AWS API**: `iam list-roles` -> `aws_iam_role`

## Mapping Rules

| HCL Attribute | API JSON Path | Type | Required | Notes |
|---------------|---------------|------|----------|-------|
| `name` | `RoleName` | string | Y | Block name derived from this |
| `assume_role_policy` | `AssumeRolePolicyDocument` | string | Y | URL-decoded JSON policy |
| `path` | `Path` | string | N | Default `/` |
| `description` | `Description` | string | N | Role description |
| `tags` | `Tags` | map | N | Name tag |

## Block Name

`{role_name_slug}` (e.g. `eks_node_role`)

## Stable Import ID

`{role_name}` (e.g. `eks-node-role`)

## Deferred to Phase 2

- Attached policies (`aws_iam_role_policy_attachment`)
- Inline policies (`aws_iam_role_policy`)
- Instance profiles (`aws_iam_instance_profile`)

## Notes

- `AssumeRolePolicyDocument` is URL-encoded in API response — must decode
- Service-linked roles (`/aws-service-role/`) excluded by default
- `Arn` used for cross-reference with EKS/Lambda role fields
