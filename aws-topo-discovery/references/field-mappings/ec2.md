# EC2 Instance Field Mapping

**AWS API**: `ec2 describe-instances` -> `aws_instance`

## Mapping Rules

| HCL Attribute | API JSON Path | Type | Required | Notes |
|---------------|---------------|------|----------|-------|
| `ami` | `ImageId` | string | Y | AMI ID |
| `instance_type` | `InstanceType` | string | Y | e.g. `t3.medium` |
| `subnet_id` | `SubnetId` | string | Y | Parent ref via Subnet |
| `vpc_security_group_ids` | `SecurityGroups[].GroupId` | list | Y | Security group IDs |
| `key_name` | `KeyName` | string | N | SSH key pair |
| `tags` | `Tags` | map | N | Name tag used for block name |

## Block Name

`{name_tag_slug}` (e.g. `web_server_01`)

## Stable Import ID

`{instance_id}` (e.g. `i-0a1b2c3d4e5f6g7h8`)

## Deferred to Phase 2

- EBS volumes (`aws_ebs_volume` + attachment)
- Network interfaces
- IAM instance profile
- User data
