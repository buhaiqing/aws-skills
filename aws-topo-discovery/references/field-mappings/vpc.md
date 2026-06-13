# VPC Field Mapping

**AWS API**: `ec2 describe-vpcs` -> `aws_vpc`

## Mapping Rules

| HCL Attribute | API JSON Path | Type | Required | Notes |
|---------------|---------------|------|----------|-------|
| `cidr_block` | `CidrBlock` | string | Y | e.g. `10.0.0.0/16` |
| `tags` | `Tags` | map | N | Name tag used for block name |
| `enable_dns_support` | `EnableDnsSupport` | bool | N | Default true |
| `enable_dns_hostnames` | `EnableDnsHostnames` | bool | N | Default false |

## Block Name

`{name_tag_slug}` (e.g. `prod_vpc_us_east_1`)

## Stable Import ID

`{vpc_id}` (e.g. `vpc-0a1b2c3d4e5f6g7h8`)

## Example

Input JSON (describe-vpcs):
```json
{
  "VpcId": "vpc-0a1b2c3d",
  "CidrBlock": "10.0.0.0/16",
  "Tags": [{"Key": "Name", "Value": "prod-vpc"}]
}
```

Output HCL:
```hcl
resource "aws_vpc" "prod_vpc" {
  cidr_block = "10.0.0.0/16"
  tags = { Name = "prod-vpc" }
}
```
