# AWS CLI Usage — EKS

## Common JSON Paths (Centralized)

```
# Create Cluster:        .cluster.{arn,name,status,endpoint,version}
# Describe Cluster:      .cluster.{status,endpoint,certificateAuthority,version,arn}
# List Clusters:         .clusters[]
# Create Nodegroup:      .nodegroup.{nodegroupArn,status}
# Describe Nodegroup:    .nodegroup.{status,scalingConfig,instanceTypes,nodegroupArn}
# List Nodegroups:       .nodegroups[]
# Create Fargate:        .fargateProfile.{fargateProfileArn,status}
# Describe Fargate:      .fargateProfile.{status,selectors}
# List Fargate:          .fargateProfileNames[]
# Create Addon:          .addon.{addonArn,status}
# Describe Addon:        .addon.{addonArn,status,addonVersion}
# List Addons:           .addons[]
# Describe Update:       .update.{id,status}
```

## Command Map

| Goal | CLI Command |
|------|-------------|
| Create cluster | `aws eks create-cluster` |
| Describe cluster | `aws eks describe-cluster` |
| List clusters | `aws eks list-clusters` |
| Delete cluster | `aws eks delete-cluster` |
| Update cluster version | `aws eks update-cluster-version` |
| Create nodegroup | `aws eks create-nodegroup` |
| Describe nodegroup | `aws eks describe-nodegroup` |
| Delete nodegroup | `aws eks delete-nodegroup` |
| Create Fargate profile | `aws eks create-fargate-profile` |
| Create addon | `aws eks create-addon` |
| Update kubeconfig | `aws eks update-kubeconfig` |
| Describe update | `aws eks describe-update` |

## Common Patterns

### Create EKS Cluster
```bash
aws eks create-cluster \
  --name my-cluster --version 1.30 \
  --role-arn arn:aws:iam::123456789012:role/eksClusterRole \
  --resources-vpc-config subnetIds=subnet-aaa,subnet-bbb,securityGroupIds=sg-xxx

# With logging
aws eks create-cluster --name my-cluster --version 1.30 \
  --role-arn arn:aws:iam::123456789012:role/eksClusterRole \
  --resources-vpc-config subnetIds=subnet-aaa,subnet-bbb,securityGroupIds=sg-xxx \
  --logging-config clusterLogging=[{types=api,audit,authenticator,controllerManager,scheduler},enabled=true]

# With encryption
aws eks create-cluster --name my-cluster --version 1.30 \
  --role-arn arn:aws:iam::123456789012:role/eksClusterRole \
  --resources-vpc-config subnetIds=subnet-aaa,subnet-bbb,securityGroupIds=sg-xxx \
  --encryption-config resources=[secretEnvelopes],provider=[keyArn=arn:aws:kms:region:account:key/key-id]
```

### Describe / List / Update Cluster
```bash
aws eks describe-cluster --name my-cluster
aws eks describe-cluster --name my-cluster --query 'cluster.endpoint'
aws eks describe-cluster --name my-cluster --query 'cluster.certificateAuthority.data'
aws eks list-clusters --max-items 10
aws eks update-cluster-version --name my-cluster --version 1.31
aws eks describe-update --name my-cluster --update-id {{update_id}}
aws eks update-cluster-config --name my-cluster \
  --logging-config clusterLogging=[{types=api,audit,enabled=true}]
```

### Create Node Group
```bash
aws eks create-nodegroup --cluster-name my-cluster --nodegroup-name my-nodegroup \
  --scaling-config minSize=2,maxSize=10,desiredSize=3 \
  --instance-types t3.medium --ami-type AL2_x86_64 \
  --node-role arn:aws:iam::123456789012:role/eksNodeRole \
  --subnets subnet-aaa,subnet-bbb

# With launch template
aws eks create-nodegroup --cluster-name my-cluster --nodegroup-name custom-nodegroup \
  --launch-template id=lt-xxx,version=1 \
  --node-role arn:aws:iam::123456789012:role/eksNodeRole \
  --subnets subnet-aaa,subnet-bbb --scaling-config minSize=1,maxSize=5,desiredSize=2
```

### Describe / Update / Delete Nodegroup
```bash
aws eks describe-nodegroup --cluster-name my-cluster --nodegroup-name my-nodegroup
aws eks list-nodegroups --cluster-name my-cluster
aws eks update-nodegroup-config --cluster-name my-cluster --nodegroup-name my-nodegroup \
  --scaling-config minSize=2,maxSize=10,desiredSize=5
aws eks update-nodegroup-version --cluster-name my-cluster --nodegroup-name my-nodegroup --version 1.30
aws eks delete-nodegroup --cluster-name my-cluster --nodegroup-name my-nodegroup
```

### Fargate Profile
```bash
aws eks create-fargate-profile --cluster-name my-cluster --fargate-profile-name my-profile \
  --pod-execution-role-arn arn:aws:iam::123456789012:role/eksFargateRole \
  --selectors namespace=default,labels=app=my-app --subnets subnet-aaa,subnet-bbb
aws eks describe-fargate-profile --cluster-name my-cluster --fargate-profile-name my-profile
aws eks list-fargate-profiles --cluster-name my-cluster
aws eks delete-fargate-profile --cluster-name my-cluster --fargate-profile-name my-profile
```

### Addons
```bash
aws eks create-addon --cluster-name my-cluster --addon-name vpc-cni \
  --addon-version v1.12.0-eksbuild.1 --resolve-conflicts OVERWRITE
aws eks list-addons --cluster-name my-cluster
aws eks describe-addon --cluster-name my-cluster --addon-name vpc-cni
aws eks update-addon --cluster-name my-cluster --addon-name vpc-cni \
  --addon-version v1.13.0-eksbuild.1 --resolve-conflicts OVERWRITE
aws eks delete-addon --cluster-name my-cluster --addon-name vpc-cni
```

### Update kubeconfig
```bash
aws eks update-kubeconfig --name my-cluster --region us-east-1
kubectl cluster-info
kubectl get nodes
```

### Delete Cluster (Complete Cleanup)
```bash
# 1. Delete Fargate profiles
aws eks list-fargate-profiles --cluster-name my-cluster
aws eks delete-fargate-profile --cluster-name my-cluster --fargate-profile-name profile1

# 2. Delete addons
aws eks list-addons --cluster-name my-cluster
aws eks delete-addon --cluster-name my-cluster --addon-name vpc-cni

# 3. Delete nodegroups
aws eks list-nodegroups --cluster-name my-cluster
aws eks delete-nodegroup --cluster-name my-cluster --nodegroup-name ng1

# 4. Delete cluster
aws eks delete-cluster --name my-cluster
```