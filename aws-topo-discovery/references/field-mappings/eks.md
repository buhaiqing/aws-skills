# EKS Cluster Field Mapping

**AWS API**: `eks describe-cluster` -> `aws_eks_cluster`

## Mapping Rules

| HCL Attribute | API JSON Path | Type | Required | Notes |
|---------------|---------------|------|----------|-------|
| `name` | `name` | string | Y | Block name derived from this |
| `role_arn` | `roleArn` | string | Y | IAM role ARN |
| `version` | `version` | string | N | Kubernetes version |
| `vpc_config.subnet_ids` | `resourcesVpcConfig.subnetIds` | list | Y | Subnet IDs |
| `vpc_config.security_group_ids` | `resourcesVpcConfig.securityGroupIds` | list | N | SG IDs |
| `vpc_config.endpoint_public_access` | `resourcesVpcConfig.endpointPublicAccess` | bool | N | Default true |

## Block Name

`{cluster_name_slug}` (e.g. `prod_eks_cluster`)

## Stable Import ID

`{cluster_name}` (e.g. `prod-eks-cluster`)

## Notes

- Node groups (`aws_eks_node_group`) deferred to Phase 2
- Requires `eks describe-cluster` per cluster (list-clusters only returns names)
