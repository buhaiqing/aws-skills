# VPC Core Concepts

Virtual Private Cloud architecture, components, and AWS quotas.

## Architecture Overview
- **VPC**: Min /28 (14 IPs), Max /16 (65,534 IPs). RFC 1918 preferred: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16.
- **Subnet**: Must be within VPC CIDR, no overlap. AWS reserves 5 IPs per subnet.
- **Public subnet**: Route to IGW (0.0.0.0/0 → igw-id) + auto-assign public IP
- **Private subnet**: Route to NAT GW (0.0.0.0/0 → nat-gw-id) or no internet

## Route Tables
- **Main**: Created with VPC, contains local route, cannot be deleted
- **Custom**: Per routing need; longest prefix match; targets: local / igw / nat-gw / pcx / vpn-gw / vpce

## Security Groups vs Network ACLs
| Feature | Security Group | Network ACL |
|---------|----------------|-------------|
| Level | Instance (ENI) | Subnet |
| Stateful | Yes | No |
| Rules | Allow only | Allow + Deny |
| Order | All evaluated | Numbered |
| Default | Block inbound, allow outbound | Allow all |

## Internet Gateway
1 per VPC, managed HA, no bandwidth limit. Workflow: Create → Attach → Add route 0.0.0.0/0 → Enable public IP on subnet.

## NAT Gateway
In public subnet, requires EIP, single-AZ, charged per hour + GB. Default 5 per AZ (adjustable). HA: one per AZ.

## VPC Peering
Connect 2 VPCs privately. Not transitive. CIDRs cannot overlap. Max 125 per VPC. Lifecycle: `pending-acceptance` → `active` / `rejected` / `expired` → `deleted`.

## VPC Endpoints
| Type | Services | Cost | Method |
|------|----------|------|--------|
| Gateway | S3, DynamoDB | Free | Route table entry |
| Interface | Most AWS services | Hourly + data | ENI in subnet (PrivateLink) |

## Quotas (Adjustable)
| Resource | Default | Code |
|----------|---------|------|
| VPCs per region | 5 | L-F678F1CE |
| Subnets per VPC | 200 | n/a |
| IGWs per region | 5 | n/a |
| NAT GWs per AZ | 5 | L-3633C6E3 |
| Peering per VPC | 125 | n/a |
| SGs per VPC | 2,500 | n/a |
| Rules per SG | 60 in + 60 out | L-7F3D9F25 |
| Elastic IPs per region | 5 | n/a |

## CIDR Planning
| Environment | VPC CIDR | Subnet Size |
|-------------|----------|-------------|
| Production | /16 | /20-/24 per AZ |
| Development | /20 | /24-/27 |
| Testing | /24 | /27-/28 |

## Best Practices
- Plan CIDRs to avoid overlap with on-premises. Use /16 for prod. Spread ≥2 AZs.
- Least-privilege SGs; reference SGs not CIDRs; enable Flow Logs; use NACLs sparingly.
- NAT GW per AZ for HA. Gateway Endpoints for S3/DynamoDB.
- NAT Instance for dev (lower cost). Consolidate NAT Gateways. Right-size subnets.

## VPC Flow Logs

### Enable
```bash
aws ec2 create-flow-logs --resource-type VPC --resource-ids {{id}} --log-group-name /aws/vpc/flow-logs/{{name}} \
  --traffic-type ALL --log-destination-type cloud-watch-logs --max-aggregation-interval 60
```

### Record Format
```
version account-id interface-id srcaddr dstaddr srcport dstport protocol packets bytes start end action log-status
```
Key fields: `action` (ACCEPT/REJECT), `srcaddr`, `dstaddr`, `dstport`, `packets`/`bytes`.

### Analysis Queries
```bash
# REJECT traffic
aws logs start-query --log-group-name /aws/vpc/flow-logs/{{name}} --query-string \
  'fields @timestamp, srcaddr, dstaddr, dstport, action | filter action="REJECT" and dstaddr like /10\.0\./ | stats count() by dstaddr, dstport | sort count desc | limit 20'

# Connection timeout (ACCEPT with packets=0)
aws logs start-query --log-group-name /aws/vpc/flow-logs/{{name}} --query-string \
  'fields @timestamp, srcaddr, dstaddr, dstport, packets | filter action="ACCEPT" and packets=0 | stats count() by dstaddr | sort count desc'
```

### NAT Gateway Monitoring
| Metric | Namespace | Threshold | Use |
|--------|-----------|-----------|-----|
| `ActiveConnectionCount` | AWS/NATGateway | > 80% of 50,000 | Pool exhaustion |
| `PacketsDropCount` | AWS/NATGateway | > 0 | Packet loss → latency |
| `BytesOutToSource` | AWS/NATGateway | Baseline + 3σ | Traffic surge |
| `ErrorPortAllocation` | AWS/NATGateway | > 0 | Port exhaustion |

```bash
aws cloudwatch get-metric-statistics --namespace AWS/NATGateway --metric-name ActiveConnectionCount \
  --dimensions Name=NatGatewayId,Value={{nat_id}} --statistics Maximum --period 60
```

### VPC Reachability Analyzer
```bash
aws ec2 create-network-insights-path --source {{lb_eni}} --destination {{target_eni}} --protocol TCP --destination-port {{port}}
aws ec2 start-network-insights-analysis --network-insights-path-id {{path_id}}
```