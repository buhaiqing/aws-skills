# Troubleshooting — EKS

## Common Error Codes

| Error Code | HTTP | Meaning | Agent Action |
|------------|------|---------|--------------|
| ResourceInUseException | 400 | Cluster/nodegroup name exists | HALT; use different name |
| ResourceLimitExceededException | 400 | EKS quota reached | HALT; request quota increase |
| InvalidParameterException | 400 | Parameter value invalid | Fix parameter; retry once |
| ResourceNotFoundException | 404 | Cluster/nodegroup not found | HALT; verify name |
| AccessDeniedException | 403 | IAM permissions missing | HALT; check role permissions |
| ClientException | 400 | Configuration error | Fix config; retry once |
| ServiceUnavailableException | 500 | EKS service issue | Retry 3x; HALT if persists |
| ThrottlingException | 429 | Too many requests | Backoff; retry 3x |
| UnsupportedAvailabilityZoneException | 400 | AZ not supported for EKS | Use different AZ |

## Diagnostic Order

1. **Verify credentials**: `aws sts get-caller-identity`
2. **Verify cluster exists**: `aws eks describe-cluster --name {{cluster_name}}`
3. **Verify VPC**: `aws ec2 describe-vpcs --vpc-ids {{vpc_id}}`
4. **Verify subnets**: `aws ec2 describe-subnets --subnet-ids {{subnet_ids}}`
5. **Verify IAM roles**: `aws iam get-role --role-name {{role_name}}`
6. **Check nodegroup health**: `aws eks describe-nodegroup`
7. **Check addon status**: `aws eks describe-addon`
8. **Check update status**: `aws eks describe-update`

## Common Issues

### ResourceInUseException

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Cluster creation fails | Cluster name exists | Use different name (unique per region) |
| Nodegroup creation fails | Nodegroup name exists | Use different name per cluster |

### ResourceLimitExceededException

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Cannot create cluster | 100 clusters reached | Delete unused clusters or request increase |
| Cannot create nodegroup | 30 nodegroups per cluster | Delete unused nodegroups |

### InvalidParameterException

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Invalid subnet | Subnet not in same VPC | Use subnets from same VPC |
| Invalid version | Kubernetes version not supported | Use supported version (1.27-1.31) |
| Invalid role ARN | Role not found or wrong format | Verify role exists and ARN format |
| Invalid CIDR | Service CIDR overlaps VPC | Use non-overlapping CIDR |

### ResourceNotFoundException

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Cluster not found | Wrong name or region | Verify cluster name and region |
| Nodegroup not found | Wrong nodegroup name | Verify nodegroup exists for cluster |
| Addon not found | Addon not installed | Install addon first |
| Fargate profile not found | Profile not exists | Verify profile name |

### AccessDeniedException

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Cannot create cluster | Role lacks eks:* | Add EKS permissions to IAM role |
| Cannot create nodegroup | Node role lacks permissions | Add EC2/SSM permissions |
| kubectl access denied | IAM not mapped in cluster | Update aws-auth ConfigMap or use access entry |
| Addon failed | Addon role lacks permissions | Add required permissions to addon role |

### Node Group Health Issues

| Health Issue Code | Cause | Resolution |
|--------------------|-------|------------|
| NodeCreationFailure | EC2 quota or AMI issue | Check EC2 quotas, verify AMI |
| AsgInstanceLaunchFailed | Auto Scaling Group issue | Check ASG capacity |
| InstanceLimitExceeded | EC2 instance limit | Request EC2 quota increase |
| InternalError | Unknown EKS error | Contact AWS support |
| ClusterUnreachable | Node cannot reach API | Check network/SG rules |

### Cluster Status Issues

| Status | Cause | Resolution |
|--------|-------|------------|
| FAILED | Creation failed | Check error message, recreate |
| UPDATING (stuck) | Update timeout | Check update status, retry |
| DEGRADED | Control plane unhealthy | Check CloudWatch logs |

### Fargate Profile Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Pods not on Fargate | Selector mismatch | Verify namespace and labels match |
| Profile creation fails | IAM role missing | Create pod execution role first |
| Profile deletion stuck | Pods running | Delete pods first |

### Addon Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Addon CREATE_FAILED | Role permissions missing | Add required permissions |
| Addon DEGRADED | Configuration conflict | Update addon config |
| Addon version mismatch | Cluster upgrade needed | Update addon version |

### Update Issues

| Update Status | Cause | Resolution |
|---------------|-------|------------|
| InProgress (stuck) | Large cluster, slow update | Wait longer (check progress) |
| Failed | Prerequisite not met | Check error, fix issue |
| Cancelled | Manual cancellation | Retry update |

### kubectl Connection Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Connection refused | Wrong endpoint | Update kubeconfig with correct endpoint |
| Certificate error | Wrong cluster | Regenerate kubeconfig |
| Unauthorized | IAM not mapped | Add IAM user/role to aws-auth |
| Timeout | Private endpoint only | Connect from VPC or VPN |

## Permissions Required

### Cluster IAM Role
| Permission | Purpose |
|------------|---------|
| ec2:Describe* | Describe VPC resources |
| ec2:CreateNetworkInterface | Create ENI for control plane |
| ec2:DeleteNetworkInterface | Delete ENI |
| iam:CreateServiceLinkedRole | Create AWSServiceRoleForAmazonEKS |
| logs:CreateLogGroup | CloudWatch Logs |

### Node IAM Role
| Permission | Purpose |
|------------|---------|
| ec2:Describe* | Describe instances |
| ecr:GetAuthorizationToken | Pull images from ECR |
| ecr:BatchCheckLayerAvailability | Check image layers |
| ecr:GetRepositoryPolicy | Get repository policy |
| ecr:DescribeRepositories | Describe repositories |
| ecr:GetDownloadUrlForLayer | Download image layers |
| ecr:BatchGetImage | Get images |
| eks:DescribeCluster | Describe cluster |
| logs:CreateLogStream | CloudWatch Logs |
| logs:PutLogEvents | Send logs |

### Fargate Pod Execution Role
| Permission | Purpose |
|------------|---------|
| ec2:Describe* | Describe VPC resources |
| ecr:GetAuthorizationToken | Pull images |
| ecr:BatchCheckLayerAvailability | Check layers |
| ecr:GetDownloadUrlForLayer | Download layers |
| ecr:BatchGetImage | Get images |
| logs:CreateLogStream | CloudWatch Logs |
| logs:PutLogEvents | Send logs |

### Addon Roles (IRSA)
| Addon | Required Permissions |
|-------|---------------------|
| vpc-cni | ec2:Describe*, ec2:CreateNetworkInterface, ec2:DeleteNetworkInterface |
| ebs-csi-driver | ec2:CreateVolume, ec2:AttachVolume, ec2:DetachVolume, ec2:DeleteVolume |
| efs-csi-driver | elasticfilesystem:CreateMountTarget, elasticfilesystem:DeleteMountTarget |

## Cleanup Sequence (Delete Cluster)

```
1. List Fargate profiles: list-fargate-profiles
2. Delete each profile: delete-fargate-profile
3. Wait for profiles deleted (poll)
4. List nodegroups: list-nodegroups
5. Delete each nodegroup: delete-nodegroup
6. Wait for nodegroups deleted (poll)
7. List addons: list-addons
8. Delete each addon: delete-addon
9. Wait for addons deleted (poll)
10. Delete cluster: delete-cluster
11. Wait for cluster deleted (poll)
```

## Cleanup Sequence (Delete Nodegroup)

```
1. Verify no critical pods on nodes: kubectl get pods -o wide
2. Drain nodes: kubectl drain nodes
3. Delete nodegroup: delete-nodegroup
4. Wait for deletion (poll)
```

## Update Sequence (Cluster Version)

```
1. Check current version: describe-cluster
2. Verify target version supported: check version availability
3. Start update: update-cluster-version
4. Monitor update: describe-update
5. Update addons: update-addon for each
6. Update nodegroups: update-nodegroup-version
```

## Health Check Commands

```bash
# Cluster status
aws eks describe-cluster \
  --name {{cluster_name}} \
  --output json | jq '.cluster.status'

# Nodegroup health
aws eks describe-nodegroup \
  --cluster-name {{cluster_name}} \
  --nodegroup-name {{ng_name}} \
  --output json | jq '.nodegroup.health'

# Addon status
aws eks describe-addon \
  --cluster-name {{cluster_name}} \
  --addon-name vpc-cni \
  --output json | jq '.addon.status'

# Update status
aws eks list-updates \
  --name {{cluster_name}} \
  --output json

# Check pod status (kubectl)
kubectl get pods -A
kubectl get nodes
kubectl cluster-info
```

## kubectl Troubleshooting

```bash
# Update kubeconfig
aws eks update-kubeconfig \
  --name {{cluster_name}} \
  --region {{region}}

# Verify connectivity
kubectl cluster-info

# Check auth
kubectl auth can-i list pods

# Check nodes
kubectl get nodes -o wide

# Check pods
kubectl get pods -A -o wide

# Describe node
kubectl describe node {{node_name}}

# Check events
kubectl get events -A --sort-by='.lastTimestamp'
```

## Recovery Actions

| Error | Max Retries | Action |
|-------|-------------|--------|
| 5xx ServiceUnavailable | 3 | Backoff 30s, 60s, 120s; HALT after 3 |
| 429 ThrottlingException | 3 | Exponential backoff |
| 400 InvalidParameterException | 1 | Fix; retry once |
| 400 ResourceInUseException | 0 | HALT; use different name |
| 404 ResourceNotFoundException | 0 | HALT; verify name |
| 403 AccessDeniedException | 0 | HALT; check IAM |
| Health Issues | Monitor | Check health.issues array |

## CloudWatch Logs for Troubleshooting

```bash
# Check control plane logs
aws logs get-log-events \
  --log-group-name /aws/eks/{{cluster_name}}/cluster \
  --log-stream-name {{stream_name}} \
  --output json
```

## Common Pod Issues

| Issue | Cause | Resolution |
|-------|-------|------------|
| ImagePullBackOff | ECR permissions or image missing | Check ECR permissions, verify image |
| CrashLoopBackOff | Application error | Check pod logs |
| Pending | Resource unavailable | Check node capacity, taints |
| Evicted | Resource pressure | Check node resources |
| CreateContainerConfigError | ConfigMap/Secret missing | Create required resources |

## Network Troubleshooting

| Issue | Cause | Resolution |
|-------|-------|------------|
| Pod cannot reach API | Wrong SG rules | Allow node-to-control-plane |
| Service not accessible | LB not configured | Deploy AWS LB Controller |
| Cross-AZ issues | VPC CNI config | Check subnet config |
| DNS resolution fails | CoreDNS issue | Check CoreDNS addon |

## Node Troubleshooting

```bash
# Check node status via kubectl
kubectl get nodes
kubectl describe node {{node_name}}

# Check node logs (SSH to node)
sudo journalctl -u kubelet

# Check instance status
aws ec2 describe-instance-status \
  --instance-ids {{node_instance_id}} \
  --output json
```