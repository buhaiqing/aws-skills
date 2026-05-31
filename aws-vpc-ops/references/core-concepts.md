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

## AIOps: VPC Flow Logs for Network Diagnostics

### Enabling Flow Logs

```bash
# Create Flow Log to CloudWatch Logs
aws ec2 create-flow-logs \
  --resource-type VPC \
  --resource-ids {{vpc_id}} \
  --log-group-name /aws/vpc/flow-logs/{{vpc_name}} \
  --traffic-type ALL \
  --log-destination-type cloud-watch-logs \
  --max-aggregation-interval 60
```

### Flow Log Record Format

```
version account-id interface-id srcaddr dstaddr srcport dstport protocol packets bytes start end action log-status
```

Key fields for ELB AIOps:
| Field | AIOps Use |
|-------|-----------|
| `srcaddr` | Client IP (for NLB), LB private IP (for ALB) |
| `dstaddr` | Target IP |
| `dstport` | Target port (health check or traffic) |
| `action` | ACCEPT or REJECT — connectivity filter |
| `packets` / `bytes` | Traffic volume |
| `log-status` | OK / NODATA / SKIPDATA — data quality |

### Flow Log Analysis Queries

```bash
# Logs Insights: REJECT traffic from LB to targets
aws logs start-query \
  --log-group-name /aws/vpc/flow-logs/{{vpc_name}} \
  --start-time "$(date -d '-1 hour' +%s)" \
  --end-time "$(date +%s)" \
  --query-string 'fields @timestamp, srcaddr, dstaddr, dstport, action
    | filter action = "REJECT"
      and dstaddr like /10\.0\./
    | stats count() by dstaddr, dstport
    | sort count desc
    | limit 20'

# Logs Insights: Connection timeout detection (packet count = 0 for SYN)
aws logs start-query \
  --log-group-name /aws/vpc/flow-logs/{{vpc_name}} \
  --query-string 'fields @timestamp, srcaddr, dstaddr, dstport, packets, action
    | filter action = "ACCEPT" and packets = 0
    | stats count() by dstaddr
    | sort count desc'
```

### NAT Gateway Monitoring for ELB Performance

| Metric | Namespace | Threshold | AIOps Use |
|--------|-----------|-----------|-----------|
| `ActiveConnectionCount` | AWS/NATGateway | > 80% of limit (50,000 per GW) | Connection pool exhaustion |
| `PacketsDropCount` | AWS/NATGateway | > 0 | Packet loss → retransmission → latency |
| `BytesOutToSource` | AWS/NATGateway | Baseline + 3σ | Traffic surge detection |
| `ErrorPortAllocation` | AWS/NATGateway | > 0 | Port exhaustion → connections rejected |

```bash
# Check NAT Gateway health for ELB latency RCA
aws cloudwatch get-metric-statistics --namespace AWS/NATGateway \
  --metric-name ActiveConnectionCount \
  --dimensions Name=NatGatewayId,Value={{nat_id}} \
  --statistics Maximum --period 60 \
  --start-time "$(date -d '-30 minutes' -u +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

### VPC Reachability Analyzer

```bash
# Analyze path from LB to target (troubleshoot health check failures)
aws ec2 create-network-insights-path \
  --source "{{lb_network_interface_id}}" \
  --destination "{{target_network_interface_id}}" \
  --protocol TCP \
  --destination-port {{health_check_port}}

# Start analysis
aws ec2 start-network-insights-analysis \
  --network-insights-path-id "{{path_id}}"
```