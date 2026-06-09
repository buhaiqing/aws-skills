# Core Concepts — AWS Resource Access Manager (RAM)

## What is RAM

- **Purpose**: Securely share AWS resources across accounts or within an organization
- **Category**: Management & Governance
- **Console**: https://console.aws.amazon.com/ram/
- **Docs**: https://docs.aws.amazon.com/ram/

## Primary Resources

| Resource | Description |
|----------|-------------|
| Resource Share | Container for resources and principals; defines who can access what |
| Permission | IAM policy template attached to a resource share |
| Principal | AWS account, OU, or IAM entity that receives access |
| Association | Links principals/resources to a resource share |
| Invitation | Cross-account sharing request (must be accepted) |

## Architecture

```
Account A (Owner)
  └── Resource Share
        ├── Resources (Subnets, SGs, Clusters, ...)
        ├── Principals (Account IDs, OUs)
        └── Permissions (IAM policy templates)
              ↓ (cross-account)
Account B (Consumer)
  └── Accepts Invitation → Gets access to shared resources
```

## Sharing Models

| Model | Description | When to Use |
|-------|-------------|-------------|
| AWS Organization | Share with all/org accounts via org sharing | Internal org sharing |
| External Accounts | Share with specific account IDs via invitation | Cross-org / partner sharing |
| IAM Principal | Share with specific IAM roles/users | Fine-grained access |

## Supported Resource Types

| Category | Resource Types |
|----------|---------------|
| Compute | EC2 Subnets, Security Groups, Capacity Reservations, DX Gateway Associations |
| Networking | VPC Prefix Delegations |
| Database | RDS Clusters (Aurora), Neptune Clusters, DocumentDB Clusters |
| Storage | EFS File Systems |
| Other | License Manager Configurations |

## Quotas

| Quota | Default | Adjustable? |
|-------|---------|-------------|
| Resource shares per account | 1000 | No |
| Resources per share | 50 | No |
| Principals per share | 100 | No |
| Permissions per share | 10 | No |
| Pending invitations per account | 100 | No |

## Lifecycle States

| Resource State | Meaning |
|---------------|---------|
| PENDING | Share creation in progress |
| ACTIVE | Share is active and functional |
| DELETING | Share deletion in progress |
| DELETED | Share has been deleted |

## Safety Considerations

- **Delete Resource Share**: All associated principals lose access to shared resources
- **Delete Permission**: All resource shares using that permission are affected
- **Reject Invitation**: Declines access to shared resources
- **Cross-account**: Consumer account must accept invitation before resources are accessible
