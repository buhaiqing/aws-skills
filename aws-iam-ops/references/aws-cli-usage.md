# AWS CLI Usage — IAM

## Command Map

| Goal | CLI Command | JSON Output Path |
|------|-------------|------------------|
| Create user | `aws iam create-user` | `.User.Arn` |
| Get user | `aws iam get-user` | `.User` |
| List users | `aws iam list-users` | `.Users[]` |
| Delete user | `aws iam delete-user` | Empty (success) |
| Create role | `aws iam create-role` | `.Role.Arn` |
| Get role | `aws iam get-role` | `.Role` |
| List roles | `aws iam list-roles` | `.Roles[]` |
| Delete role | `aws iam delete-role` | Empty (success) |
| Create group | `aws iam create-group` | `.Group.Arn` |
| List groups | `aws iam list-groups` | `.Groups[]` |
| Create policy | `aws iam create-policy` | `.Policy.Arn` |
| List policies | `aws iam list-policies` | `.Policies[]` |
| Attach role policy | `aws iam attach-role-policy` | Empty (success) |
| Attach user policy | `aws iam attach-user-policy` | Empty (success) |
| Create access key | `aws iam create-access-key` | `.AccessKey` |
| Delete access key | `aws iam delete-access-key` | Empty (success) |

## Key CLI Conventions

### Global Service
IAM is a **global service** — region parameter usually ignored except for STS operations.

### Output Format
Always use `--output json` for agent parsing.

### Policy Documents
Use `file://` to load JSON policy files:
```bash
aws iam create-policy --policy-name MyPolicy --policy-document file://policy.json --output json
aws iam create-role --role-name MyRole --assume-role-policy-document file://trust-policy.json --output json
```

### Path Convention
Paths organize IAM entities hierarchically:
- Default path: `/`
- Custom path: `/department/engineers/`

## Common Patterns

### Create User
```bash
aws iam create-user --user-name john --path /developers/ --output json
```

### Create Role with Trust Policy
```bash
# Trust policy file (trust-policy.json)
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "ec2.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }
  ]
}

aws iam create-role \
  --role-name EC2-SSM-Role \
  --assume-role-policy-document file://trust-policy.json \
  --output json
```

### Attach Managed Policy to Role
```bash
# Attach AWS managed policy
aws iam attach-role-policy \
  --role-name EC2-SSM-Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore \
  --output json
```

### Create Custom Policy
```bash
# Policy file (policy.json)
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": ["arn:aws:s3:::my-bucket", "arn:aws:s3:::my-bucket/*"]
    }
  ]
}

aws iam create-policy \
  --policy-name S3-Read-Only \
  --policy-document file://policy.json \
  --output json
```

### Create Access Key for User
```bash
aws iam create-access-key --user-name john --output json
# IMPORTANT: SecretAccessKey visible only once — user must save immediately
```

### Add User to Group
```bash
aws iam add-user-to-group --user-name john --group-name developers --output json
```

### Create Group and Attach Policy
```bash
aws iam create-group --group-name s3-admins --output json
aws iam attach-group-policy --group-name s3-admins --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess --output json
```

### Delete User (Complete Cleanup)
```bash
# List and detach policies
aws iam list-attached-user-policies --user-name john --output json

# Detach each policy
aws iam detach-user-policy --user-name john --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

# Delete access keys
aws iam list-access-keys --user-name john --output json
aws iam delete-access-key --user-name john --access-key-id AKIA...

# Remove from groups
aws iam list-groups-for-user --user-name john --output json
aws iam remove-user-from-group --user-name john --group-name developers

# Delete user
aws iam delete-user --user-name john
```

### List All Policies (AWS Managed)
```bash
aws iam list-policies --scope AWS --output json
```

### List All Policies (Customer Managed)
```bash
aws iam list-policies --scope Local --output json
```

## CLI vs API Coverage Gap

| Operation (API) | CLI Available | Notes |
|-----------------|---------------|-------|
| CreateUser | ✅ | `create-user` |
| GetUser | ✅ | `get-user` |
| ListUsers | ✅ | `list-users` |
| DeleteUser | ✅ | `delete-user` |
| CreateRole | ✅ | `create-role` |
| GetRole | ✅ | `get-role` |
| ListRoles | ✅ | `list-roles` |
| DeleteRole | ✅ | `delete-role` |
| CreateGroup | ✅ | `create-group` |
| AddUserToGroup | ✅ | `add-user-to-group` |
| CreatePolicy | ✅ | `create-policy` |
| AttachRolePolicy | ✅ | `attach-role-policy` |
| AttachUserPolicy | ✅ | `attach-user-policy` |
| CreateAccessKey | ✅ | `create-access-key` |
| DeleteAccessKey | ✅ | `delete-access-key` |
| PutRolePolicy (inline) | ✅ | `put-role-policy` |
| GetPolicyDocument | ✅ | `get-policy-version` |

## AWS Managed Policy ARNs (Common)

| Policy | ARN |
|--------|-----|
| AdministratorAccess | `arn:aws:iam::aws:policy/AdministratorAccess` |
| PowerUserAccess | `arn:aws:iam::aws:policy/PowerUserAccess` |
| ReadOnlyAccess | `arn:aws:iam::aws:policy/ReadOnlyAccess` |
| AmazonS3FullAccess | `arn:aws:iam::aws:policy/AmazonS3FullAccess` |
| AmazonS3ReadOnlyAccess | `arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess` |
| AmazonEC2FullAccess | `arn:aws:iam::aws:policy/AmazonEC2FullAccess` |
| AmazonRDSFullAccess | `arn:aws:iam::aws:policy/AmazonRDSFullAccess` |

## Credential Handling

CLI reads credentials in priority order:
1. Environment: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
2. Config file: `~/.aws/credentials`
3. IAM role (EC2/Lambda)

Verify:
```bash
aws sts get-caller-identity --output json
```