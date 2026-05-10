# AWS CLI Usage — EKS

## Command Map

| Goal | CLI Command | JSON Output Path |
|------|-------------|------------------|
| Create cluster | `aws eks create-cluster` | `.cluster.arn` |
| Describe cluster | `aws eks describe-cluster` | `.cluster` |
| List clusters | `aws eks list-clusters` | `.clusters[]` |
| Delete cluster | `aws eks delete-cluster` | Empty (success) |
| Update cluster version | `aws eks update-cluster-version` | `.update.id` |
| Create nodegroup | `aws eks create-nodegroup` | `.nodegroup.nodegroupArn` |
| Describe nodegroup | `aws eks describe-nodegroup` | `.nodegroup` |
| List nodegroups | `aws eks list-nodegroups` | `.nodegroups[]` |
| Delete nodegroup | `aws eks delete-nodegroup` | Empty (success) |
| Create Fargate profile | `aws eks create-fargate-profile` | `.fargateProfile.fargateProfileArn` |
| Describe Fargate profile | `aws eks describe-fargate-profile` | `.fargateProfile` |
| List Fargate profiles | `aws eks list-fargate-profiles` | `.fargateProfileNames[]` |
| Delete Fargate profile | `aws eks delete-fargate-profile` | Empty (success) |
| Update kubeconfig | `aws eks update-kubeconfig` | Path to kubeconfig file |
| List addons | `aws eks list-addons` | `.addons[]` |
| Create addon | `aws eks create-addon` | `.addon addonArn` |
| Describe addon | `aws eks describe-addon` | `.addon` |
| Delete addon | `aws eks delete-addon` | Empty (success) |
| List updates | `aws eks list-updates` | `.updates[]` |
| Describe update | `aws eks describe-update` | `.update.status` |

## Key CLI Conventions

### Regional Service
EKS is **regional** — region parameter required.

### Output Format
Always use `--output json` for agent parsing.

### Cluster Status Values
- `CREATING` — Cluster being created
- `ACTIVE` — Cluster ready for use
- `UPDATING` — Cluster being updated
- `DELETING` — Cluster being deleted
- `FAILED` — Creation or update failed

## Common Patterns

### Create EKS Cluster

```bash
aws eks create-cluster \
  --name my-cluster \
  --version 1.30 \
  --role-arn arn:aws:iam::123456789012:role/eksClusterRole \
  --resources-vpc-config subnetIds=subnet-aaa,subnet-bbb,securityGroupIds=sg-xxx \
  --kubernetes-networking-config serviceIpV4Cidr=10.100.0.0/16 \
  --output json
```

### Create Cluster with Logging Enabled

```bash
aws eks create-cluster \
  --name my-cluster \
  --version 1.30 \
  --role-arn arn:aws:iam::123456789012:role/eksClusterRole \
  --resources-vpc-config subnetIds=subnet-aaa,subnet-bbb,securityGroupIds=sg-xxx \
  --logging-config clusterLogging=[{types=api,audit,authenticator,controllerManager,scheduler},enabled=true] \
  --output json
```

### Create Cluster with Encryption

```bash
aws eks create-cluster \
  --name my-cluster \
  --version 1.30 \
  --role-arn arn:aws:iam::123456789012:role/eksClusterRole \
  --resources-vpc-config subnetIds=subnet-aaa,subnet-bbb,securityGroupIds=sg-xxx \
  --encryption-config resources=[secretEnvelopes],provider=[keyArn=arn:aws:kms:region:account:key/key-id] \
  --output json
```

### Describe Cluster

```bash
aws eks describe-cluster \
  --name my-cluster \
  --output json

# Get cluster endpoint
aws eks describe-cluster --name my-cluster --output json --query 'cluster.endpoint'

# Get certificate authority
aws eks describe-cluster --name my-cluster --output json --query 'cluster.certificateAuthority.data'
```

### List Clusters

```bash
aws eks list-clusters --output json

# Pagination
aws eks list-clusters --max-items 10 --output json
```

### Update Cluster Version

```bash
aws eks update-cluster-version \
  --name my-cluster \
  --version 1.31 \
  --output json

# Check update status
aws eks describe-update \
  --name my-cluster \
  --update-id {{update_id}} \
  --output json
```

### Update Cluster Configuration

```bash
# Enable logging
aws eks update-cluster-config \
  --name my-cluster \
  --logging-config clusterLogging=[{types=api,audit,enabled=true}] \
  --output json

# Update VPC config
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config securityGroupIds=sg-new \
  --output json
```

### Create Managed Node Group

```bash
aws eks create-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --scaling-config minSize=2,maxSize=10,desiredSize=3 \
  --instance-types t3.medium \
  --ami-type AL2_x86_64 \
  --node-role arn:aws:iam::123456789012:role/eksNodeRole \
  --subnets subnet-aaa,subnet-bbb \
  --labels env=prod \
  --tags Key=Environment,Value=Production \
  --output json
```

### Create Node Group with Launch Template

```bash
aws eks create-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name custom-nodegroup \
  --launch-template id=lt-xxx,version=1 \
  --node-role arn:aws:iam::123456789012:role/eksNodeRole \
  --subnets subnet-aaa,subnet-bbb \
  --scaling-config minSize=1,maxSize=5,desiredSize=2 \
  --output json
```

### Describe Node Group

```bash
aws eks describe-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --output json

# Get nodegroup status
aws eks describe-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --output json --query 'nodegroup.status'
```

### List Node Groups

```bash
aws eks list-nodegroups \
  --cluster-name my-cluster \
  --output json
```

### Update Node Group Config

```bash
aws eks update-nodegroup-config \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --scaling-config minSize=2,maxSize=10,desiredSize=5 \
  --labels add=app=web \
  --output json
```

### Update Node Group Version

```bash
aws eks update-nodegroup-version \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --version 1.30 \
  --launch-template-version 2 \
  --output json
```

### Delete Node Group

```bash
# Safety Gate: Confirm with user before deletion
aws eks delete-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --output json
```

### Create Fargate Profile

```bash
aws eks create-fargate-profile \
  --cluster-name my-cluster \
  --fargate-profile-name my-profile \
  --pod-execution-role-arn arn:aws:iam::123456789012:role/eksFargateRole \
  --selectors namespace=default,labels=app=my-app \
  --subnets subnet-aaa,subnet-bbb \
  --output json
```

### Describe Fargate Profile

```bash
aws eks describe-fargate-profile \
  --cluster-name my-cluster \
  --fargate-profile-name my-profile \
  --output json
```

### List Fargate Profiles

```bash
aws eks list-fargate-profiles \
  --cluster-name my-cluster \
  --output json
```

### Delete Fargate Profile

```bash
aws eks delete-fargate-profile \
  --cluster-name my-cluster \
  --fargate-profile-name my-profile \
  --output json
```

### Create Addon

```bash
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --addon-version v1.12.0-eksbuild.1 \
  --service-account-role-arn arn:aws:iam::123456789012:role/eksVPCCniRole \
  --resolve-conflicts OVERWRITE \
  --output json
```

### List Addons

```bash
aws eks list-addons \
  --cluster-name my-cluster \
  --output json
```

### Describe Addon

```bash
aws eks describe-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --output json
```

### Update Addon

```bash
aws eks update-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --addon-version v1.13.0-eksbuild.1 \
  --resolve-conflicts OVERWRITE \
  --output json
```

### Delete Addon

```bash
aws eks delete-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --output json
```

### Update kubeconfig

```bash
aws eks update-kubeconfig \
  --name my-cluster \
  --region us-east-1 \
  --role-arn arn:aws:iam::123456789012:role/eksAdminRole

# Verify kubeconfig
kubectl cluster-info
kubectl get nodes
```

### Delete Cluster (Complete Cleanup)

```bash
# 1. Delete all Fargate profiles
aws eks list-fargate-profiles --cluster-name my-cluster --output json
aws eks delete-fargate-profile --cluster-name my-cluster --fargate-profile-name profile1 --output json

# 2. Delete all nodegroups
aws eks list-nodegroups --cluster-name my-cluster --output json
aws eks delete-nodegroup --cluster-name my-cluster --nodegroup-name ng1 --output json

# 3. Delete all addons
aws eks list-addons --cluster-name my-cluster --output json
aws eks delete-addon --cluster-name my-cluster --addon-name vpc-cni --output json

# 4. Wait for all deletions (poll until complete)

# 5. Safety Gate: Confirm with user before deletion
aws eks delete-cluster --name my-cluster --output json
```

## ARN Format

| Resource | ARN Pattern |
|----------|-------------|
| Cluster | `arn:aws:eks:region:account:cluster/name` |
| Node Group | `arn:aws:eks:region:account:nodegroup/cluster-name/nodegroup-name/uuid` |
| Fargate Profile | `arn:aws:eks:region:account:fargateprofile/cluster-name/profile-name/uuid` |
| Addon | `arn:aws:eks:region:account:addon/cluster-name/addon-name/uuid` |

## AMI Types

| AMI Type | Description |
|----------|-------------|
| AL2_x86_64 | Amazon Linux 2 (x86_64) |
| AL2_x86_64_GPU | Amazon Linux 2 with GPU |
| AL2_ARM_64 | Amazon Linux 2 (ARM64) |
| CUSTOM | Custom launch template |

## Status Values

| Resource | Status Values |
|----------|---------------|
| Cluster | CREATING, ACTIVE, UPDATING, DELETING, FAILED |
| Nodegroup | CREATING, ACTIVE, UPDATING, DELETING, CREATE_FAILED, DELETE_FAILED, DEGRADED |
| Fargate Profile | CREATING, ACTIVE, DELETING, CREATE_FAILED, DELETE_FAILED |
| Addon | CREATING, ACTIVE, UPDATING, DELETING, CREATE_FAILED, DELETE_FAILED, DEGRADED |

## Credential Handling

CLI reads credentials in priority order:
1. Environment: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
2. Config file: `~/.aws/credentials`
3. IAM role (EC2/Lambda)

Verify:
```bash
aws sts get-caller-identity --output json
```

## kubectl Integration

After cluster creation:
```bash
# Update kubeconfig
aws eks update-kubeconfig --name my-cluster --region us-east-1

# Test connectivity
kubectl cluster-info
kubectl get nodes
kubectl get pods -A
```