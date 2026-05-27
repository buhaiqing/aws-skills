# VPC Core Concepts

Virtual Private Cloud architecture, components, and AWS quotas.

## Architecture Overview
**VPC** — logically isolated virtual network in AWS.
- **VPC CIDR**: Min /28 (14 IPs), Max /16 (65,534 IPs). RFC 1918 preferred: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16.
- **Subnet**: Must be within VPC CIDR, cannot overlap. AWS reserves 5 IPs per subnet.
- **Public subnet**: Route to IGW (0.0.0.0/0 → igw-id) + auto-assign public IP
- **Private subnet**: Route to NAT Gateway (0.0.0.0/0 → nat-gw-id) or no internet

## Route Tables
- **Main**: Created with VPC, contains local route, cannot be deleted
- **Custom**: Created per-routing need, routes by longest prefix match
- **Route targets**: local / igw / nat-gw / pcx (peering) / vpn-gw / vpce

## Security Groups vs Network ACLs
| Feature | Security Group | Network ACL |
|---------|----------------|-------------|
| Level | Instance (ENI) | Subnet |
| Stateful | Yes | No (return traffic must be allowed) |
| Rules | Allow only | Allow + Deny |
| Order | All evaluated | Numbered order |
| Default | Block inbound, allow outbound | Allow all |

## Internet Gateway (IGW)
- 1 per VPC, managed/AWS HA, no bandwidth limit, no charge (only data transfer).
- **Workflow**: Create → Attach to VPC → Add route 0.0.0.0/0 → Enable public IP on subnet.

## NAT Gateway
- In public subnet, requires Elastic IP, single-AZ, charged per hour + GB.
- **Limits**: 5 per AZ (adjustable). For HA: one per AZ.
- Alternative: NAT Instance (user-managed, lower cost, supports port forwarding).

## VPC Peering
- Connect 2 VPCs privately. Not transitive (A→B→C ≠ A→C).
- CIDRs cannot overlap. Max 125 peering connections per VPC.
- Cross-region: requires `--peer-region`.
- Lifecycle: `pending-acceptance` → `active` / `rejected` / `expired` → `deleted`.

## VPC Endpoints
| Type | Services | Cost | Method |
|------|----------|------|--------|
| Gateway | S3, DynamoDB | Free | Route table entry |
| Interface | Most AWS services | Hourly + data | ENI in subnet (PrivateLink) |

## Quotas (Adjustable via AWS Service Quotas)
| Resource | Default Limit | Quota Code |
|----------|--------------|------------|
| VPCs per region | 5 | L-F678F1CE |
| Subnets per VPC | 200 | L-... |
| IGWs per region | 5 | L-... |
| NAT Gateways per AZ | 5 | L-3633C6E3 |
| Peering per VPC | 125 | L-... |
| SGs per VPC | 2,500 | L-... |
| Rules per SG | 60 in + 60 out | L-7F3D9F25 |
| Elastic IPs per region | 5 | L-... |

## CIDR Planning
| Environment | VPC CIDR | Subnet Size |
|-------------|----------|-------------|
| Production | /16 | /20-/24 per AZ |
| Development | /20 | /24-/27 |
| Testing | /24 | /27-/28 |

## Best Practices
- **Architecture**: Plan CIDRs to avoid overlap with on-premises. Use /16 for prod. Spread across ≥2 AZs. Separate public/private/data tiers.
- **Security**: Least-privilege SGs, reference SGs not CIDRs, enable Flow Logs, use NACLs sparingly.
- **HA**: NAT Gateway per AZ. Gateway Endpoints for S3/DynamoDB.
- **Cost**: NAT Instance for dev, consolidate NAT Gateways, right-size subnets.