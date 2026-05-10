# AWS CLI Usage for VPC Operations

Complete CLI command reference for AWS VPC operations with JSON output paths.

## Prerequisites

```bash
# Verify CLI version (>= 2.0 required)
aws --version

# Configure credentials (or use environment variables)
aws configure list

# Test connectivity
aws ec2 describe-regions --output json
```

## VPC Operations

### Create VPC

```bash
# Basic VPC creation
aws ec2 create-vpc \
  --cidr-block "{{user.vpc_cidr}}" \
  --output json

# JSON path: Vpc.VpcId, Vpc.CidrBlock, Vpc.State

# Create VPC with tags
aws ec2 create-vpc \
  --cidr-block "{{user.vpc_cidr}}" \
  --tag-specifications "ResourceType=vpc,Tags=[{Key=Name,Value={{user.vpc_name}}]" \
  --output json

# Create VPC with IPv6
aws ec2 create-vpc \
  --cidr-block "{{user.vpc_cidr}}" \
  --amazon-provided-ipv6-cidr-block \
  --output json

# JSON path: Vpc.Ipv6CidrBlockAssociationSet[0].Ipv6CidrBlock
```

### Describe VPCs

```bash
# List all VPCs
aws ec2 describe-vpcs --output json

# JSON path: Vpcs[].VpcId, Vpcs[].CidrBlock, Vpcs[].State, Vpcs[].Tags

# Describe specific VPC
aws ec2 describe-vpcs \
  --vpc-ids "{{user.vpc_id}}" \
  --output json

# Filter by CIDR
aws ec2 describe-vpcs \
  --filters "Name=cidr-block,Values={{user.vpc_cidr}}" \
  --output json

# Filter by tag
aws ec2 describe-vpcs \
  --filters "Name=tag:Name,Values={{user.vpc_name}}" \
  --output json
```

### Modify VPC Attributes

```bash
# Enable DNS support
aws ec2 modify-vpc-attribute \
  --vpc-id "{{user.vpc_id}}" \
  --enable-dns-support "{\"Value\":true}"

# Enable DNS hostnames
aws ec2 modify-vpc-attribute \
  --vpc-id "{{user.vpc_id}}" \
  --enable-dns-hostnames "{\"Value\":true}"
```

### Delete VPC

```bash
# Delete VPC (requires all dependencies removed first)
aws ec2 delete-vpc \
  --vpc-id "{{user.vpc_id}}" \
  --output json

# Returns: {} on success
```

## Subnet Operations

### Create Subnet

```bash
# Basic subnet creation
aws ec2 create-subnet \
  --vpc-id "{{user.vpc_id}}" \
  --cidr-block "{{user.subnet_cidr}}" \
  --output json

# JSON path: Subnet.SubnetId, Subnet.CidrBlock, Subnet.VpcId, Subnet.State

# Create subnet with Availability Zone
aws ec2 create-subnet \
  --vpc-id "{{user.vpc_id}}" \
  --cidr-block "{{user.subnet_cidr}}" \
  --availability-zone "{{user.az}}" \
  --output json

# Create subnet with tags
aws ec2 create-subnet \
  --vpc-id "{{user.vpc_id}}" \
  --cidr-block "{{user.subnet_cidr}}" \
  --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value={{user.subnet_name}}]" \
  --output json
```

### Describe Subnets

```bash
# List all subnets
aws ec2 describe-subnets --output json

# JSON path: Subnets[].SubnetId, Subnets[].CidrBlock, Subnets[].VpcId, Subnets[].AvailabilityZone

# Describe subnets in VPC
aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values={{user.vpc_id}}" \
  --output json

# Describe specific subnet
aws ec2 describe-subnets \
  --subnet-ids "{{user.subnet_id}}" \
  --output json
```

### Modify Subnet Attributes

```bash
# Make subnet public (auto-assign public IP)
aws ec2 modify-subnet-attribute \
  --subnet-id "{{user.subnet_id}}" \
  --map-public-ip-on-launch

# Make subnet private
aws ec2 modify-subnet-attribute \
  --subnet-id "{{user.subnet_id}}" \
  --no-map-public-ip-on-launch
```

### Delete Subnet

```bash
# Delete subnet
aws ec2 delete-subnet \
  --subnet-id "{{user.subnet_id}}" \
  --output json

# Returns: {} on success
```

## Security Group Operations

### Create Security Group

```bash
# Create security group
aws ec2 create-security-group \
  --group-name "{{user.sg_name}}" \
  --description "{{user.sg_description}}" \
  --vpc-id "{{user.vpc_id}}" \
  --output json

# JSON path: GroupId

# Create with tags
aws ec2 create-security-group \
  --group-name "{{user.sg_name}}" \
  --description "{{user.sg_description}}" \
  --vpc-id "{{user.vpc_id}}" \
  --tag-specifications "ResourceType=security-group,Tags=[{Key=Name,Value={{user.sg_name}}]" \
  --output json
```

### Describe Security Groups

```bash
# List all security groups
aws ec2 describe-security-groups --output json

# JSON path: SecurityGroups[].GroupId, SecurityGroups[].GroupName, SecurityGroups[].IpPermissions

# Describe specific security group
aws ec2 describe-security-groups \
  --group-ids "{{user.sg_id}}" \
  --output json

# Filter by VPC
aws ec2 describe-security-groups \
  --filters "Name=vpc-id,Values={{user.vpc_id}}" \
  --output json
```

### Authorize Ingress Rules

```bash
# Allow SSH (port 22) from specific IP
aws ec2 authorize-security-group-ingress \
  --group-id "{{user.sg_id}}" \
  --protocol tcp \
  --port 22 \
  --cidr "{{user.allowed_cidr}}" \
  --output json

# Returns: {"Return": true}

# Allow HTTP from anywhere
aws ec2 authorize-security-group-ingress \
  --group-id "{{user.sg_id}}" \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0 \
  --output json

# Allow HTTPS
aws ec2 authorize-security-group-ingress \
  --group-id "{{user.sg_id}}" \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0 \
  --output json

# Allow from another security group
aws ec2 authorize-security-group-ingress \
  --group-id "{{user.sg_id}}" \
  --protocol tcp \
  --port 0-65535 \
  --source-group "{{user.source_sg_id}}" \
  --output json

# Multiple rules with IP permissions JSON
aws ec2 authorize-security-group-ingress \
  --group-id "{{user.sg_id}}" \
  --ip-permissions '[{"IpProtocol":"tcp","FromPort":443,"ToPort":443,"IpRanges":[{"CidrIp":"0.0.0.0/0"}]}]' \
  --output json
```

### Authorize Egress Rules

```bash
# Allow outbound traffic
aws ec2 authorize-security-group-egress \
  --group-id "{{user.sg_id}}" \
  --ip-permissions '[{"IpProtocol":"-1","IpRanges":[{"CidrIp":"0.0.0.0/0"}]}]' \
  --output json
```

### Revoke Rules

```bash
# Revoke ingress rule
aws ec2 revoke-security-group-ingress \
  --group-id "{{user.sg_id}}" \
  --protocol tcp \
  --port 22 \
  --cidr "{{user.allowed_cidr}}" \
  --output json

# Revoke egress rule
aws ec2 revoke-security-group-egress \
  --group-id "{{user.sg_id}}" \
  --ip-permissions '[{"IpProtocol":"-1","IpRanges":[{"CidrIp":"0.0.0.0/0"}]}]' \
  --output json
```

### Delete Security Group

```bash
# Delete security group
aws ec2 delete-security-group \
  --group-id "{{user.sg_id}}" \
  --output json

# Returns: {"Return": true}
```

## Route Table Operations

### Create Route Table

```bash
# Create route table
aws ec2 create-route-table \
  --vpc-id "{{user.vpc_id}}" \
  --output json

# JSON path: RouteTable.RouteTableId

# Create with tags
aws ec2 create-route-table \
  --vpc-id "{{user.vpc_id}}" \
  --tag-specifications "ResourceType=route-table,Tags=[{Key=Name,Value={{user.rt_name}}]" \
  --output json
```

### Describe Route Tables

```bash
# List all route tables
aws ec2 describe-route-tables --output json

# JSON path: RouteTables[].RouteTableId, RouteTables[].Routes[], RouteTables[].Associations[]

# Describe specific route table
aws ec2 describe-route-tables \
  --route-table-ids "{{user.rt_id}}" \
  --output json

# Filter by VPC
aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values={{user.vpc_id}}" \
  --output json
```

### Create Route

```bash
# Add route to Internet Gateway (public subnet)
aws ec2 create-route \
  --route-table-id "{{user.rt_id}}" \
  --destination-cidr-block 0.0.0.0/0 \
  --gateway-id "{{user.igw_id}}" \
  --output json

# Returns: {"Return": true}

# Add route to NAT Gateway (private subnet)
aws ec2 create-route \
  --route-table-id "{{user.rt_id}}" \
  --destination-cidr-block 0.0.0.0/0 \
  --nat-gateway-id "{{user.natgw_id}}" \
  --output json

# Add route for VPC Peering
aws ec2 create-route \
  --route-table-id "{{user.rt_id}}" \
  --destination-cidr-block "{{user.peer_cidr}}" \
  --vpc-peering-connection-id "{{user.peer_conn_id}}" \
  --output json
```

### Delete Route

```bash
# Delete route
aws ec2 delete-route \
  --route-table-id "{{user.rt_id}}" \
  --destination-cidr-block 0.0.0.0/0 \
  --output json

# Returns: {"Return": true}
```

### Associate Subnet with Route Table

```bash
# Associate subnet with route table
aws ec2 associate-route-table \
  --route-table-id "{{user.rt_id}}" \
  --subnet-id "{{user.subnet_id}}" \
  --output json

# JSON path: AssociationId
```

### Disassociate Subnet

```bash
# Disassociate subnet from route table
aws ec2 disassociate-route-table \
  --association-id "{{user.assoc_id}}" \
  --output json

# Returns: {"Return": true}
```

### Delete Route Table

```bash
# Delete route table (must disassociate first)
aws ec2 delete-route-table \
  --route-table-id "{{user.rt_id}}" \
  --output json

# Returns: {"Return": true}
```

## Internet Gateway Operations

### Create Internet Gateway

```bash
# Create Internet Gateway
aws ec2 create-internet-gateway \
  --output json

# JSON path: InternetGateway.InternetGatewayId

# Create with tags
aws ec2 create-internet-gateway \
  --tag-specifications "ResourceType=internet-gateway,Tags=[{Key=Name,Value={{user.igw_name}}]" \
  --output json
```

### Attach Internet Gateway to VPC

```bash
# Attach Internet Gateway to VPC
aws ec2 attach-internet-gateway \
  --internet-gateway-id "{{user.igw_id}}" \
  --vpc-id "{{user.vpc_id}}" \
  --output json

# Returns: {} on success
```

### Describe Internet Gateways

```bash
# List all Internet Gateways
aws ec2 describe-internet-gateways --output json

# JSON path: InternetGateways[].InternetGatewayId, InternetGateways[].Attachments[].VpcId

# Describe specific IGW
aws ec2 describe-internet-gateways \
  --internet-gateway-ids "{{user.igw_id}}" \
  --output json
```

### Detach Internet Gateway

```bash
# Detach Internet Gateway from VPC
aws ec2 detach-internet-gateway \
  --internet-gateway-id "{{user.igw_id}}" \
  --vpc-id "{{user.vpc_id}}" \
  --output json

# Returns: {} on success
```

### Delete Internet Gateway

```bash
# Delete Internet Gateway (must detach first)
aws ec2 delete-internet-gateway \
  --internet-gateway-id "{{user.igw_id}}" \
  --output json

# Returns: {"Return": true}
```

## NAT Gateway Operations

### Allocate Elastic IP for NAT Gateway

```bash
# Allocate Elastic IP
aws ec2 allocate-address \
  --domain vpc \
  --output json

# JSON path: AllocationId, PublicIp
```

### Create NAT Gateway

```bash
# Create NAT Gateway (requires subnet and Elastic IP)
aws ec2 create-nat-gateway \
  --subnet-id "{{user.subnet_id}}" \
  --allocation-id "{{user.eip_allocation_id}}" \
  --output json

# JSON path: NatGateway.NatGatewayId, NatGateway.State (pending → available)

# Create with tags
aws ec2 create-nat-gateway \
  --subnet-id "{{user.subnet_id}}" \
  --allocation-id "{{user.eip_allocation_id}}" \
  --tag-specifications "ResourceType=natgateway,Tags=[{Key=Name,Value={{user.natgw_name}}]" \
  --output json
```

### Describe NAT Gateways

```bash
# List all NAT Gateways
aws ec2 describe-nat-gateways --output json

# JSON path: NatGateways[].NatGatewayId, NatGateways[].State, NatGateways[].SubnetId

# Describe specific NAT Gateway
aws ec2 describe-nat-gateways \
  --nat-gateway-ids "{{user.natgw_id}}" \
  --output json

# Filter by VPC
aws ec2 describe-nat-gateways \
  --filter "Name=vpc-id,Values={{user.vpc_id}}" \
  --output json
```

### Delete NAT Gateway

```bash
# Delete NAT Gateway
aws ec2 delete-nat-gateway \
  --nat-gateway-id "{{user.natgw_id}}" \
  --output json

# Returns: {} on success

# Release Elastic IP after NAT Gateway deletion
aws ec2 release-address \
  --allocation-id "{{user.eip_allocation_id}}" \
  --output json
```

## VPC Peering Operations

### Create VPC Peering Connection

```bash
# Create VPC Peering Connection (same region)
aws ec2 create-vpc-peering-connection \
  --vpc-id "{{user.vpc_id}}" \
  --peer-vpc-id "{{user.peer_vpc_id}}" \
  --output json

# JSON path: VpcPeeringConnection.VpcPeeringConnectionId, VpcPeeringConnection.Status.Code

# Create cross-region peering
aws ec2 create-vpc-peering-connection \
  --vpc-id "{{user.vpc_id}}" \
  --peer-vpc-id "{{user.peer_vpc_id}}" \
  --peer-region "{{user.peer_region}}" \
  --output json
```

### Accept VPC Peering Connection

```bash
# Accept peering request (in peer VPC's region)
aws ec2 accept-vpc-peering-connection \
  --vpc-peering-connection-id "{{user.peer_conn_id}}" \
  --output json

# JSON path: VpcPeeringConnection.Status.Code → "active"
```

### Describe VPC Peering Connections

```bash
# List all peering connections
aws ec2 describe-vpc-peering-connections --output json

# JSON path: VpcPeeringConnections[].VpcPeeringConnectionId, VpcPeeringConnections[].Status.Code

# Describe specific connection
aws ec2 describe-vpc-peering-connections \
  --vpc-peering-connection-ids "{{user.peer_conn_id}}" \
  --output json
```

### Reject VPC Peering Connection

```bash
# Reject peering request
aws ec2 reject-vpc-peering-connection \
  --vpc-peering-connection-id "{{user.peer_conn_id}}" \
  --output json

# Returns: {"Return": true}
```

### Delete VPC Peering Connection

```bash
# Delete peering connection
aws ec2 delete-vpc-peering-connection \
  --vpc-peering-connection-id "{{user.peer_conn_id}}" \
  --output json

# Returns: {"Return": true}
```

## CIDR Block Conventions

### Valid Private CIDR Ranges (RFC 1918)

| CIDR Block | Range | Typical Use |
|------------|-------|-------------|
| 10.0.0.0/8 | 10.0.0.0 - 10.255.255.255 | Large enterprises |
| 172.16.0.0/12 | 172.16.0.0 - 172.31.255.255 | Medium networks |
| 192.168.0.0/16 | 192.168.0.0 - 192.168.255.255 | Small networks |

### Recommended VPC Sizes

| VPC CIDR | Available IPs | Suitable For |
|----------|---------------|--------------|
| /16 | 65,534 | Production, multi-tier apps |
| /20 | 4,094 | Development, medium workloads |
| /24 | 254 | Small workloads, testing |
| /28 | 14 | Minimal resources |

### Subnet Sizing Guidelines

| Subnet CIDR | Available IPs | Typical Use |
|-------------|---------------|-------------|
| /24 | 254 | Application tier |
| /25 | 126 | Database tier |
| /26 | 62 | Management, bastion |
| /27 | 30 | Small workloads |
| /28 | 14 | Minimal resources |

**Note**: AWS reserves 5 IPs per subnet (first 4 and last 1).

## Common JSON Paths

| Resource | VpcId/SubnetId Path |
|----------|---------------------|
| VPC | `.Vpc.VpcId` |
| Subnet | `.Subnet.SubnetId` |
| Security Group | `.GroupId` |
| Route Table | `.RouteTable.RouteTableId` |
| Internet Gateway | `.InternetGateway.InternetGatewayId` |
| NAT Gateway | `.NatGateway.NatGatewayId` |
| VPC Peering | `.VpcPeeringConnection.VpcPeeringConnectionId` |

| Resource | State Path |
|----------|------------|
| VPC | `.Vpc.State` (available) |
| Subnet | `.Subnet.State` (available) |
| NAT Gateway | `.NatGateway.State` (pending → available) |
| VPC Peering | `.VpcPeeringConnection.Status.Code` (pending → active) |