# Security Group Field Mapping

**AWS API**: `ec2 describe-security-groups` -> `aws_security_group`

## Mapping Rules

| HCL Attribute | API JSON Path | Type | Required | Notes |
|---------------|---------------|------|----------|-------|
| `name` | `GroupName` | string | Y | Block name derived from this |
| `description` | `Description` | string | Y | SG description |
| `vpc_id` | `VpcId` | string | Y | Parent ref via VPC |
| `tags` | `Tags` | map | N | Name tag |

## Block Name

`{group_name_slug}` (e.g. `web_sg`)

## Stable Import ID

`{group_id}` (e.g. `sg-0a1b2c3d`)

## Deferred to Phase 2

- Ingress/Egress rules (`aws_security_group_rule` or inline)
- Prefix lists
- Referenced group IDs
