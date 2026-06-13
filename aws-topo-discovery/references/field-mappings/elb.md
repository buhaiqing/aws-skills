# ELB (ALB/NLB/CLB) Field Mapping

**AWS API**: `elbv2 describe-load-balancers` -> `aws_lb`

## Mapping Rules

| HCL Attribute | API JSON Path | Type | Required | Notes |
|---------------|---------------|------|----------|-------|
| `name` | `LoadBalancerName` | string | Y | Block name derived from this |
| `internal` | `Scheme` | bool | Y | `"internal"` -> true, else false |
| `load_balancer_type` | `Type` | string | Y | `application`, `network`, `gateway` |
| `subnets` | `AvailabilityZones[].SubnetId` | list | Y | Subnet IDs |
| `security_groups` | `SecurityGroups` | list | N | ALB only |
| `tags` | (from `describe-tags`) | map | N | Name tag |

## Block Name

`{load_balancer_name_slug}` (e.g. `prod_alb_01`)

## Stable Import ID

`{load_balancer_arn}` (full ARN)
