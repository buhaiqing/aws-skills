# boto3 SDK Usage for VPC Operations

Python SDK patterns. All functions use `handle_vpc_error(e)` for error handling (see Error Handling section).

## Client & Retry Config
```python
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
ec2 = boto3.client('ec2', region_name='{{env.AWS_DEFAULT_REGION}}')

# With retry
ec2 = boto3.client('ec2', config=Config(retries={'max_attempts': 3, 'mode': 'adaptive'}))
```

## Error Handling
```python
def handle_vpc_error(error):
    code = error.response['Error']['Code']
    recovery_map = {
        'InvalidVpcID.NotFound': 'HALT', 'VpcLimitExceeded': 'HALT',
        'InvalidVpc.Range': 'HALT', 'InvalidVpc.CidrBlock': 'HALT',
        'ResourceDependencyViolation': 'HALT', 'InvalidSubnetID.NotFound': 'HALT',
        'InvalidSecurityGroupID.NotFound': 'HALT', 'InvalidGroupId.Malformed': 'FIX_AND_RETRY',
        'RulesPerSecurityGroupLimitExceeded': 'HALT',
        'InvalidRouteTableID.NotFound': 'HALT', 'InvalidInternetGatewayID.NotFound': 'HALT',
        'InvalidNatGatewayID.NotFound': 'HALT', 'NatGatewayLimitExceeded': 'HALT',
        'InvalidAllocationID.NotFound': 'HALT', 'InvalidVpcPeeringConnectionID.NotFound': 'HALT',
        'VpcPeeringConnectionLimitExceeded': 'HALT', 'RequestLimitExceeded': 'RETRY',
        'InternalError': 'RETRY', 'InvalidParameter': 'FIX_AND_RETRY',
    }
    action = recovery_map.get(code, 'HALT')
    raise Exception(f"VPC Error [{code}]: {error.response['Error']['Message']}\nAction: {action}")
```

## VPC Operations
```python
def create_vpc(cidr_block, name=None):
    params = {'CidrBlock': cidr_block}
    if name: params['TagSpecifications'] = [{'ResourceType': 'vpc', 'Tags': [{'Key': 'Name', 'Value': name}]}]
    try:
        resp = ec2.create_vpc(**params)
        ec2.get_waiter('vpc_available').wait(VpcIds=[resp['Vpc']['VpcId']])
        return {'vpc_id': resp['Vpc']['VpcId'], 'cidr': resp['Vpc']['CidrBlock'], 'state': resp['Vpc']['State']}
    except ClientError as e: handle_vpc_error(e)

def describe_vpcs(vpc_ids=None, filters=None):
    params = {}
    if vpc_ids: params['VpcIds'] = vpc_ids
    if filters: params['Filters'] = filters
    vpcs = []
    for page in ec2.get_paginator('describe_vpcs').paginate(**params): vpcs.extend(page['Vpcs'])
    return vpcs

def enable_dns_attributes(vpc_id):
    try:
        ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsSupport={'Value': True})
        ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={'Value': True})
        return {'vpc_id': vpc_id, 'dns_enabled': True}
    except ClientError as e: handle_vpc_error(e)

def delete_vpc(vpc_id):
    try:
        ec2.delete_vpc(VpcId=vpc_id)
        return {'vpc_id': vpc_id, 'deleted': True}
    except ClientError as e: handle_vpc_error(e)
```

## Subnet Operations
```python
def create_subnet(vpc_id, cidr_block, az=None, name=None):
    params = {'VpcId': vpc_id, 'CidrBlock': cidr_block}
    if az: params['AvailabilityZone'] = az
    if name: params['TagSpecifications'] = [{'ResourceType': 'subnet', 'Tags': [{'Key': 'Name', 'Value': name}]}]
    try:
        resp = ec2.create_subnet(**params)
        ec2.get_waiter('subnet_available').wait(SubnetIds=[resp['Subnet']['SubnetId']])
        return {'subnet_id': resp['Subnet']['SubnetId'], 'vpc_id': resp['Subnet']['VpcId'],
                'cidr': resp['Subnet']['CidrBlock'], 'az': resp['Subnet']['AvailabilityZone']}
    except ClientError as e: handle_vpc_error(e)

def describe_subnets(subnet_ids=None, vpc_id=None):
    params = {}
    if subnet_ids: params['SubnetIds'] = subnet_ids
    elif vpc_id: params['Filters'] = [{'Name': 'vpc-id', 'Values': [vpc_id]}]
    subnets = []
    for page in ec2.get_paginator('describe_subnets').paginate(**params): subnets.extend(page['Subnets'])
    return subnets

def set_subnet_public(subnet_id):
    try:
        ec2.modify_subnet_attribute(SubnetId=subnet_id, MapPublicIpOnLaunch={'Value': True})
        return {'subnet_id': subnet_id, 'public': True}
    except ClientError as e: handle_vpc_error(e)

def set_subnet_private(subnet_id):
    try:
        ec2.modify_subnet_attribute(SubnetId=subnet_id, MapPublicIpOnLaunch={'Value': False})
        return {'subnet_id': subnet_id, 'public': False}
    except ClientError as e: handle_vpc_error(e)
```

## Security Group Operations
```python
def create_security_group(vpc_id, group_name, description):
    try:
        resp = ec2.create_security_group(GroupName=group_name, Description=description, VpcId=vpc_id)
        return {'group_id': resp['GroupId'], 'group_name': group_name}
    except ClientError as e: handle_vpc_error(e)

def describe_security_groups(group_ids=None, vpc_id=None):
    params = {}
    if group_ids: params['GroupIds'] = group_ids
    elif vpc_id: params['Filters'] = [{'Name': 'vpc-id', 'Values': [vpc_id]}]
    groups = []
    for page in ec2.get_paginator('describe_security_groups').paginate(**params): groups.extend(page['SecurityGroups'])
    return groups

def authorize_ingress(group_id, protocol, port, cidr=None, source_group_id=None):
    perm = {'IpProtocol': protocol}
    if cidr: perm.update({'FromPort': port, 'ToPort': port, 'IpRanges': [{'CidrIp': cidr}]})
    if source_group_id: perm['UserIdGroupPairs'] = [{'GroupId': source_group_id}]
    try:
        ec2.authorize_security_group_ingress(GroupId=group_id, IpPermissions=[perm])
        return {'group_id': group_id}
    except ClientError as e: handle_vpc_error(e)

def revoke_ingress(group_id, protocol, port, cidr):
    try:
        ec2.revoke_security_group_ingress(GroupId=group_id, IpPermissions=[{'IpProtocol': protocol, 'FromPort': port, 'ToPort': port, 'IpRanges': [{'CidrIp': cidr}]}])
        return {'group_id': group_id}
    except ClientError as e: handle_vpc_error(e)
```

## Route Table Operations
```python
def create_route_table(vpc_id, name=None):
    params = {'VpcId': vpc_id}
    if name: params['TagSpecifications'] = [{'ResourceType': 'route-table', 'Tags': [{'Key': 'Name', 'Value': name}]}]
    try: return {'route_table_id': ec2.create_route_table(**params)['RouteTable']['RouteTableId'], 'vpc_id': vpc_id}
    except ClientError as e: handle_vpc_error(e)

def create_route(route_table_id, destination, gateway_id=None, natgw_id=None, peer_conn_id=None):
    params = {'RouteTableId': route_table_id, 'DestinationCidrBlock': destination}
    if gateway_id: params['GatewayId'] = gateway_id
    elif natgw_id: params['NatGatewayId'] = natgw_id
    elif peer_conn_id: params['VpcPeeringConnectionId'] = peer_conn_id
    try:
        ec2.create_route(**params)
        return {'route_table_id': route_table_id}
    except ClientError as e: handle_vpc_error(e)

def associate_route_table(route_table_id, subnet_id):
    try:
        resp = ec2.associate_route_table(RouteTableId=route_table_id, SubnetId=subnet_id)
        return {'association_id': resp['AssociationId']}
    except ClientError as e: handle_vpc_error(e)
```

## Internet Gateway & NAT Gateway Operations
```python
def create_internet_gateway(vpc_id, name=None):
    params = {}
    if name: params['TagSpecifications'] = [{'ResourceType': 'internet-gateway', 'Tags': [{'Key': 'Name', 'Value': name}]}]
    try:
        resp = ec2.create_internet_gateway(**params)
        igw_id = resp['InternetGateway']['InternetGatewayId']
        ec2.attach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)
        return {'internet_gateway_id': igw_id, 'vpc_id': vpc_id}
    except ClientError as e: handle_vpc_error(e)

def delete_internet_gateway(igw_id, vpc_id):
    try:
        ec2.detach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)
        ec2.delete_internet_gateway(InternetGatewayId=igw_id)
        return {'deleted': True}
    except ClientError as e: handle_vpc_error(e)

def create_nat_gateway(subnet_id, name=None):
    try:
        eip = ec2.allocate_address(Domain='vpc')
        params = {'SubnetId': subnet_id, 'AllocationId': eip['AllocationId']}
        if name: params['TagSpecifications'] = [{'ResourceType': 'natgateway', 'Tags': [{'Key': 'Name', 'Value': name}]}]
        resp = ec2.create_nat_gateway(**params)
        ec2.get_waiter('nat_gateway_available').wait(NatGatewayIds=[resp['NatGateway']['NatGatewayId']])
        return {'nat_gateway_id': resp['NatGateway']['NatGatewayId'], 'public_ip': eip['PublicIp']}
    except ClientError as e: handle_vpc_error(e)

def delete_nat_gateway(natgw_id, allocation_id=None):
    try:
        ec2.delete_nat_gateway(NatGatewayId=natgw_id)
        ec2.get_waiter('nat_gateway_deleted').wait(NatGatewayIds=[natgw_id])
        if allocation_id: ec2.release_address(AllocationId=allocation_id)
        return {'deleted': True}
    except ClientError as e: handle_vpc_error(e)
```

## VPC Peering Operations
```python
def create_vpc_peering(vpc_id, peer_vpc_id, peer_region=None):
    params = {'VpcId': vpc_id, 'PeerVpcId': peer_vpc_id}
    if peer_region: params['PeerRegion'] = peer_region
    try:
        resp = ec2.create_vpc_peering_connection(**params)
        return {'peering_id': resp['VpcPeeringConnection']['VpcPeeringConnectionId']}
    except ClientError as e: handle_vpc_error(e)

def accept_vpc_peering(peering_id):
    try:
        ec2.accept_vpc_peering_connection(VpcPeeringConnectionId=peering_id)
        return {'peering_id': peering_id, 'status': 'active'}
    except ClientError as e: handle_vpc_error(e)
```