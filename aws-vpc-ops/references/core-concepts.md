# VPC Core Concepts

Virtual Private Cloud architecture, components, and AWS quotas.

## VPC Architecture Overview

A Virtual Private Cloud (VPC) is a logically isolated virtual network in AWS where you can launch AWS resources in a defined network topology.

### Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         VPC (10.0.0.0/16)                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Internet Gateway                        │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │           Route Table (Main + Custom)                      │  │
│  │  Routes:                                                   │  │
│  │  - 10.0.0.0/16 → local                                    │  │
│  │  - 0.0.0.0/0 → IGW (public)                               │  │
│  │  - 0.0.0.0/0 → NAT GW (private)                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌─────────────────────┐    │    ┌──────────────────────────┐   │
│  │   Public Subnet     │    │    │    Private Subnet        │   │
│  │   (10.0.1.0/24)     │────┼────│    (10.0.2.0/24)         │   │
│  │                     │    │    │                          │   │
│  │  ┌───────────────┐  │    │    │  ┌────────────────────┐  │   │
│  │  │ NAT Gateway   │  │    │    │  │ Application Tier   │  │   │
│  │  │ (EIP bound)   │  │    │    │  │ EC2, RDS, etc.     │  │   │
│  │  └───────────────┘  │    │    │  └────────────────────┘  │   │
│  │                     │    │    │                          │   │
│  │  ┌───────────────┐  │    │    │  ┌────────────────────┐  │   │
│  │  │ Security      │  │    │    │  │ Security Group     │  │   │
│  │  │ Group         │  │    │    │  │                    │  │   │
│  │  └───────────────┘  │    │    │  └────────────────────┘  │   │
│  └─────────────────────┘    │    └──────────────────────────┘   │
│                              │                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                  Network ACL (Optional)                    │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## CIDR Blocks and IP Addressing

### RFC 1918 Private Address Ranges

| CIDR Block | IP Range | Total IPs | Use Case |
|------------|----------|-----------|----------|
| 10.0.0.0/8 | 10.0.0.0 - 10.255.255.255 | ~16.7M | Large enterprises |
| 172.16.0.0/12 | 172.16.0.0 - 172.31.255.255 | ~1M | Medium networks |
| 192.168.0.0/16 | 192.168.0.0 - 192.168.255.255 | ~65K | Small networks |

### AWS CIDR Constraints

- **VPC**: Minimum /28 (14 usable IPs), Maximum /16 (65,534 usable IPs)
- **Subnet**: Must be within VPC CIDR block
- **Subnet**: Minimum /28, Maximum = VPC CIDR size
- **Overlap**: Subnets cannot overlap within a VPC

### AWS Reserved IPs (5 per subnet)

| IP Address | Purpose |
|------------|---------|
| First IP (x.x.x.0) | Network address |
| Second IP (x.x.x.1) | VPC router |
| Third IP (x.x.x.2) | DNS server |
| Fourth IP (x.x.x.3) | Reserved for future use |
| Last IP (x.x.x.255) | Broadcast address |

**Example**: 10.0.1.0/28 has 16 IPs, but only 11 (10.0.1.4 - 10.0.1.14) are usable.

### Recommended CIDR Planning

| Environment | VPC CIDR | Subnet Size | Notes |
|-------------|----------|-------------|-------|
| Production | /16 | /20-/24 | Room for growth |
| Development | /20 | /24-/27 | Cost-efficient |
| Testing | /24 | /27-/28 | Minimal footprint |
| Multi-AZ Production | /16 | /20 per AZ | High availability |

## Subnets: Public vs Private

### Public Subnet

**Characteristics**:
- Route to Internet Gateway (0.0.0.0/0 → IGW)
- Auto-assign public IP enabled
- Instances can have public IPs
- Direct internet access inbound/outbound

**Use Cases**:
- Load balancers
- Bastion hosts
- NAT Gateway placement
- Public-facing web servers

### Private Subnet

**Characteristics**:
- No route to Internet Gateway
- Route to NAT Gateway (0.0.0.0/0 → NAT GW)
- Auto-assign public IP disabled
- Instances only have private IPs
- Internet access only via NAT Gateway (outbound)

**Use Cases**:
- Application servers
- Database servers
- Internal services
- Worker instances

### Subnet Best Practices

1. **AZ Distribution**: Spread subnets across multiple Availability Zones
2. **Tier Separation**: Separate public, private, and data tiers
3. **Sizing**: Plan for growth, but don't over-provision
4. **Naming**: Use descriptive names with AZ indicator (e.g., `prod-public-1a`)

## Route Tables

### Default/Main Route Table

- Created automatically with VPC
- Contains local route: `Vpc-Cidr → local`
- Cannot be deleted
- Used by subnets without explicit association

### Custom Route Tables

- Created manually for specific routing needs
- Must create routes manually
- Can be deleted after disassociating subnets

### Route Types

| Destination | Target | Use Case |
|-------------|--------|----------|
| VPC CIDR | local | Internal routing (automatic) |
| 0.0.0.0/0 | igw-id | Public subnet internet access |
| 0.0.0.0/0 | nat-gw-id | Private subnet internet access |
| Peer CIDR | pcx-id | VPC Peering |
| 10.0.0.0/16 | vpn-gw-id | VPN connection |
| Pl-xxx | vpce-id | VPC Endpoint |

### Route Priority

AWS routes traffic by longest prefix match:
1. Local route (VPC CIDR) - always highest priority
2. More specific routes (e.g., 10.0.1.0/24)
3. Less specific routes (e.g., 0.0.0.0/0)

## Security Groups vs Network ACLs

### Security Groups (Stateful)

| Property | Description |
|----------|-------------|
| Scope | Instance-level (attached to ENI) |
| Stateful | Return traffic automatically allowed |
| Rules | Allow rules only (no deny) |
| Evaluation | All rules evaluated before decision |
| Default | All inbound blocked; all outbound allowed |
| Limits | 5 SGs per ENI, 60 rules per SG (adjustable) |

**Best Practices**:
- Use descriptive names and descriptions
- Follow least-privilege principle
- Group by function (web, app, db)
- Reference other SGs for cross-tier access

### Network ACLs (Stateless)

| Property | Description |
|----------|-------------|
| Scope | Subnet-level |
| Stateless | Return traffic must be explicitly allowed |
| Rules | Allow and deny rules |
| Evaluation | Processed in order (lowest number first) |
| Default | Allow all inbound/outbound |
| Limits | 20 rules per ACL (adjustable) |

**Best Practices**:
- Use for subnet-level filtering
- Add deny rules for known bad traffic
- Remember to allow return traffic
- Keep rules simple and ordered

### Comparison Table

| Feature | Security Group | Network ACL |
|---------|----------------|-------------|
| Level | Instance | Subnet |
| Stateful | Yes | No |
| Allow Rules | Yes | Yes |
| Deny Rules | No | Yes |
| Order Matters | No | Yes |
| Default Action | Block inbound | Allow all |

## Internet Gateway (IGW)

### Purpose

- Connects VPC to internet
- Provides public IP addresses with internet access
- Required for public subnet internet connectivity

### Characteristics

- One IGW per VPC
- Horizontally scaled, redundant by AWS
- No bandwidth limits
- No additional charge (only data transfer fees)

### Workflow

1. Create IGW: `create-internet-gateway`
2. Attach to VPC: `attach-internet-gateway`
3. Add route to public route table: `0.0.0.0/0 → IGW`
4. Enable public IP on subnet: `modify-subnet-attribute`

## NAT Gateway

### Purpose

- Enables private subnet instances to access internet (outbound only)
- Cannot receive inbound traffic from internet
- Required for private subnet updates, downloads

### Characteristics

- Created in public subnet
- Requires Elastic IP allocation
- Managed by AWS (high availability in single AZ)
- Charged per hour + per GB data processed

### Types

| Type | Availability | Cost | Use Case |
|------|--------------|------|----------|
| Public | Single AZ | Higher | Development |
| Private (NAT Instance) | Single AZ | Lower | Cost-sensitive |

### NAT Gateway vs NAT Instance

| Feature | NAT Gateway | NAT Instance |
|---------|-------------|--------------|
| Managed | AWS | User |
| Bandwidth | Up to 45 Gbps | Instance size dependent |
| Availability | Single AZ | Single AZ |
| Port Forwarding | No | Yes |
| Bastion | No | Yes (can be combined) |

### Best Practices

1. Deploy NAT Gateway in public subnet
2. Create NAT Gateway in each AZ for HA (cross-AZ routing)
3. Monitor NAT Gateway metrics (bytes, packets, connections)
4. Consider NAT Instance for cost savings in dev environments

## VPC Peering

### Purpose

- Connect two VPCs privately
- Traffic stays within AWS network
- No internet exposure
- Works across accounts and regions

### Characteristics

- Transitive peering NOT supported (A→B→C, A cannot reach C)
- Overlapping CIDRs NOT allowed
- Each side must update route tables
- Security groups can reference peer VPC SGs

### Peering Lifecycle

| Status | Description | Action |
|--------|-------------|--------|
| `pending-acceptance` | Request created | Accepter must accept |
| `active` | Connection established | Add routes |
| `rejected` | Request rejected | No connection |
| `expired` | Request timed out | Retry |
| `deleted` | Connection deleted | Cleanup routes |

### Cross-Region Peering

- Requires explicit `--peer-region` parameter
- Both sides must create routes
- Inter-region data transfer charges apply

### Peering Limitations

1. **No transitivity**: A→B and B→C does not mean A→C
2. **No overlapping CIDRs**: Must have unique IP ranges
3. **Cannot peer with VPCs with matching CIDRs**
4. **Maximum 125 peering connections per VPC**

## VPC Endpoints

### Purpose

- Private connection to AWS services
- No internet gateway required
- Traffic stays within VPC

### Types

| Type | Services | Use Case |
|------|----------|----------|
| Gateway Endpoints | S3, DynamoDB | Free, route table entry |
| Interface Endpoints | Most AWS services | ENI in subnet, PrivateLink |

### Gateway Endpoints

- Free (no hourly/data charges)
- Added as route table entry
- S3 and DynamoDB only

### Interface Endpoints

- Uses PrivateLink (AWS-managed ENI)
- Hourly charge + data processing fee
- Supports most AWS services (EC2, SSM, Secrets Manager, etc.)

## AWS Quotas (Service Limits)

### VPC Quotas

| Resource | Default Limit | Adjustable |
|----------|---------------|------------|
| VPCs per region | 5 | Yes |
| Subnets per VPC | 200 | Yes |
| Route tables per VPC | 200 | Yes |
| Internet Gateways per region | 5 | Yes |
| NAT Gateways per AZ | 5 | Yes |
| VPN Gateways per region | 5 | Yes |
| VPC peering connections per VPC | 125 | Yes |
| Network ACLs per VPC | 200 | No |

### Security Group Quotas

| Resource | Default Limit | Adjustable |
|----------|---------------|------------|
| Security groups per VPC | 2,500 | Yes |
| Rules per security group | 60 inbound + 60 outbound | Yes (up to 1,000) |
| Security groups per ENI | 5 | Yes |

### Elastic IP Quotas

| Resource | Default Limit | Adjustable |
|----------|---------------|------------|
| Elastic IPs per region | 5 | Yes |
| EIPs for NAT Gateway | 5 | Yes |

### Request Limit Increase

Via AWS Service Quotas console or:
```
aws service-quotas request-service-quota-increase \
  --service-code ec2 \
  --quota-code L-F678F1CE \
  --desired-value 10
```

## VPC Best Practices

### Architecture Design

1. **Plan CIDR blocks carefully** - Avoid overlap with on-premises, other VPCs
2. **Use /16 for production** - Room for expansion
3. **Spread across AZs** - 2-3 Availability Zones minimum
4. **Separate tiers** - Public, private, data subnets

### Security

1. **Least privilege security groups** - Allow only necessary traffic
2. **Use Network ACLs sparingly** - For known bad traffic blocklist
3. **Enable VPC Flow Logs** - Monitor network traffic
4. **Reference SGs not CIDRs** - For cross-tier communication

### High Availability

1. **Multi-AZ architecture** - Subnets in each AZ
2. **NAT Gateway per AZ** - For cross-AZ HA
3. **Use Gateway Endpoints** - S3, DynamoDB without IGW

### Cost Optimization

1. **NAT Instance for dev** - Lower cost than NAT Gateway
2. **Consolidate NAT Gateways** - Single NAT for low-traffic VPCs
3. **Use Gateway Endpoints** - Free S3/DynamoDB access
4. **Right-size subnets** - Don't waste IP space

### Naming Conventions

| Resource | Pattern | Example |
|----------|---------|---------|
| VPC | `{env}-{project}-vpc` | `prod-api-vpc` |
| Subnet | `{env}-{tier}-{az}` | `prod-public-1a` |
| Security Group | `{env}-{tier}-{function}` | `prod-web-ssh` |
| Route Table | `{env}-{tier}-rt` | `prod-public-rt` |
| IGW | `{env}-{vpc}-igw` | `prod-api-igw` |
| NAT GW | `{env}-{vpc}-{az}-natgw` | `prod-api-1a-natgw` |