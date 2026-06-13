# Elastic IP Field Mapping

**AWS API**: `ec2 describe-addresses` -> `aws_eip`

## Mapping Rules

| HCL Attribute | API JSON Path | Type | Required | Notes |
|---------------|---------------|------|----------|-------|
| `domain` | `Domain` | string | Y | `"vpc"` for VPC EIPs |
| `tags` | `Tags` | map | N | Name tag used for block name |

## Block Name

`{name_tag_slug}` or `eip_{allocation_id_slug}` (e.g. `prod_eip_01`)

## Stable Import ID

`{allocation_id}` (e.g. `eipalloc-0a1b2c3d`)

## Notes

- Associated instance info (`InstanceId`) used for dependency inference
- `PublicIp` is informational, not set in HCL
