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
9. **Check Access Entries**: `aws eks list-access-entries`
10. **Check Cluster Autoscaler**: `kubectl logs -n kube-system deployment/cluster-autoscaler`

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
4. List addons: list-addons
5. Delete each addon: delete-addon
6. Wait for addons deleted (poll)
7. List nodegroups: list-nodegroups
8. Delete each nodegroup: delete-nodegroup
9. Wait for nodegroups deleted (poll)
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

## Cluster Autoscaler Troubleshooting

### Pod 持续 Pending

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Pod Pending | Cluster Autoscaler not running | Check CA pod status |
| Pod Pending | Node group at max size | Increase maxSize |
| Pod Pending | Insufficient resource requests | Set appropriate requests |
| Pod Pending | Node group not discovered | Check auto-discovery tags |

### 诊断命令

```bash
# 检查 Cluster Autoscaler 状态
kubectl get pods -n kube-system | grep cluster-autoscaler

# 查看 Cluster Autoscaler 日志
kubectl logs -n kube-system deployment/cluster-autoscaler -f

# 查看 Pending Pod
kubectl get pods --field-selector=status.phase=Pending

# 查看 Pending Pod 详情
kubectl describe pod <pod-name>

# 查看节点组状态
aws eks describe-nodegroup \
  --cluster-name {{cluster_name}} \
  --nodegroup-name {{nodegroup_name}} \
  --query 'nodegroup.status,nodegroup.scalingConfig'

# 检查自动发现标签
aws eks describe-nodegroup \
  --cluster-name {{cluster_name}} \
  --nodegroup-name {{nodegroup_name}} \
  --query 'nodegroup.tags'
```

### 常见错误

| Error | Cause | Resolution |
|-------|-------|------------|
| `scale up failed` | IAM permissions insufficient | Add AutoScalingFullAccess policy |
| `scale down failed` | PDB blocks scale down | Adjust PDB minAvailable |
| `no nodes available` | Node group at max size | Increase maxSize |
| `node not ready` | Node not initialized | Wait for node ready |

### 验证 Cluster Autoscaler 配置

```bash
# 检查 Cluster Autoscaler 环境变量
kubectl get deployment cluster-autoscaler -n kube-system -o yaml | grep -A 10 env:

# 检查 IAM 角色
kubectl get serviceaccount cluster-autoscaler -n kube-system -o yaml

# 验证 IAM 权限
aws iam get-role --role-name ClusterAutoscalerRole

# 检查 Pod 资源请求
kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[*].resources.requests}{"\n"}{end}'
```

## EKS Access Entries Troubleshooting

### 访问被拒绝

| Symptom | Cause | Resolution |
|---------|-------|------------|
| kubectl access denied | Access Entry not created | Create Access Entry |
| kubectl access denied | Policy not associated | Associate access policy |
| kubectl access denied | Wrong scope | Check cluster vs namespace scope |

### 诊断命令

```bash
# 列出所有 Access Entries
aws eks list-access-entries --cluster-name {{cluster_name}}

# 描述 Access Entry
aws eks describe-access-entry \
  --cluster-name {{cluster_name}} \
  --principal-arn arn:aws:iam::{{account_id}}:user/{{username}}

# 列出关联的策略
aws eks list-associated-access-policies \
  --cluster-name {{cluster_name}} \
  --principal-arn arn:aws:iam::{{account_id}}:user/{{username}}

# 检查当前用户身份
aws sts get-caller-identity

# 测试 kubectl 访问
kubectl auth can-i list pods --all-namespaces
```

### 常见问题

| Issue | Cause | Resolution |
|-------|-------|------------|
| Cannot create cluster | Principal type wrong | Use STANDARD type |
| Policy not applied | Wrong ARN format | Verify policy ARN |
| Namespace access denied | Namespace not in scope | Add namespace to scope |
| Migrated from aws-auth | Old ConfigMap active | Delete aws-auth ConfigMap |

### 从 aws-auth 迁移

```bash
# 检查 aws-auth ConfigMap
kubectl get configmap aws-auth -n kube-system -o yaml

# 删除 aws-auth ConfigMap（迁移后）
kubectl delete configmap aws-auth -n kube-system

# 验证 Access Entries
aws eks list-access-entries --cluster-name {{cluster_name}}
```

## Pod Security Standards Troubleshooting

### Pod 创建失败

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Pod rejected | Violates PSS | Adjust pod spec |
| Pod rejected | Wrong security level | Change PSS level |
| Pod rejected | Privileged mode | Remove privileged flag |

### 诊断命令

```bash
# 查看 Pod 错误
kubectl describe pod <pod-name> | grep -A 5 "Forbidden"

# 检查命名空间 PSS 标签
kubectl describe namespace {{namespace}} | grep -A 5 "Labels:"

# 查看 PSS 违规事件
kubectl get events -n {{namespace}} --field-selector reason=FailedValidation

# 验证 Pod 安全上下文
kubectl get pod <pod-name> -o yaml | grep -A 10 "securityContext:"

# 测试 Pod 创建
kubectl run test-pod --image=nginx --dry-run=client -o yaml
```

### 常见违规

| Violation | Cause | Resolution |
|-----------|-------|------------|
| `privileged` | Pod runs as privileged | Remove `privileged: true` |
| `hostNetwork` | Pod uses host network | Remove `hostNetwork: true` |
| `hostPath` | Pod mounts host path | Use volume instead |
| `runAsRoot` | Container runs as root | Set `runAsNonRoot: true` |
| `capabilities` | Too many capabilities | Reduce capabilities |

### 解决 PSS 违规

```yaml
# 修改 Pod 规范
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: secure-container
    image: nginx:latest
    securityContext:
      allowPrivilegeEscalation: false
      capabilities:
        drop:
        - ALL
```

## Network Policies Troubleshooting

### 网络连接失败

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Cannot reach service | Network policy blocks | Add allow rule |
| DNS resolution fails | CoreDNS blocked | Allow DNS traffic |
| Cross-namespace blocked | No egress rule | Add egress policy |

### 诊断命令

```bash
# 列出网络策略
kubectl get networkpolicies --all-namespaces

# 描述网络策略
kubectl describe networkpolicy <policy-name> -n {{namespace}}

# 测试 Pod 连接
kubectl run test-pod --image=busybox --rm -it --restart=Never -- wget -O- http://service-name

# 查看 Pod IP
kubectl get pod <pod-name> -o jsonpath='{.status.podIP}'

# 检查网络插件
kubectl get pods -n kube-system | grep -E "(calico|cilium|weave)"

# 测试 DNS
kubectl run dns-test --image=busybox --rm -it --restart=Never -- nslookup kubernetes.default
```

### 常见问题

| Issue | Cause | Resolution |
|-------|-------|------------|
| Default deny all | No policy allows traffic | Create allow policy |
| Service unreachable | Port not allowed | Add port to policy |
| Egress blocked | No egress rule | Add egress policy |
| Inter-namespace blocked | Namespace selector wrong | Fix selector |

### 调试网络策略

```bash
# 创建测试 Pod
kubectl run debug-pod --image=nicolaka/netshoot --rm -it --restart=Never -- bash

# 在调试 Pod 中测试
# 测试 TCP 连接
nc -zv service-name 80

# 测试 DNS
nslookup kubernetes.default

# 测试 ICMP
ping target-pod-ip

# 查看路由表
ip route

# 查看 iptables
iptables -L -n -v
```

## Monitoring and Logging Troubleshooting

### CloudWatch Logs 不显示

| Symptom | Cause | Resolution |
|---------|-------|------------|
| No logs in CloudWatch | Fluent Bit not running | Check Fluent Bit pod |
| Logs delayed | Log group not created | Create log group manually |
| Missing logs | Wrong log format | Check log configuration |

### 诊断命令

```bash
# 检查 Fluent Bit 状态
kubectl get pods -n logging | grep fluent-bit

# 查看 Fluent Bit 日志
kubectl logs -n logging deployment/fluent-bit -f

# 检查日志组
aws logs describe-log-groups \
  --log-group-name-prefix /aws/eks/{{cluster_name}}

# 测试日志发送
kubectl logs <pod-name> --tail=10

# 查看 CloudWatch 日志
aws logs tail /aws/eks/{{cluster_name}}/application --follow
```

### Prometheus 指标不显示

| Symptom | Cause | Resolution |
|---------|-------|------------|
| No metrics | ServiceMonitor not created | Create ServiceMonitor |
| Scrape failed | Wrong port/path | Fix ServiceMonitor config |
| Metrics missing | Pod not labeled | Add required labels |

### 诊断命令

```bash
# 检查 Prometheus 状态
kubectl get pods -n monitoring | grep prometheus

# 查看 Prometheus 日志
kubectl logs -n monitoring prometheus-kube-prometheus-prometheus-0 -f

# 检查 ServiceMonitor
kubectl get servicemonitor -A

# 测试指标端点
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090
curl http://localhost:9090/api/v1/targets
```

### X-Ray 追踪不显示

| Symptom | Cause | Resolution |
|---------|-------|------------|
| No traces | X-Ray daemon not running | Check X-Ray pod |
| Segments missing | Application not instrumented | Add X-Ray SDK |
| Invalid segments | Wrong sample rate | Adjust sampling |

### 诊断命令

```bash
# 检查 X-Ray Daemon
kubectl get pods -n aws-xray | grep xray

# 查看 X-Ray 日志
kubectl logs -n aws-xray daemonset/aws-xray-daemon -f

# 查询 X-Ray 追踪
aws xray get-trace-summaries \
  --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ)
```

## EKS 2024 Features Troubleshooting

### Pod Identity 不工作

| Symptom | Cause | Resolution |
|---------|-------|------------|
| IAM credentials not found | Pod Identity not enabled | Enable Pod Identity Agent |
| Access denied | Wrong role association | Fix IAM role |
| Stale credentials | Pod not updated | Restart pod |

### 诊断命令

```bash
# 检查 Pod Identity Agent
kubectl get pods -n kube-system | grep pod-identity-agent

# 查看 Pod Identity 配置
aws eks describe-pod-identity-agent-config \
  --cluster-name {{cluster_name}}

# 测试 Pod 身份
kubectl exec -it <pod-name> -- aws sts get-caller-identity

# 查看环境变量
kubectl exec -it <pod-name> -- env | grep AWS
```

### Bottlerocket 节点问题

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Nodes not joining | Wrong AMI type | Use BOTTLEROCKET AMI |
| Cannot SSH | No SSH access | Use SSM instead |
| Updates failing | Wrong update config | Check Bottlerocket settings |

### 诊断命令

```bash
# 检查 Bottlerocket 节点
kubectl get nodes -l os=bottlerocket

# 通过 SSM 访问节点
aws ssm send-command \
  --instance-ids {{instance_id}} \
  --document-name AWS-RunShellScript \
  --parameters commands='cat /etc/os-release'

# 查看 Bottlerocket 版本
kubectl describe node <node-name> | grep OS
```

### Fargate Pod 不运行

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Pods on EC2 instead | Selector mismatch | Fix Fargate Profile |
| Profile not found | Wrong namespace | Update profile |
| IAM role missing | Pod execution role | Create role |

### 诊断命令

```bash
# 列出 Fargate Profiles
aws eks list-fargate-profiles --cluster-name {{cluster_name}}

# 描述 Fargate Profile
aws eks describe-fargate-profile \
  --cluster-name {{cluster_name}} \
  --fargate-profile-name {{profile_name}}

# 检查 Pod 调度
kubectl get pod <pod-name> -o jsonpath='{.spec.nodeName}'

# 查看 Fargate 事件
kubectl get events -n {{namespace}} --field-selector reason=TriggeredScaleUp
```

## 常见错误代码（新增）

| Error Code | HTTP | New Feature | Resolution |
|------------|------|-------------|------------|
| InvalidAccessEntryException | 400 | Access Entries | Verify principal ARN |
| PolicyNotFoundException | 404 | Access Entries | Check policy ARN |
| AccessScopeInvalidException | 400 | Access Entries | Verify scope |
| PodIdentityAgentConfigNotFound | 404 | Pod Identity | Enable agent |
| BottlerocketUpdateFailed | 500 | Bottlerocket | Check settings |
| FargateProfileCreationFailed | 400 | Fargate | Verify IAM role |

## 性能问题排查

### 集群响应慢

| Symptom | Cause | Resolution |
|---------|-------|------------|
| API Server slow | High load | Scale control plane |
| DNS resolution slow | CoreDNS issue | Scale CoreDNS |
| Network latency | AZ spread | Use local AZ |

### 诊断命令

```bash
# 检查 API Server 延迟
kubectl get --raw='/metrics' | grep apiserver_request_duration_seconds

# 检查 DNS 延迟
kubectl exec -it <pod-name> -- time nslookup kubernetes.default

# 检查节点资源
kubectl top nodes

# 检查 Pod 资源
kubectl top pods -A
```

## 安全问题排查

### 未授权访问

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Unauthenticated access | Public endpoint open | Restrict CIDRs |
| IAM bypassed | Old aws-auth active | Migrate to Access Entries |
| Secrets leaked | Not encrypted | Enable encryption |

### 诊断命令

```bash
# 检查集群端点
aws eks describe-cluster --name {{cluster_name}} \
  --query 'cluster.resourcesVpcConfig.endpointPublicAccess'

# 检查 Access Entries
aws eks list-access-entries --cluster-name {{cluster_name}}

# 检查加密配置
aws eks describe-cluster --name {{cluster_name}} \
  --query 'cluster.encryptionConfig'

# 审计 CloudTrail
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue={{cluster_name}}
```

## 故障排查最佳实践

### 1. 建立故障排查流程

```
问题报告 → 收集日志 → 识别根本原因 → 制定解决方案 → 验证修复 → 防止复发
```

### 2. 使用调试工具

| 工具 | 用途 |
|------|------|
| kubectl | Kubernetes CLI |
| k9s | 交互式终端 UI |
| stern | 多 Pod 日志查看 |
| kubectl-trace | BPF 跟踪 |
| kubectl-debug | 调试 Pod |

### 3. 监控和告警

- 设置关键指标告警
- 配置日志告警
- 使用 CloudWatch Dashboard
- 定期检查健康状态

### 4. 文档和知识库

- 记录常见问题和解决方案
- 建立故障排查手册
- 分享团队经验
- 持续改进流程