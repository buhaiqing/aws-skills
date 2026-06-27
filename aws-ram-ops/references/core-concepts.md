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
| OU Principal | Share with `arn:aws:organizations::acct:ou/o-xxx/ou-yyy` | Batch authorize all app accounts under an OU |
| External Accounts | Share with specific account IDs via invitation | Cross-org / partner sharing |
| IAM Principal | Share with specific IAM roles/users | Fine-grained access |

## Multi-Account App Patterns

| Pattern | Owner Account | Consumer | RAM Operations |
|---------|---------------|----------|----------------|
| Shared VPC subnets | Network / shared-services | App-team accounts | `create-resource-share` + subnet ARNs |
| Standard security groups | Platform / security | App-team accounts | Share SG ARNs; consumer uses `aws-ec2-ops` |
| Aurora read-only for BI | Database / data platform | Analytics app account | Share cluster + `AmazonRDSDBClusterReadOnlyAccess` |
| Org-wide landing zone | Management account | All workloads OU | `enable-sharing-with-aws-organization` + OU principal |
| Partner dedicated subnet | Service provider | External partner account | `--allow-external-principals` + invitation accept |

**RAM vs IAM**: RAM grants **resource visibility** across accounts. Consumer accounts still need `aws-iam-ops` policies (e.g. `ec2:RunInstances`) to operate on shared resources.

## Supported Resource Types

Query the API to get the authoritative, up-to-date list:

```bash
aws ram list-resource-types --region {{user.region}} --output json | jq '.resourceTypes[].resourceType'
```

No hardcoded table — resource type availability varies by region and account.

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
