# boto3 SDK Usage for VPC Operations

Python SDK patterns for AWS VPC operations with error handling and pagination.

## Prerequisites

```bash
# Install boto3 with uv
uv add boto3

# Or with pip
pip install boto3
```

## Client Initialization

```python
import boto3
from botocore.exceptions import ClientError

# Initialize EC2 client (VPC operations use EC2 API)
ec2 = boto3.client(
    'ec2',
    region_name='{{env.AWS_DEFAULT_REGION}}',
    aws_access_key_id='{{env.AWS_ACCESS_KEY_ID}}',
    aws_secret_access_key='{{env.AWS_SECRET_ACCESS_KEY}}',
    aws_session_token='{{env.AWS_SESSION_TOKEN}}'  # Optional for temporary creds
)

# Or use default credential chain (environment, ~/.aws/credentials, IAM role)
ec2 = boto3.client('ec2', region_name='{{env.AWS_DEFAULT_REGION}}')
```

## Error Handling Pattern

```python
from botocore.exceptions import ClientError

def handle_vpc_error(error: ClientError) -> dict:
    """Standardized VPC error handling."""
    error_code = error.response['Error']['Code']
    error_message = error.response['Error']['Message']

    recovery_map = {
        'InvalidVpcID.NotFound': 'HALT',
        'VpcLimitExceeded': 'HALT',
        'InvalidVpc.Range': 'HALT',
        'InvalidVpc.CidrBlock': 'HALT',
        'ResourceDependencyViolation': 'HALT',
        'RequestLimitExceeded': 'RETRY',
        'InternalError': 'RETRY',
        'InvalidParameter': 'FIX_AND_RETRY'
    }

    action = recovery_map.get(error_code, 'HALT')

    return {
        'error_code': error_code,
        'message': error_message,
        'action': action,
        'retry': action == 'RETRY'
    }
```

## Retry with Exponential Backoff

```python
import time
from botocore.config import Config

# Configure retry strategy
config = Config(
    retries={
        'max_attempts': 3,
        'mode': 'adaptive'
    }
)

ec2 = boto3.client('ec2', config=config)

# Manual retry with exponential backoff
def retry_operation(operation, max_retries=3, base_delay=2):
    """Retry operation with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return operation()
        except ClientError as e:
            error_info = handle_vpc_error(e)
            if not error_info['retry'] or attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            time.sleep(delay)
```

## VPC Operations

### Create VPC

```python
def create_vpc(cidr_block: str, name: str = None) -> dict:
    """Create a VPC with optional name tag."""
    try:
        params = {'CidrBlock': cidr_block}

        if name:
            params['TagSpecifications'] = [
                {
                    'ResourceType': 'vpc',
                    'Tags': [{'Key': 'Name', 'Value': name}]
                }
            ]

        response = ec2.create_vpc(**params)

        vpc_id = response['Vpc']['VpcId']

        # Wait for VPC to be available
        waiter = ec2.get_waiter('vpc_available')
        waiter.wait(VpcIds=[vpc_id])

        return {
            'vpc_id': vpc_id,
            'cidr_block': response['Vpc']['CidrBlock'],
            'state': response['Vpc']['State'],
            'success': True
        }

    except ClientError as e:
        return {'success': False, 'error': handle_vpc_error(e)}
```

### Describe VPCs

```python
def describe_vpcs(vpc_ids: list = None, filters: list = None) -> list:
    """Describe VPCs with pagination."""
    vpcs = []

    params = {}
    if vpc_ids:
        params['VpcIds'] = vpc_ids
    if filters:
        params['Filters'] = filters

    paginator = ec2.get_paginator('describe_vpcs')

    for page in paginator.paginate(**params):
        vpcs.extend(page['Vpcs'])

    return vpcs

# Usage examples
all_vpcs = describe_vpcs()

specific_vpc = describe_vpcs(vpc_ids=['vpc-0a1b2c3d4e5f6g7h'])

filtered_vpcs = describe_vpcs(filters=[
    {'Name': 'tag:Name', 'Values': ['production-vpc']},
    {'Name': 'cidr-block', 'Values': ['10.0.0.0/16']}
])
```

### Modify VPC Attributes

```python
def enable_dns_attributes(vpc_id: str) -> dict:
    """Enable DNS support and hostnames."""
    try:
        ec2.modify_vpc_attribute(
            VpcId=vpc_id,
            EnableDnsSupport={'Value': True}
        )

        ec2.modify_vpc_attribute(
            VpcId=vpc_id,
            EnableDnsHostnames={'Value': True}
        )

        return {'vpc_id': vpc_id, 'dns_enabled': True, 'success': True}

    except ClientError as e:
        return {'success': False, 'error': handle_vpc_error(e)}
```

### Delete VPC

```python
def delete_vpc(vpc_id: str) -> dict:
    """Delete VPC after verifying dependencies."""
    try:
        # Check for dependencies before deletion
        dependencies = check_vpc_dependencies(vpc_id)

        if dependencies['has_dependencies']:
            return {
                'success': False,
                'reason': 'ResourceDependencyViolation',
                'dependencies': dependencies
            }

        ec2.delete_vpc(VpcId=vpc_id)

        return {'vpc_id': vpc_id, 'success': True}

    except ClientError as e:
        return {'success': False, 'error': handle_vpc_error(e)}

def check_vpc_dependencies(vpc_id: str) -> dict:
    """Check for resources that prevent VPC deletion."""
    # Check subnets
    subnets = ec2.describe_subnets(Filters=[
        {'Name': 'vpc-id', 'Values': [vpc_id]}
    ])['Subnets']

    # Check instances
    instances = ec2.describe_instances(Filters=[
        {'Name': 'vpc-id', 'Values': [vpc_id]}
    ])['Reservations']

    # Check security groups (excluding default)
    sg_response = ec2.describe_security_groups(Filters=[
        {'Name': 'vpc-id', 'Values': [vpc_id]}
    ])['SecurityGroups']

    # Check Internet Gateway attachment
    igw_response = ec2.describe_internet_gateways(Filters=[
        {'Name': 'attachment.vpc-id', 'Values': [vpc_id]}
    ])['InternetGateways']

    # Check NAT Gateways
    natgw_response = ec2.describe_nat_gateways(Filters=[
        {'Name': 'vpc-id', 'Values': [vpc_id]}
    ])['NatGateways']

    has_deps = (
        len(subnets) > 0 or
        len(instances) > 0 or
        len([sg for sg in sg_response if sg['GroupName'] != 'default']) > 0 or
        len(igw_response) > 0 or
        len(natgw_response) > 0
    )

    return {
        'has_dependencies': has_deps,
        'subnets': [s['SubnetId'] for s in subnets],
        'instances': [i['InstanceId'] for r in instances for i in r['Instances']],
        'internet_gateways': [igw['InternetGatewayId'] for igw in igw_response],
        'nat_gateways': [ng['NatGatewayId'] for ng in natgw_response]
    }
```

## Subnet Operations

### Create Subnet

```python
def create_subnet(vpc_id: str, cidr_block: str, az: str = None, name: str = None) -> dict:
    """Create a subnet in a VPC."""
    try:
        params = {
            'VpcId': vpc_id,
            'CidrBlock': cidr_block
        }

        if az:
            params['AvailabilityZone'] = az

        if name:
            params['TagSpecifications'] = [
                {
                    'ResourceType': 'subnet',
                    'Tags': [{'Key': 'Name', 'Value': name}]
                }
            ]

        response = ec2.create_subnet(**params)

        subnet_id = response['Subnet']['SubnetId']

        # Wait for subnet to be available
        waiter = ec2.get_waiter('subnet_available')
        waiter.wait(SubnetIds=[subnet_id])

        return {
            'subnet_id': subnet_id,
            'vpc_id': response['Subnet']['VpcId'],
            'cidr_block': response['Subnet']['CidrBlock'],
            'availability_zone': response['Subnet']['AvailabilityZone'],
            'success': True
        }

    except ClientError as e:
        return {'success': False, 'error': handle_vpc_error(e)}
```

### Describe Subnets

```python
def describe_subnets(subnet_ids: list = None, vpc_id: str = None) -> list:
    """Describe subnets with pagination."""
    subnets = []

    params = {}
    if subnet_ids:
        params['SubnetIds'] = subnet_ids
    elif vpc_id:
        params['Filters'] = [{'Name': 'vpc-id', 'Values': [vpc_id]}]

    paginator = ec2.get_paginator('describe_subnets')

    for page in paginator.paginate(**params):
        subnets.extend(page['Subnets'])

    return subnets
```

### Modify Subnet Attributes

```python
def set_subnet_public(subnet_id: str) -> dict:
    """Enable auto-assign public IP for public subnet."""
    try:
        ec2.modify_subnet_attribute(
            SubnetId=subnet_id,
            MapPublicIpOnLaunch={'Value': True}
        )

        return {'subnet_id': subnet_id, 'public': True, 'success': True}

    except ClientError as e:
        return {'success': False, 'error': handle_vpc_error(e)}

def set_subnet_private(subnet_id: str) -> dict:
    """Disable auto-assign public IP for private subnet."""
    try:
        ec2.modify_subnet_attribute(
            SubnetId=subnet_id,
            MapPublicIpOnLaunch={'Value': False}
        )

        return {'subnet_id': subnet_id, 'public': False, 'success': True}

    except ClientError as e:
        return {'success': False, 'error': handle_vpc_error(e)}
```

## Security Group Operations

### Create Security Group

```python
def create_security_group(vpc_id: str, group_name: str, description: str) -> dict:
    """Create a security group in a VPC."""
    try:
        response = ec2.create_security_group(
            GroupName=group_name,
            Description=description,
            VpcId=vpc_id
        )

        return {
            'group_id': response['GroupId'],
            'group_name': group_name,
            'success': True
        }

    except ClientError as e:
        return {'success': False, 'error': handle_vpc_error(e)}
```

### Describe Security Groups

```python
def describe_security_groups(group_ids: list = None, vpc_id: str = None) -> list:
    """Describe security groups with pagination."""
    groups = []

    params = {}
    if group_ids:
        params['GroupIds'] = group_ids
    elif vpc_id:
        params['Filters'] = [{'Name': 'vpc-id', 'Values': [vpc_id]}]

    paginator = ec2.get_paginator('describe_security_groups')

    for page in paginator.paginate(**params):
        groups.extend(page['SecurityGroups'])

    return groups
```

### Authorize Security Group Rules

```python
def authorize_ingress(group_id: str, protocol: str, port: int, cidr: str) -> dict:
    """Add an ingress rule to security group."""
    try:
        ec2.authorize_security_group_ingress(
            GroupId=group_id,
            IpPermissions=[
                {
                    'IpProtocol': protocol,
                    'FromPort': port,
                    'ToPort': port,
                    'IpRanges': [{'CidrIp': cidr}]
                }
            ]
        )

        return {'group_id': group_id, 'success': True}

    except ClientError as e:
        return {'success': False, 'error': handle_vpc_error(e)}

def authorize_ingress_from_sg(group_id: str, source_group_id: str, protocol: str = '-1') -> dict:
    """Allow all traffic from another security group."""
    try:
        ec2.authorize_security_group_ingress(
            GroupId=group_id,
            IpPermissions=[
                {
                    'IpProtocol': protocol,
                    'UserIdGroupPairs': [{'GroupId': source_group_id}]
                }
            ]
        )

        return {'group_id': group_id, 'source_group_id': source_group_id, 'success': True}

    except ClientError as e:
        return {'success': False, 'error': handle_vpc_error(e)}
```

### Revoke Security Group Rules

```python
def revoke_ingress(group_id: str, protocol: str, port: int, cidr: str) -> dict:
    """Remove an ingress rule from security group."""
    try:
        ec2.revoke_security_group_ingress(
            GroupId=group_id,
            IpPermissions=[
                {
                    'IpProtocol': protocol,
                    'FromPort': port,
                    'ToPort': port,
                    'IpRanges': [{'CidrIp': cidr}]
                }
            ]
        )

        return {'group_id': group_id, 'success': True}

    except ClientError as e:
        return {'success': False, 'error': handle_vpc_error(e)}
```

## Route Table Operations

### Create Route Table

```python
def create_route_table(vpc_id: str, name: str = None) -> dict:
    """Create a route table in a VPC."""
    try:
        params = {'VpcId': vpc_id}

        if name:
            params['TagSpecifications'] = [
                {
                    'ResourceType': 'route-table',
                    'Tags': [{'Key': 'Name', 'Value': name}]
                }
            ]

        response = ec2.create_route_table(**params)

        return {
            'route_table_id': response['RouteTable']['RouteTableId'],
            'vpc_id': vpc_id,
            'success': True
        }

    except ClientError as e:
        return {'success': False, 'error': handle_vpc_error(e)}
```

### Create Route

```python
def create_route_to_igw(route_table_id: str, igw_id: str) -> dict:
    """Add route to Internet Gateway."""
    try:
        ec2.create_route(
            RouteTableId=route_table_id,
            DestinationCidrBlock='0.0.0.0/0',
            GatewayId=igw_id
        )

        return {'route_table_id': route_table_id, 'igw_id': igw_id, 'success': True}

    except ClientError as e:
        return {'success': False, 'error': handle_vpc_error(e)}

def create_route_to_natgw(route_table_id: str, natgw_id: str) -> dict:
    """Add route to NAT Gateway."""
    try:
        ec2.create_route(
            RouteTableId=route_table_id,
            DestinationCidrBlock='0.0.0.0/0',
            NatGatewayId=natgw_id
        )

        return {'route_table_id': route_table_id, 'natgw_id': natgw_id, 'success': True}

    except ClientError as e:
        return {'success': False, 'error': handle_vpc_error(e)}
```

### Associate Subnet with Route Table

```python
def associate_route_table(route_table_id: str, subnet_id: str) -> dict:
    """Associate subnet with route table."""
    try:
        response = ec2.associate_route_table(
            RouteTableId=route_table_id,
            SubnetId=subnet_id
        )

        return {
            'association_id': response['AssociationId'],
            'route_table_id': route_table_id,
            'subnet_id': subnet_id,
            'success': True
        }

    except ClientError as e:
        return {'success': False, 'error': handle_vpc_error(e)}
```

## Internet Gateway Operations

### Create and Attach Internet Gateway

```python
def create_internet_gateway(vpc_id: str, name: str = None) -> dict:
    """Create and attach Internet Gateway to VPC."""
    try:
        # Create IGW
        params = {}
        if name:
            params['TagSpecifications'] = [
                {
                    'ResourceType': 'internet-gateway',
                    'Tags': [{'Key': 'Name', 'Value': name}]
                }
            ]

        response = ec2.create_internet_gateway(**params)
        igw_id = response['InternetGateway']['InternetGatewayId']

        # Attach to VPC
        ec2.attach_internet_gateway(
            InternetGatewayId=igw_id,
            VpcId=vpc_id
        )

        return {
            'internet_gateway_id': igw_id,
            'vpc_id': vpc_id,
            'success': True
        }

    except ClientError as e:
        return {'success': False, 'error': handle_vpc_error(e)}
```

### Detach and Delete Internet Gateway

```python
def delete_internet_gateway(igw_id: str, vpc_id: str) -> dict:
    """Detach and delete Internet Gateway."""
    try:
        # Detach first
        ec2.detach_internet_gateway(
            InternetGatewayId=igw_id,
            VpcId=vpc_id
        )

        # Then delete
        ec2.delete_internet_gateway(InternetGatewayId=igw_id)

        return {
            'internet_gateway_id': igw_id,
            'success': True
        }

    except ClientError as e:
        return {'success': False, 'error': handle_vpc_error(e)}
```

## NAT Gateway Operations

### Create NAT Gateway

```python
def create_nat_gateway(subnet_id: str, name: str = None) -> dict:
    """Create NAT Gateway with Elastic IP."""
    try:
        # Allocate Elastic IP
        eip_response = ec2.allocate_address(Domain='vpc')
        allocation_id = eip_response['AllocationId']

        # Create NAT Gateway
        params = {
            'SubnetId': subnet_id,
            'AllocationId': allocation_id
        }

        if name:
            params['TagSpecifications'] = [
                {
                    'ResourceType': 'natgateway',
                    'Tags': [{'Key': 'Name', 'Value': name}]
                }
            ]

        response = ec2.create_nat_gateway(**params)
        natgw_id = response['NatGateway']['NatGatewayId']

        # Wait for NAT Gateway to be available
        waiter = ec2.get_waiter('nat_gateway_available')
        waiter.wait(NatGatewayIds=[natgw_id])

        return {
            'nat_gateway_id': natgw_id,
            'allocation_id': allocation_id,
            'public_ip': eip_response['PublicIp'],
            'success': True
        }

    except ClientError as e:
        return {'success': False, 'error': handle_vpc_error(e)}
```

### Delete NAT Gateway

```python
def delete_nat_gateway(natgw_id: str, allocation_id: str = None) -> dict:
    """Delete NAT Gateway and optionally release Elastic IP."""
    try:
        ec2.delete_nat_gateway(NatGatewayId=natgw_id)

        # Wait for deletion
        waiter = ec2.get_waiter('nat_gateway_deleted')
        waiter.wait(NatGatewayIds=[natgw_id])

        # Release Elastic IP if provided
        if allocation_id:
            ec2.release_address(AllocationId=allocation_id)

        return {
            'nat_gateway_id': natgw_id,
            'success': True
        }

    except ClientError as e:
        return {'success': False, 'error': handle_vpc_error(e)}
```

## VPC Peering Operations

### Create and Accept VPC Peering

```python
def create_vpc_peering(vpc_id: str, peer_vpc_id: str, peer_region: str = None) -> dict:
    """Create VPC Peering Connection."""
    try:
        params = {
            'VpcId': vpc_id,
            'PeerVpcId': peer_vpc_id
        }

        if peer_region:
            params['PeerRegion'] = peer_region

        response = ec2.create_vpc_peering_connection(**params)
        peer_conn_id = response['VpcPeeringConnection']['VpcPeeringConnectionId']

        return {
            'peering_connection_id': peer_conn_id,
            'status': response['VpcPeeringConnection']['Status']['Code'],
            'success': True
        }

    except ClientError as e:
        return {'success': False, 'error': handle_vpc_error(e)}

def accept_vpc_peering(peer_conn_id: str) -> dict:
    """Accept VPC Peering Connection request."""
    try:
        response = ec2.accept_vpc_peering_connection(
            VpcPeeringConnectionId=peer_conn_id
        )

        return {
            'peering_connection_id': peer_conn_id,
            'status': response['VpcPeeringConnection']['Status']['Code'],
            'success': True
        }

    except ClientError as e:
        return {'success': False, 'error': handle_vpc_error(e)}
```

## Complete VPC Setup Example

```python
def create_complete_vpc(vpc_cidr: str, vpc_name: str) -> dict:
    """Create complete VPC with public/private subnets, IGW, and NAT Gateway."""
    results = {}

    # 1. Create VPC
    vpc_result = create_vpc(vpc_cidr, vpc_name)
    if not vpc_result['success']:
        return vpc_result

    vpc_id = vpc_result['vpc_id']
    results['vpc'] = vpc_result

    # 2. Enable DNS
    enable_dns_attributes(vpc_id)

    # 3. Create Internet Gateway
    igw_result = create_internet_gateway(vpc_id, f"{vpc_name}-igw")
    if not igw_result['success']:
        return igw_result

    igw_id = igw_result['internet_gateway_id']
    results['internet_gateway'] = igw_result

    # 4. Create public subnet
    public_subnet_result = create_subnet(
        vpc_id,
        f"{vpc_cidr[:-5]}.1.0/24",  # e.g., 10.0.1.0/24
        f"{vpc_name}-public-1a",
        name=f"{vpc_name}-public"
    )
    if not public_subnet_result['success']:
        return public_subnet_result

    public_subnet_id = public_subnet_result['subnet_id']
    set_subnet_public(public_subnet_id)
    results['public_subnet'] = public_subnet_result

    # 5. Create route table for public subnet
    public_rt_result = create_route_table(vpc_id, f"{vpc_name}-public-rt")
    if not public_rt_result['success']:
        return public_rt_result

    public_rt_id = public_rt_result['route_table_id']
    create_route_to_igw(public_rt_id, igw_id)
    associate_route_table(public_rt_id, public_subnet_id)
    results['public_route_table'] = public_rt_result

    # 6. Create NAT Gateway
    natgw_result = create_nat_gateway(public_subnet_id, f"{vpc_name}-natgw")
    if not natgw_result['success']:
        return natgw_result

    natgw_id = natgw_result['nat_gateway_id']
    results['nat_gateway'] = natgw_result

    # 7. Create private subnet
    private_subnet_result = create_subnet(
        vpc_id,
        f"{vpc_cidr[:-5]}.2.0/24",  # e.g., 10.0.2.0/24
        f"{vpc_name}-private-1a",
        name=f"{vpc_name}-private"
    )
    if not private_subnet_result['success']:
        return private_subnet_result

    private_subnet_id = private_subnet_result['subnet_id']
    results['private_subnet'] = private_subnet_result

    # 8. Create route table for private subnet
    private_rt_result = create_route_table(vpc_id, f"{vpc_name}-private-rt")
    if not private_rt_result['success']:
        return private_rt_result

    private_rt_id = private_rt_result['route_table_id']
    create_route_to_natgw(private_rt_id, natgw_id)
    associate_route_table(private_rt_id, private_subnet_id)
    results['private_route_table'] = private_rt_result

    return {'success': True, 'vpc_id': vpc_id, 'components': results}
```

## Pagination Pattern

```python
def paginate_all_vpcs() -> list:
    """Get all VPCs across all pages."""
    paginator = ec2.get_paginator('describe_vpcs')
    all_vpcs = []

    for page in paginator.paginate():
        all_vpcs.extend(page['Vpcs'])

    return all_vpcs

def paginate_with_filter(filter_name: str, filter_values: list) -> list:
    """Paginate with specific filter."""
    paginator = ec2.get_paginator('describe_vpcs')

    pages = paginator.paginate(
        Filters=[{'Name': filter_name, 'Values': filter_values}]
    )

    results = []
    for page in pages:
        results.extend(page['Vpcs'])

    return results
```

## Common Error Codes

| Error Code | Description | Recovery |
|------------|-------------|----------|
| `InvalidVpcID.NotFound` | VPC ID does not exist | HALT |
| `VpcLimitExceeded` | VPC quota limit reached | HALT |
| `InvalidVpc.Range` | CIDR block invalid | HALT |
| `InvalidVpc.CidrBlock` | CIDR conflict | HALT |
| `ResourceDependencyViolation` | VPC has resources | HALT - cleanup |
| `InvalidSubnetID.NotFound` | Subnet does not exist | HALT |
| `InvalidSecurityGroupID.NotFound` | SG does not exist | HALT |
| `RequestLimitExceeded` | API throttling | RETRY with backoff |
| `InternalError` | AWS service error | RETRY 3x |