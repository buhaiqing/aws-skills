# Integration Guide — RAM: Organizations, IAM, and Cross-Account Sharing

_Latest update: 2026-06-27_

This document covers how to integrate AWS RAM with its key dependencies:
AWS Organizations (org sharing), IAM (consumer-side permissions), and the
consuming services (VPC, RDS, Aurora) that RAM enables.

---

## 1. AWS Organizations Integration

### Enable RAM Sharing via Organizations

RAM can share resources with all accounts in an organization without individual
invitations. This is the recommended approach for internal org sharing.

```bash
# Enable org sharing (must be run by management account or delegated admin)
aws ram enable-sharing-with-aws-organization --region {{user.region}}

# Verify
aws organizations describe-organization
```

### Sharing with an OU

```bash
aws ram create-resource-share \
  --name "shared-vpc-for-app-team" \
  --resource-arns "arn:aws:ec2:{{user.region}}:111111111111:subnet/subnet-aaa" \
  --principals "arn:aws:organizations::111111111111:ou/o-xxxx/ou-yyyy" \
  --allow-external-principals false \
  --region {{user.region}} \
  --output json
```

### Organizations Quotas for RAM

| Quota | Default | Adjustable? |
|-------|---------|-------------|
| Organizational units per org | 1,000 | No |
| Accounts per OU | 1,000 | No |
| RAM resource shares | 1,000 | No |

---

## 2. Cross-Account Invitation Flow

### Owner Side (Producer Account)

```bash
# 1. Create resource share (without auto-accept)
aws ram create-resource-share \
  --name "app-team-access" \
  --resource-arns "arn:aws:ec2:{{user.region}}:111111111111:subnet/subnet-aaa" \
  --principals "222222222222" \
  --region {{user.region}} \
  --output json

# 2. List pending invitations to see invitation ARN
aws ram get-resource-share-invitations --region {{user.region}} --output json

# 3. Monitor status
aws ram get-resource-share-associations \
  --association-type PRINCIPAL \
  --resource-share-arns "arn:aws:ram:{{user.region}}:111111111111:resource-share/xxxx" \
  --region {{user.region}} --output json
```

### Consumer Side (App Account)

```bash
# 1. List pending invitations
aws ram get-resource-share-invitations --region {{user.region}} --output json

# 2. Accept invitation
aws ram accept-resource-share-invitation \
  --resource-share-invitation-arn "arn:aws:ram:{{user.region}}:222222222222:resource-share-invitation/invitation-xxxx" \
  --region {{user.region}} \
  --output json

# 3. Verify shared resources are visible
aws ec2 describe-vpcs --region {{user.region}} --output json | jq '.Vpcs[].VpcId'
aws ram list-resources --resource-owner SELF --region {{user.region}} --output json
```

### Reject / Accept Trade-offs

| Action | Effect | Use When |
|--------|--------|----------|
| Accept | Consumer gains access to shared resources | Intentional onboarding |
| Reject | Consumer refuses the share | Resource not needed |
| Pending | No action yet | Review in progress |

---

## 3. IAM Integration (Consumer-Side)

RAM grants **resource visibility** — consumers can see shared resources, but still
need IAM permissions to operate on them. See `aws-iam-ops` for IAM management.

### Common Consumer IAM Policies

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
        "ec2:DescribeSecurityGroups"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "rds:DescribeDBClusters"
      ],
      "Resource": "arn:aws:rds:{{user.region}}:111111111111:cluster:*"
    }
  ]
}
```

### RAM Permission Types

| Permission | Description | Use Case |
|------------|-------------|----------|
| `AWSRAMPermissionAssociatingResources` | Allow associating resources to share | Owner attaching resources |
| `AWSRAMPermissionCreatingResourceShare` | Allow creating shares | Owner creating shares |
| `AWSRAMPermissionEnableSharingWithAwsOrganization` | Enable org sharing | Management account only |

---

## 4. VPC Subnet Sharing (VPC Integration)

RAM shares VPC subnets for multi-account architectures. Consumer accounts can
launch EC2 instances in shared subnets.

### Pre-flight: Verify Subnet Sharing

```bash
# Owner: verify subnet ARN
aws ec2 describe-subnets \
  --subnet-ids subnet-aaa \
  --query 'Subnets[0].SubnetArn' \
  --region {{user.region}} \
  --output json

# Owner: verify share is ACTIVE
aws ram get-resource-share-associations \
  --association-type PRINCIPAL \
  --resource-share-arns "arn:aws:ram:{{user.region}}:111111111111:resource-share/xxxx" \
  --region {{user.region}} --output json

# Consumer: verify subnet is visible
aws ec2 describe-subnets \
  --filters "Name=tag:awsm résourced.resourcel.owner,Values=111111111111" \
  --region {{user.region}} \
  --output json
```

### Cross-Service Flow: Shared Subnet for EC2

```
1. Network account: ram create-resource-share (subnets + principals)
2. App account: ram accept-resource-share-invitation
3. App account: verify subnet visible via ec2 describe-subnets
4. App account: create IAM role with ec2:RunInstances permission
5. App account: launch EC2 in shared subnet via aws-ec2-ops
```

---

## 5. RDS / Aurora Sharing

RAM can share RDS DB Subnet Groups and Aurora clusters for cross-account
database access.

### Share RDS Subnet Group

```bash
# Network/DB account
aws ram create-resource-share \
  --name "shared-db-subnet-group" \
  --resource-arns "arn:aws:rds:{{user.region}}:111111111111:subgrp:default-prod-db" \
  --principals "222222222222" \
  --region {{user.region}} \
  --output json

# App account
aws ram accept-resource-share-invitation \
  --resource-share-invitation-arn "arn:aws:ram:{{user.region}}:222222222222:resource-share-invitation/invitation-xxxx"

# Verify DB subnet group visible
aws rds describe-db-subnet-groups \
  --db-subnet-group-name default-prod-db \
  --region {{user.region}} --output json
```

---

## 6. RAM + CloudTrail Audit Trail

Track who shared what and when for compliance.

```bash
# Find RAM API events around anomaly time
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventSource,AttributeValue=ram.amazonaws.com \
  --start-time "2026-06-27T00:00:00Z" \
  --end-time "2026-06-27T12:00:00Z" \
  --region {{user.region}} \
  --output json | jq '.Events[] | {EventName, Username, EventTime}'
```

### Key RAM Events for Audit

| EventName | Meaning |
|-----------|---------|
| `CreateResourceShare` | New share created |
| `UpdateResourceShare` | Share modified |
| `DeleteResourceShare` | Share deleted |
| `EnableSharingWithAwsOrganization` | Org sharing enabled |
| `AcceptResourceShareInvitation` | Consumer accepted invitation |
| `RejectResourceShareInvitation` | Consumer rejected invitation |
| `AssociateResourceShare` | Resources/principals added |
| `DisassociateResourceShare` | Resources/principals removed |

---

## 7. Troubleshooting Integration

### Share Not Visible to Consumer

```
Check order:
1. ram get-resource-share-invitations (consumer side) — invitation PENDING?
2. ram accept-resource-share-invitation (consumer side) — accepted?
3. ram get-resource-share-associations (owner side) — status ACTIVE?
4. aws organizations describe-organization — org sharing enabled?
```

### Resource Type Not Shareable

```bash
# Check if resource type supports sharing
aws ram list-resource-types --region {{user.region}} --output json | \
  jq '.resourceTypes[] | select(.resourceType == "{{user.resource_type}}")'

# Check specific resource's shareability
aws ram get-resource-share-associations \
  --resource-arns "arn:aws:ec2:{{user.region}}:111111111111:subnet/subnet-aaa" \
  --region {{user.region}} --output json
```

### Permission Denied on Shared Resource

```
1. Verify RAM association is ACTIVE (ram get-resource-share-associations)
2. Verify consumer has IAM permission (aws-iam-ops)
3. For Aurora: verify cluster is shared AND IAM role allows access
4. Check resource ARN matches exactly (no typos in account ID)
```
