# VPC Troubleshooting

Error codes, cleanup procedures, and connectivity troubleshooting.

## Error Codes
| Code | Recovery |
|------|----------|
| InvalidVpcID.NotFound / InvalidSubnetID.NotFound / InvalidSecurityGroupID.NotFound / InvalidRouteTableID.NotFound / InvalidInternetGatewayID.NotFound / InvalidNatGatewayID.NotFound / InvalidAllocationID.NotFound / InvalidVpcPeeringConnectionID.NotFound | HALT — verify ID |
| VpcLimitExceeded / NatGatewayLimitExceeded / VpcPeeringConnectionLimitExceeded / RulesPerSecurityGroupLimitExceeded | HALT — request quota increase |
| InvalidVpc.Range / InvalidVpc.CidrBlock | HALT — valid RFC 1918 CIDR |
| InvalidSubnet.Conflict | HALT — unique CIDR required |
| InvalidPeeringConnectionRange.CidrBlockOverlap | HALT — non-overlapping CIDRs |
| InvalidGroupId.Malformed | FIX — use `sg-xxxx` format |
| InvalidPermission.Duplicate | HALT — rule exists, skip |
| Resource.AlreadyAttached | HALT — detach first |
| ResourceDependencyViolation | HALT — cleanup dependencies |
| InvalidParameter | FIX_AND_RETRY |
| RequestLimitExceeded / InternalError | RETRY (backoff 3x) |

## VPC Deletion Cleanup Sequence
1. EC2 Instances → 2. NAT Gateways (wait deleted) → 3. Release EIPs → 4. Detach/Delete IGW → 5. Disassociate/Delete RTs (skip main) → 6. Delete Subnets → 7. Delete SGs (skip default) → 8. Delete VPC

## Connectivity Issues

### No Internet from Public Subnet
- Route table has `0.0.0.0/0 → igw-id`? IGW attached? SG allows outbound? Instance has public IP?

### No Internet from Private Subnet
- Route table has `0.0.0.0/0 → nat-gw-id`? NAT GW state=available? Has EIP? SG allows outbound?

### VPC Peering Issues
- Status=active? RTs on both sides have peer CIDR routes? SGs allow peer CIDR? No overlapping CIDRs?

### SG Rule Not Working
- Wrong CIDR, port, protocol? SG attached to ENI? (`describe-network-interfaces --filters "Name=group-id"`)

## Quota Issues
```bash
aws service-quotas get-service-quota --service-code ec2 --quota-code L-F678F1CE  # VPCs
aws service-quotas request-service-quota-increase --service-code ec2 --quota-code L-F678F1CE --desired-value 10
```

## CIDR Conflict
```bash
aws ec2 describe-vpcs --query 'Vpcs[].[VpcId,CidrBlock]' --output table
aws ec2 describe-subnets --filters "Name=vpc-id,Values={{id}}" --query 'Subnets[].[SubnetId,CidrBlock]' --output table
```
Peering requires non-overlapping CIDRs.

## Throttling
Exponential backoff: `delay = 2 ** attempt` (2s → 4s → 8s), max 3 retries.

## Flow Log Diagnostics
```bash
aws logs filter-log-events --log-group-name /aws/vpc/{{name}}/flow-logs --filter-pattern '[version,,,,,,,,,,,action="REJECT"]'
```