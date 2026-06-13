# Subnet Field Mapping

**AWS API**: `ec2 describe-subnets` -> `aws_subnet`

## Mapping Rules

| HCL Attribute | API JSON Path | Type | Required | Notes |
|---------------|---------------|------|----------|-------|
| `vpc_id` | `VpcId` | string | Y | Parent ref via VPC |
| `cidr_block` | `CidrBlock` | string | Y | e.g. `10.0.1.0/24` |
| `availability_zone` | `AvailabilityZone` | string | Y | e.g. `us-east-1a` |
| `map_public_ip_on_launch` | `MapPublicIpOnLaunch` | bool | N | Default false |
| `tags` | `Tags` | map | N | Name tag used for block name |

## Block Name

`{name_tag_slug}` (e.g. `prod_subnet_public_1a`)

## Stable Import ID

`{subnet_id}` (e.g. `subnet-0a1b2c3d`)
