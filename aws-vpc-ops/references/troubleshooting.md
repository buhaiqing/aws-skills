# VPC Troubleshooting

Error codes, cleanup procedures, and connectivity troubleshooting for VPC operations.

## Error Code Reference
| Error Code | Recovery Action |
|------------|-----------------|
| InvalidVpcID.NotFound | HALT — verify VPC ID with `describe-vpcs` |
| VpcLimitExceeded | HALT — request quota increase or delete unused VPCs |
| InvalidVpc.Range / InvalidVpc.CidrBlock | HALT — use valid CIDR (RFC 1918), no overlap |
| ResourceDependencyViolation | HALT — cleanup dependencies first |
| InvalidSubnetID.NotFound | HALT — verify subnet exists |
| InvalidSubnet.Conflict | HALT — unique CIDR block required |
| InvalidSecurityGroupID.NotFound | HALT — verify SG exists |
| InvalidGroupId.Malformed | FIX — use format `sg-xxxx` |
| RulesPerSecurityGroupLimitExceeded | HALT — request quota increase (max 1000) |
| InvalidPermission.Duplicate | HALT — rule already exists, skip |
| InvalidRouteTableID.NotFound | HALT — verify route table exists |
| InvalidInternetGatewayID.NotFound | HALT — verify IGW exists |
| Resource.AlreadyAttached | HALT — IGW already attached, detach first |
| InvalidNatGatewayID.NotFound | HALT — verify NAT Gateway exists |
| NatGatewayLimitExceeded | HALT — request quota increase |
| InvalidAllocationID.NotFound | HALT — allocate EIP first |
| InvalidVpcPeeringConnectionID.NotFound | HALT — verify connection ID |
| InvalidPeeringConnectionRange.CidrBlockOverlap | HALT — CIDRs overlap, use unique ranges |
| RequestLimitExceeded | RETRY — exponential backoff, max 3 retries |
| InternalError | RETRY — 3x, then HALT |

## VPC Deletion Cleanup Sequence
```
1. EC2 Instances:   aws ec2 describe-instances --filters Name=vpc-id,Values={{id}} → terminate
2. NAT Gateways:    aws ec2 describe-nat-gateways --filter Name=vpc-id,Values={{id}} → delete → wait deleted
3. Release EIPs:    aws ec2 release-address --allocation-id {{eip}} (after NAT GW deleted)
4. Internet GW:     aws ec2 detach-internet-gateway --internet-gateway-id {{igw}} --vpc-id {{id}}
                    aws ec2 delete-internet-gateway --internet-gateway-id {{igw}}
5. Route Tables:    disassociate subnets → delete (skip main)
6. Subnets:         aws ec2 delete-subnet --subnet-id {{id}} (all subnets)
7. Security Groups: delete (except default)
8. VPC:             aws ec2 delete-vpc --vpc-id {{id}}
```

## Connectivity Issues

### No Internet from Public Subnet
1. Route table has `0.0.0.0/0 → igw-id`?
2. IGW attached to VPC? (`describe-internet-gateways --filters "Name=attachment.vpc-id"`)
3. SG allows outbound traffic?
4. Instance has public IP? Subnet auto-assign public IP enabled?

### No Internet from Private Subnet
1. Route table has `0.0.0.0/0 → nat-gw-id`?
2. NAT Gateway in public subnet, state=`available`?
3. NAT Gateway has Elastic IP? (`describe-nat-gateways --nat-gateway-ids {{id}}`)
4. SG allows outbound traffic?

### VPC Peering Issues
1. Peering status = `active`? (`describe-vpc-peering-connections`)
2. Route tables on BOTH sides have peer CIDR routes?
3. SGs allow traffic from peer CIDR?
4. No overlapping CIDRs?

### Security Group Rule Not Working
- Wrong CIDR (use instance's public IP or 0.0.0.0/0 for testing)
- Wrong port or protocol (TCP vs UDP)
- SG not attached to ENI (`describe-network-interfaces --filters "Name=group-id"`)

## Quota Issues
```bash
# Check & request increase
aws service-quotas get-service-quota --service-code ec2 --quota-code L-F678F1CE  # VPCs
aws service-quotas request-service-quota-increase --service-code ec2 --quota-code L-F678F1CE --desired-value 10
```

## CIDR Conflict Resolution
```bash
# List all VPCs and subnets
aws ec2 describe-vpcs --query 'Vpcs[].[VpcId,CidrBlock]' --output table
aws ec2 describe-subnets --filters "Name=vpc-id,Values={{id}}" --query 'Subnets[].[SubnetId,CidrBlock]' --output table
```
**Peering**: Requires non-overlapping CIDRs. If overlap exists, create new VPC with unique CIDR.

## Throttling
Exponential backoff: `delay = 2 ** attempt` (2s → 4s → 8s), max 3 retries.

## VPC Flow Logs for Diagnostics
```bash
aws ec2 create-flow-logs --resource-type VPC --resource-ids {{id}} --traffic-type ALL --log-group-name /aws/vpc/{{name}}/flow-logs --deliver-logs-permission-arn {{role_arn}}
aws logs filter-log-events --log-group-name /aws/vpc/{{name}}/flow-logs --filter-pattern '[version,,,,,,,,,,,action="REJECT"]'
```