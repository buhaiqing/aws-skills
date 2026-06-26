# boto3 SDK Usage for VPC Operations

Python SDK patterns. All functions use `handle_vpc_error(e)`.

## Client Setup
```python
import boto3
from botocore.exceptions import ClientError
ec2 = boto3.client('ec2', region_name='{{env.AWS_DEFAULT_REGION}}')
```

## Error Handling
```python
def handle_vpc_error(e):
    code = e.response['Error']['Code']
    action = {'InvalidVpcID.NotFound': 'HALT', 'VpcLimitExceeded': 'HALT', 'InvalidVpc.Range': 'HALT',
        'InvalidVpc.CidrBlock': 'HALT', 'ResourceDependencyViolation': 'HALT',
        'InvalidSubnetID.NotFound': 'HALT', 'InvalidSubnet.Conflict': 'HALT',
        'InvalidSecurityGroupID.NotFound': 'HALT', 'InvalidGroupId.Malformed': 'FIX_AND_RETRY',
        'RulesPerSecurityGroupLimitExceeded': 'HALT', 'InvalidRouteTableID.NotFound': 'HALT',
        'InvalidInternetGatewayID.NotFound': 'HALT', 'InvalidNatGatewayID.NotFound': 'HALT',
        'NatGatewayLimitExceeded': 'HALT', 'InvalidAllocationID.NotFound': 'HALT',
        'InvalidVpcPeeringConnectionID.NotFound': 'HALT', 'VpcPeeringConnectionLimitExceeded': 'HALT',
        'RequestLimitExceeded': 'RETRY', 'InternalError': 'RETRY', 'InvalidParameter': 'FIX_AND_RETRY',
    }.get(code, 'HALT')
    raise Exception(f"VPC Error [{code}]: {e.response['Error']['Message']}\nAction: {action}")
```

## VPC
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
    try: ec2.delete_vpc(VpcId=vpc_id); return {'vpc_id': vpc_id, 'deleted': True}
    except ClientError as e: handle_vpc_error(e)
```

## Subnet
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

def set_subnet_public(subnet_id, pub=True):
    try:
        ec2.modify_subnet_attribute(SubnetId=subnet_id, MapPublicIpOnLaunch={'Value': pub})
        return {'subnet_id': subnet_id, 'public': pub}
    except ClientError as e: handle_vpc_error(e)
```

## Security Group
```python
def create_security_group(vpc_id, group_name, description):
    try:
        resp = ec2.create_security_group(GroupName=group_name, Description=description, VpcId=vpc_id)
        return {'group_id': resp['GroupId'], 'group_name': group_name}
    except ClientError as e: handle_vpc_error(e)

def authorize_ingress(group_id, protocol, port, cidr=None, source_group_id=None):
    perm = {'IpProtocol': protocol}
    if cidr: perm.update({'FromPort': port, 'ToPort': port, 'IpRanges': [{'CidrIp': cidr}]})
    if source_group_id: perm['UserIdGroupPairs'] = [{'GroupId': source_group_id}]
    try: ec2.authorize_security_group_ingress(GroupId=group_id, IpPermissions=[perm]); return {'group_id': group_id}
    except ClientError as e: handle_vpc_error(e)

def revoke_ingress(group_id, protocol, port, cidr):
    try:
        ec2.revoke_security_group_ingress(GroupId=group_id, IpPermissions=[
            {'IpProtocol': protocol, 'FromPort': port, 'ToPort': port, 'IpRanges': [{'CidrIp': cidr}]}])
        return {'group_id': group_id}
    except ClientError as e: handle_vpc_error(e)
```

## Route Table
```python
def create_route_table(vpc_id):
    try: return {'route_table_id': ec2.create_route_table(VpcId=vpc_id)['RouteTable']['RouteTableId'], 'vpc_id': vpc_id}
    except ClientError as e: handle_vpc_error(e)

def create_route(route_table_id, destination, gateway_id=None, natgw_id=None, peer_conn_id=None):
    params = {'RouteTableId': route_table_id, 'DestinationCidrBlock': destination}
    if gateway_id: params['GatewayId'] = gateway_id
    elif natgw_id: params['NatGatewayId'] = natgw_id
    elif peer_conn_id: params['VpcPeeringConnectionId'] = peer_conn_id
    try: ec2.create_route(**params); return {'route_table_id': route_table_id}
    except ClientError as e: handle_vpc_error(e)

def associate_route_table(route_table_id, subnet_id):
    try: return {'association_id': ec2.associate_route_table(RouteTableId=route_table_id, SubnetId=subnet_id)['AssociationId']}
    except ClientError as e: handle_vpc_error(e)
```

## IGW & NAT Gateway
```python
def create_internet_gateway(vpc_id):
    try:
        resp = ec2.create_internet_gateway(); igw_id = resp['InternetGateway']['InternetGatewayId']
        ec2.attach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)
        return {'internet_gateway_id': igw_id, 'vpc_id': vpc_id}
    except ClientError as e: handle_vpc_error(e)

def delete_internet_gateway(igw_id, vpc_id):
    try:
        ec2.detach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)
        ec2.delete_internet_gateway(InternetGatewayId=igw_id); return {'deleted': True}
    except ClientError as e: handle_vpc_error(e)

def create_nat_gateway(subnet_id):
    try:
        eip = ec2.allocate_address(Domain='vpc')
        resp = ec2.create_nat_gateway(SubnetId=subnet_id, AllocationId=eip['AllocationId'])
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

## VPC Peering
```python
def create_vpc_peering(vpc_id, peer_vpc_id, peer_region=None):
    params = {'VpcId': vpc_id, 'PeerVpcId': peer_vpc_id}
    if peer_region: params['PeerRegion'] = peer_region
    try: return {'peering_id': ec2.create_vpc_peering_connection(**params)['VpcPeeringConnection']['VpcPeeringConnectionId']}
    except ClientError as e: handle_vpc_error(e)

def accept_vpc_peering(peering_id):
    try: ec2.accept_vpc_peering_connection(VpcPeeringConnectionId=peering_id); return {'peering_id': peering_id, 'status': 'active'}
    except ClientError as e: handle_vpc_error(e)
```