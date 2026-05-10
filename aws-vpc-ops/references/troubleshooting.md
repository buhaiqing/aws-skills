# VPC Troubleshooting

Error codes, common issues, and recovery procedures for VPC operations.

## Error Code Reference

### VPC Errors

| Error Code | Cause | Recovery Action |
|------------|-------|-----------------|
| `InvalidVpcID.NotFound` | VPC ID does not exist | HALT - verify VPC ID with describe-vpcs |
| `VpcLimitExceeded` | Region quota reached | HALT - request quota increase or delete unused VPCs |
| `InvalidVpc.Range` | CIDR block invalid format | HALT - use valid CIDR notation (RFC 1918) |
| `InvalidVpc.CidrBlock` | CIDR overlap or invalid size | HALT - verify no overlap with existing VPCs |
| `ResourceDependencyViolation` | VPC contains resources | HALT - cleanup dependencies first |
| `OperationNotPermitted` | Default VPC cannot be deleted | HALT - cannot delete default VPC |

### Subnet Errors

| Error Code | Cause | Recovery Action |
|------------|-------|-----------------|
| `InvalidSubnetID.NotFound` | Subnet ID does not exist | HALT - verify subnet exists |
| `InvalidSubnet.Range` | CIDR block invalid | HALT - use valid CIDR within VPC range |
| `InvalidSubnet.Conflict` | CIDR overlaps with existing subnet | HALT - use unique CIDR block |
| `SubnetNotAvailable` | Availability Zone unavailable | RETRY - try different AZ |

### Security Group Errors

| Error Code | Cause | Recovery Action |
|------------|-------|-----------------|
| `InvalidSecurityGroupID.NotFound` | Security Group ID does not exist | HALT - verify SG exists |
| `InvalidGroup.NotFound` | Security Group name not found | HALT - use GroupId instead |
| `InvalidGroupId.Malformed` | Invalid SG ID format | FIX_AND_RETRY - use format sg-xxxx |
| `RulesPerSecurityGroupLimitExceeded` | Rule quota exceeded | HALT - request quota increase |
| `InvalidPermission.NotFound` | Rule does not exist | HALT - rule already revoked |
| `InvalidPermission.Duplicate` | Rule already exists | HALT - skip duplicate rule |

### Route Table Errors

| Error Code | Cause | Recovery Action |
|------------|-------|-----------------|
| `InvalidRouteTableID.NotFound` | Route Table ID does not exist | HALT - verify route table exists |
| `InvalidRoute.NotFound` | Route does not exist | HALT - cannot delete non-existent route |
| `InvalidRoute.Conflict` | Route already exists | HALT - update existing route |
| `RouteNotSupported` | Invalid target for route | FIX_AND_RETRY - use valid gateway ID |

### Internet Gateway Errors

| Error Code | Cause | Recovery Action |
|------------|-------|-----------------|
| `InvalidInternetGatewayID.NotFound` | IGW ID does not exist | HALT - verify IGW exists |
| `InternetGatewayLimitExceeded` | IGW quota reached | HALT - request quota increase |
| `Resource.AlreadyAttached` | IGW already attached | HALT - detach first before new attachment |

### NAT Gateway Errors

| Error Code | Cause | Recovery Action |
|------------|-------|-----------------|
| `InvalidNatGatewayID.NotFound` | NAT Gateway ID does not exist | HALT - verify NAT Gateway exists |
| `NatGatewayLimitExceeded` | NAT Gateway quota reached | HALT - request quota increase |
| `InvalidAllocationID.NotFound` | Elastic IP allocation ID not found | HALT - allocate EIP first |
| `Resource.AlreadyAssociated` | EIP already associated | HALT - use different EIP |

### VPC Peering Errors

| Error Code | Cause | Recovery Action |
|------------|-------|-----------------|
| `InvalidVpcPeeringConnectionID.NotFound` | Peering connection not found | HALT - verify connection ID |
| `InvalidVpcPeeringConnectionState.Transition` | Invalid state for operation | HALT - check connection status |
| `VpcPeeringConnectionLimitExceeded` | Peering quota reached | HALT - request quota increase |
| `InvalidPeeringConnectionRange.CidrBlockOverlap` | CIDRs overlap | HALT - use non-overlapping CIDRs |

## Dependency Cleanup Sequence

### VPC Deletion Failure

When `delete-vpc` returns `ResourceDependencyViolation`:

```
Error: The VPC 'vpc-xxx' has dependencies and cannot be deleted.
```

**Required cleanup order**:

```
1. EC2 Instances → describe-instances → terminate
2. NAT Gateways → describe-nat-gateways → delete → wait for 'deleted'
3. Release Elastic IPs → release-address (after NAT GW deleted)
4. Internet Gateway → detach-internet-gateway → delete-internet-gateway
5. Route Tables → disassociate-route-table → delete-route-table (except main)
6. Network ACLs → replace-network-acl-association (restore default) → delete
7. Subnets → delete-subnet (all subnets)
8. Security Groups → delete-security-group (except default)
9. VPC → delete-vpc
```

### Cleanup CLI Commands

```bash
# Step 1: List and terminate EC2 instances
aws ec2 describe-instances \
  --filters "Name=vpc-id,Values={{user.vpc_id}}" \
  --query 'Reservations[].Instances[].InstanceId' \
  --output text

aws ec2 terminate-instances --instance-ids i-xxx

# Step 2: Delete NAT Gateways
aws ec2 describe-nat-gateways \
  --filter "Name=vpc-id,Values={{user.vpc_id}}" \
  --query 'NatGateways[].NatGatewayId' \
  --output text

aws ec2 delete-nat-gateway --nat-gateway-id nat-xxx

# Wait for NAT Gateway deletion
aws ec2 wait nat-gateway-deleted --nat-gateway-ids nat-xxx

# Step 3: Release Elastic IPs
aws ec2 describe-addresses \
  --filters "Name=association-id,Values={{user.allocation_id}}" \
  --output json

aws ec2 release-address --allocation-id eipalloc-xxx

# Step 4: Detach and delete Internet Gateway
aws ec2 describe-internet-gateways \
  --filters "Name=attachment.vpc-id,Values={{user.vpc_id}}" \
  --query 'InternetGateways[].InternetGatewayId' \
  --output text

aws ec2 detach-internet-gateway \
  --internet-gateway-id igw-xxx \
  --vpc-id {{user.vpc_id}}

aws ec2 delete-internet-gateway --internet-gateway-id igw-xxx

# Step 5: Delete Route Tables (except main)
aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values={{user.vpc_id}}" \
  --output json

# Disassociate subnets first
aws ec2 disassociate-route-table --association-id rtbassoc-xxx

# Delete route table (skip main)
aws ec2 delete-route-table --route-table-id rtb-xxx

# Step 6: Delete Subnets
aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values={{user.vpc_id}}" \
  --query 'Subnets[].SubnetId' \
  --output text

aws ec2 delete-subnet --subnet-id subnet-xxx

# Step 7: Delete Security Groups (except default)
aws ec2 describe-security-groups \
  --filters "Name=vpc-id,Values={{user.vpc_id}}" \
  --output json

# Skip default security group
aws ec2 delete-security-group --group-id sg-xxx

# Step 8: Delete VPC
aws ec2 delete-vpc --vpc-id {{user.vpc_id}}
```

## CIDR Conflict Resolution

### Overlapping CIDRs

**Symptom**:
```
Error: The CIDR '10.0.0.0/16' conflicts with another VPC's CIDR
```

**Diagnosis**:
```bash
# List all VPCs and their CIDRs
aws ec2 describe-vpcs \
  --query 'Vpcs[].[VpcId,CidrBlock]' \
  --output table
```

**Resolution**:
1. Choose a different CIDR block
2. Use non-overlapping ranges:
   - VPC 1: 10.0.0.0/16
   - VPC 2: 10.1.0.0/16
   - VPC 3: 172.16.0.0/16

### Subnet CIDR Overlap

**Symptom**:
```
Error: The CIDR '10.0.1.0/24' conflicts with subnet 'subnet-xxx'
```

**Diagnosis**:
```bash
# List subnets in VPC with CIDRs
aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values={{user.vpc_id}}" \
  --query 'Subnets[].[SubnetId,CidrBlock]' \
  --output table
```

**Resolution**:
1. Delete conflicting subnet first (if empty)
2. Use non-overlapping CIDRs

### VPC Peering CIDR Overlap

**Symptom**:
```
Error: VPC peering connection cannot be created due to CIDR overlap
```

**Check**:
```bash
# Compare VPC CIDRs
aws ec2 describe-vpcs --vpc-ids vpc-xxx vpc-yyy \
  --query 'Vpcs[].[VpcId,CidrBlock]' \
  --output table
```

**Resolution**:
1. VPC Peering requires non-overlapping CIDRs
2. Cannot create peering if CIDRs overlap
3. Option: Create new VPC with unique CIDR

## Connectivity Issues

### No Internet Access from Public Subnet

**Checklist**:
1. Route table has route to IGW: `0.0.0.0/0 → igw-xxx`
2. Internet Gateway attached to VPC
3. Security Group allows outbound traffic
4. Instance has public IP assigned
5. Subnet has auto-assign public IP enabled

**Diagnosis**:
```bash
# Check route table
aws ec2 describe-route-tables \
  --filters "Name=association.subnet-id,Values={{user.subnet_id}}" \
  --query 'RouteTables[].Routes[]'

# Check IGW attachment
aws ec2 describe-internet-gateways \
  --filters "Name=attachment.vpc-id,Values={{user.vpc_id}}"

# Check instance public IP
aws ec2 describe-instances \
  --filters "Name=vpc-id,Values={{user.vpc_id}}" \
  --query 'Reservations[].Instances[].PublicIpAddress'
```

### No Internet Access from Private Subnet

**Checklist**:
1. Route table has route to NAT Gateway: `0.0.0.0/0 → nat-xxx`
2. NAT Gateway is in public subnet
3. NAT Gateway state is 'available'
4. NAT Gateway has Elastic IP
5. Security Group allows outbound traffic

**Diagnosis**:
```bash
# Check NAT Gateway status
aws ec2 describe-nat-gateways \
  --nat-gateway-ids {{user.natgw_id}} \
  --query 'NatGateways[].State'

# Check route table for NAT route
aws ec2 describe-route-tables \
  --filters "Name=association.subnet-id,Values={{user.private_subnet_id}}" \
  --query 'RouteTables[].Routes[]'

# Check NAT Gateway subnet (must be public)
aws ec2 describe-nat-gateways \
  --nat-gateway-ids {{user.natgw_id}} \
  --query 'NatGateways[].SubnetId'
```

### VPC Peering Connectivity Issues

**Checklist**:
1. Peering connection status is 'active'
2. Route tables on both VPCs have peer routes
3. Security Groups allow traffic from peer CIDR
4. No overlapping CIDRs blocking routes

**Diagnosis**:
```bash
# Check peering status
aws ec2 describe-vpc-peering-connections \
  --vpc-peering-connection-ids {{user.peer_conn_id}} \
  --query 'VpcPeeringConnections[].Status'

# Check routes on both sides
aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values={{user.vpc_id}}" \
  --query 'RouteTables[].Routes[]'

# Check security group rules
aws ec2 describe-security-groups \
  --filters "Name=vpc-id,Values={{user.vpc_id}}" \
  --query 'SecurityGroups[].IpPermissions'
```

### Security Group Rule Not Working

**Common Issues**:

1. **Wrong CIDR**: Use instance's public IP or 0.0.0.0/0
2. **Wrong Port**: Check application listening port
3. **Protocol Mismatch**: TCP vs UDP
4. **Rule not applied**: Verify SG is attached to ENI

**Diagnosis**:
```bash
# Check security group rules
aws ec2 describe-security-groups \
  --group-ids {{user.sg_id}} \
  --query 'SecurityGroups[].IpPermissions[]'

# Check which ENI has the security group
aws ec2 describe-network-interfaces \
  --filters "Name=group-id,Values={{user.sg_id}}" \
  --query 'NetworkInterfaces[].[NetworkInterfaceId,Attachment.InstanceId]'

# Verify instance is running
aws ec2 describe-instances \
  --instance-ids {{user.instance_id}} \
  --query 'Reservations[].Instances[].State'
```

## Quota Exceeded Resolution

### VPC Limit Exceeded

**Symptom**:
```
Error: You have reached the limit of VPCs for this region (5)
```

**Resolution**:
1. Delete unused VPCs
2. Request quota increase

```bash
# Request quota increase
aws service-quotas request-service-quota-increase \
  --service-code ec2 \
  --quota-code L-F678F1CE \
  --desired-value 10

# Check current quota
aws service-quotas get-service-quota \
  --service-code ec2 \
  --quota-code L-F678F1CE
```

### NAT Gateway Limit Exceeded

**Symptom**:
```
Error: You have reached the limit of NAT Gateways for this AZ (5)
```

**Resolution**:
```bash
# Request quota increase
aws service-quotas request-service-quota-increase \
  --service-code ec2 \
  --quota-code L-3633C6E3 \
  --desired-value 10
```

### Security Group Rules Limit

**Symptom**:
```
Error: RulesPerSecurityGroupLimitExceeded: The maximum number of rules has been reached
```

**Resolution**:
1. Remove unused rules
2. Request quota increase (max 1,000)

```bash
# Request quota increase
aws service-quotas request-service-quota-increase \
  --service-code ec2 \
  --quota-code L-7F3D9F25 \
  --desired-value 200
```

## API Throttling

### RequestLimitExceeded

**Symptom**:
```
Error: RequestLimitExceeded: Request has exceeded the allowed rate
```

**Recovery**:
1. Exponential backoff (2s → 4s → 8s)
2. Reduce concurrent requests
3. Use pagination instead of multiple calls

**Pattern**:
```python
import time

def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except ClientError as e:
            if e.response['Error']['Code'] != 'RequestLimitExceeded':
                raise
            delay = 2 ** attempt
            time.sleep(delay)
```

## VPC Flow Logs for Troubleshooting

### Enable VPC Flow Logs

```bash
# Create flow log for VPC
aws ec2 create-flow-logs \
  --resource-type VPC \
  --resource-ids {{user.vpc_id}} \
  --traffic-type ALL \
  --log-group-name /aws/vpc/{{user.vpc_name}}/flow-logs \
  --deliver-logs-permission-arn arn:aws:iam::xxx:role/flow-logs-role \
  --output json
```

### Analyze Rejected Traffic

```bash
# Query CloudWatch Logs for rejected traffic
aws logs filter-log-events \
  --log-group-name /aws/vpc/{{user.vpc_name}}/flow-logs \
  --filter-pattern '[version, account_id, interface_id, srcaddr, dstaddr, srcport, dstport, protocol, packets, bytes, start, end, action="REJECT", log_status]'
```

## Common Scenarios

### Cannot Delete VPC - Dependencies

1. Run `describe-instances` to find EC2 instances
2. Terminate all instances or move to different VPC
3. Delete all NAT Gateways (wait for deletion)
4. Detach and delete Internet Gateway
5. Delete all Route Tables (except main)
6. Delete all Subnets
7. Delete all Security Groups (except default)
8. Finally delete VPC

### Instance Cannot Connect to Internet

1. Verify instance is in public subnet (or private with NAT)
2. Check route table has 0.0.0.0/0 route to IGW or NAT
3. Verify Security Group allows outbound traffic
4. Check instance has public IP (public subnet)
5. Enable auto-assign public IP on subnet (public subnet)

### VPC Peering Not Working

1. Accept peering connection request
2. Add route to peer CIDR in both VPC route tables
3. Update Security Groups to allow peer CIDR traffic
4. Verify no firewall blocking traffic (Network ACL)

### NAT Gateway Pending Too Long

1. NAT Gateway creation takes 2-5 minutes normally
2. If stuck in 'pending' for >15 minutes:
   - Check subnet has route to IGW
   - Verify EIP allocation was successful
   - Try creating new NAT Gateway in different AZ