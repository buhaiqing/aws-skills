# AWS CLI Usage for VPC Operations

All commands use `--output json`.

## Common JSON Paths (Centralized)
```
# Create:    .Vpc.{VpcId,CidrBlock,State}  /  .Subnet.{SubnetId,CidrBlock,VpcId,State}  /  .GroupId
#            .RouteTable.RouteTableId  /  .InternetGateway.InternetGatewayId  /  .NatGateway.{NatGatewayId,State}
#            .VpcPeeringConnection.{VpcPeeringConnectionId,Status.Code}
# Describe:  .Vpcs[].{VpcId,CidrBlock,State,Tags}  /  .Subnets[]  /  .SecurityGroups[].{GroupId,GroupName,IpPermissions}
#            .RouteTables[].{RouteTableId,Routes,Associations}  /  .NatGateways[].{NatGatewayId,State,SubnetId}
#            .InternetGateways[].{InternetGatewayId,Attachments}  /  .VpcPeeringConnections[].{VpcPeeringConnectionId,Status}
```

## VPC Operations
```bash
aws ec2 create-vpc --cidr-block {{user.vpc_cidr}}
aws ec2 create-vpc --cidr-block {{user.vpc_cidr}} --tag-specifications "ResourceType=vpc,Tags=[{Key=Name,Value={{user.vpc_name}}}]"
aws ec2 describe-vpcs --vpc-ids {{user.vpc_id}}
aws ec2 describe-vpcs --filters "Name=tag:Name,Values={{user.vpc_name}}"
aws ec2 modify-vpc-attribute --vpc-id {{user.vpc_id}} --enable-dns-support "{\"Value\":true}"
aws ec2 delete-vpc --vpc-id {{user.vpc_id}}  # Requires all deps removed
```

## Subnet Operations
```bash
aws ec2 create-subnet --vpc-id {{user.vpc_id}} --cidr-block {{user.subnet_cidr}}
aws ec2 create-subnet --vpc-id {{id}} --cidr-block {{cidr}} --availability-zone {{az}}
aws ec2 describe-subnets --filters "Name=vpc-id,Values={{user.vpc_id}}"
aws ec2 modify-subnet-attribute --subnet-id {{id}} --map-public-ip-on-launch  # Set public
aws ec2 modify-subnet-attribute --subnet-id {{id}} --no-map-public-ip-on-launch  # Set private
aws ec2 delete-subnet --subnet-id {{user.subnet_id}}
```

## Security Group Operations
```bash
aws ec2 create-security-group --group-name {{name}} --description "{{desc}}" --vpc-id {{id}}
aws ec2 describe-security-groups --filters "Name=vpc-id,Values={{user.vpc_id}}"
aws ec2 authorize-security-group-ingress --group-id {{id}} --protocol tcp --port 22 --cidr {{cidr}}
aws ec2 authorize-security-group-ingress --group-id {{id}} --protocol tcp --port 0-65535 --source-group {{src_id}}
aws ec2 authorize-security-group-egress --group-id {{id}} --ip-permissions '[{"IpProtocol":"-1","IpRanges":[{"CidrIp":"0.0.0.0/0"}]}]'
aws ec2 revoke-security-group-ingress --group-id {{id}} --protocol tcp --port 22 --cidr {{cidr}}
aws ec2 delete-security-group --group-id {{user.sg_id}}
```

## Route Table Operations
```bash
aws ec2 create-route-table --vpc-id {{user.vpc_id}}
aws ec2 describe-route-tables --filters "Name=vpc-id,Values={{user.vpc_id}}"
aws ec2 create-route --route-table-id {{rt}} --destination-cidr-block 0.0.0.0/0 --gateway-id {{igw}}  # Public subnet
aws ec2 create-route --route-table-id {{rt}} --destination-cidr-block 0.0.0.0/0 --nat-gateway-id {{nat}}  # Private subnet
aws ec2 create-route --route-table-id {{rt}} --destination-cidr-block {{peer_cidr}} --vpc-peering-connection-id {{pcx}}
aws ec2 associate-route-table --route-table-id {{rt}} --subnet-id {{subnet}}
aws ec2 disassociate-route-table --association-id {{assoc}}
aws ec2 delete-route --route-table-id {{rt}} --destination-cidr-block 0.0.0.0/0
aws ec2 delete-route-table --route-table-id {{rt}}  # Must disassociate first
```

## Internet Gateway Operations
```bash
aws ec2 create-internet-gateway
aws ec2 attach-internet-gateway --internet-gateway-id {{igw}} --vpc-id {{vpc}}
aws ec2 describe-internet-gateways --filters "Name=attachment.vpc-id,Values={{vpc}}"
aws ec2 detach-internet-gateway --internet-gateway-id {{igw}} --vpc-id {{vpc}}
aws ec2 delete-internet-gateway --internet-gateway-id {{igw}}  # Must detach first
```

## NAT Gateway Operations
```bash
aws ec2 allocate-address --domain vpc  # Get AllocationId + PublicIp
aws ec2 create-nat-gateway --subnet-id {{subnet}} --allocation-id {{eip_alloc}}
aws ec2 describe-nat-gateways --nat-gateway-ids {{natgw}}
aws ec2 delete-nat-gateway --nat-gateway-id {{natgw}}  # Then release EIP
aws ec2 release-address --allocation-id {{eip_alloc}}
```

## VPC Peering Operations
```bash
# Same region
aws ec2 create-vpc-peering-connection --vpc-id {{vpc}} --peer-vpc-id {{peer}}
# Cross-region
aws ec2 create-vpc-peering-connection --vpc-id {{vpc}} --peer-vpc-id {{peer}} --peer-region {{region}}
aws ec2 accept-vpc-peering-connection --vpc-peering-connection-id {{pcx}}
aws ec2 describe-vpc-peering-connections --vpc-peering-connection-ids {{pcx}}
aws ec2 reject-vpc-peering-connection --vpc-peering-connection-id {{pcx}}
aws ec2 delete-vpc-peering-connection --vpc-peering-connection-id {{pcx}}
```

## Waiters
```bash
aws ec2 wait vpc-available --vpc-ids {{id}}
aws ec2 wait subnet-available --subnet-ids {{id}}
aws ec2 wait nat-gateway-available --nat-gateway-ids {{id}}
aws ec2 wait nat-gateway-deleted --nat-gateway-ids {{id}}
```

## Common Option Flags
```
--cidr-block: CIDR notation (RFC 1918: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
--protocol: tcp/udp/icmp/-1 | --port: port number or range (e.g., 22, 80-443)
--tag-specifications: "ResourceType={type},Tags=[{Key={k},Value={v}}]"
```