# AWS CLI Usage for VPC Operations

All commands use `--output json`. See SKILL.md for JSON paths.

## VPC
```bash
aws ec2 create-vpc --cidr-block {{user.vpc_cidr}}
aws ec2 create-vpc --cidr-block {{cidr}} --tag-specifications "ResourceType=vpc,Tags=[{Key=Name,Value={{name}}}]"
aws ec2 describe-vpcs --vpc-ids {{id}}  # or --filters "Name=tag:Name,Values={{name}}"
aws ec2 modify-vpc-attribute --vpc-id {{id}} --enable-dns-support "{\"Value\":true}"
aws ec2 delete-vpc --vpc-id {{id}}  # all deps removed first
```

## Subnet
```bash
aws ec2 create-subnet --vpc-id {{id}} --cidr-block {{cidr}} [--availability-zone {{az}}]
aws ec2 describe-subnets --filters "Name=vpc-id,Values={{id}}"
aws ec2 modify-subnet-attribute --subnet-id {{id}} --map-public-ip-on-launch
aws ec2 modify-subnet-attribute --subnet-id {{id}} --no-map-public-ip-on-launch
aws ec2 delete-subnet --subnet-id {{id}}
```

## Security Group
```bash
aws ec2 create-security-group --group-name {{name}} --description "{{desc}}" --vpc-id {{id}}
aws ec2 describe-security-groups --filters "Name=vpc-id,Values={{id}}"
aws ec2 authorize-security-group-ingress --group-id {{id}} --protocol tcp --port 22 --cidr {{cidr}}
aws ec2 authorize-security-group-ingress --group-id {{id}} --protocol tcp --port 0-65535 --source-group {{src_id}}
aws ec2 authorize-security-group-egress --group-id {{id}} --ip-permissions '[{"IpProtocol":"-1","IpRanges":[{"CidrIp":"0.0.0.0/0"}]}]'
aws ec2 revoke-security-group-ingress --group-id {{id}} --protocol tcp --port 22 --cidr {{cidr}}
aws ec2 delete-security-group --group-id {{id}}
```

## Route Table
```bash
aws ec2 create-route-table --vpc-id {{id}}
aws ec2 describe-route-tables --filters "Name=vpc-id,Values={{id}}"
aws ec2 create-route --route-table-id {{rt}} --destination-cidr-block 0.0.0.0/0 --gateway-id {{igw}}  # public
aws ec2 create-route --route-table-id {{rt}} --destination-cidr-block 0.0.0.0/0 --nat-gateway-id {{nat}}  # private
aws ec2 create-route --route-table-id {{rt}} --destination-cidr-block {{peer_cidr}} --vpc-peering-connection-id {{pcx}}
aws ec2 associate-route-table --route-table-id {{rt}} --subnet-id {{sub}}
aws ec2 disassociate-route-table --association-id {{assoc}}
aws ec2 delete-route --route-table-id {{rt}} --destination-cidr-block 0.0.0.0/0
aws ec2 delete-route-table --route-table-id {{rt}}  # disassociate first
```

## Internet Gateway
```bash
aws ec2 create-internet-gateway
aws ec2 attach-internet-gateway --internet-gateway-id {{igw}} --vpc-id {{vpc}}
aws ec2 describe-internet-gateways --filters "Name=attachment.vpc-id,Values={{vpc}}"
aws ec2 detach-internet-gateway --internet-gateway-id {{igw}} --vpc-id {{vpc}}
aws ec2 delete-internet-gateway --internet-gateway-id {{igw}}  # detach first
```

## NAT Gateway
```bash
aws ec2 allocate-address --domain vpc  # → AllocationId
aws ec2 create-nat-gateway --subnet-id {{sub}} --allocation-id {{eip_alloc}}
aws ec2 describe-nat-gateways --nat-gateway-ids {{id}}
aws ec2 delete-nat-gateway --nat-gateway-id {{id}}  # then release-address
aws ec2 release-address --allocation-id {{eip_alloc}}
```

## VPC Peering
```bash
aws ec2 create-vpc-peering-connection --vpc-id {{vpc}} --peer-vpc-id {{peer}} [--peer-region {{region}}]
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