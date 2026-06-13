# NAT Gateway Field Mapping

**AWS API**: `ec2 describe-nat-gateways` -> `aws_nat_gateway`

## Mapping Rules

| HCL Attribute | API JSON Path | Type | Required | Notes |
|---------------|---------------|------|----------|-------|
| `subnet_id` | `SubnetId` | string | Y | Parent ref via Subnet |
| `allocation_id` | `NatGatewayAddresses[].AllocationId` | string | Y | EIP allocation |
| `tags` | `Tags` | map | N | Name tag used for block name |

## Block Name

`{name_tag_slug}` (e.g. `prod_nat_1a`)

## Stable Import ID

`{nat_gateway_id}` (e.g. `nat-0a1b2c3d`)
