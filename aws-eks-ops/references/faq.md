# FAQ — EKS

## 概述

本文档收集了 EKS 用户最常见的问题和解决方案，帮助您快速找到答案。

---

## 1. 集群创建和管理

### Q: 创建 EKS 集群需要多长时间？

**A**: 通常需要 10-15 分钟。具体时间取决于：
- 集群配置复杂度
- 网络配置
- 区域资源可用性

```bash
# 创建集群
aws eks create-cluster --name my-cluster ...

# 等待集群创建完成
aws eks wait cluster-active --name my-cluster --region us-east-1
```

### Q: 如何选择合适的 Kubernetes 版本？

**A**: 推荐策略：
- **生产环境**: 使用稳定版本（如 1.30）
- **测试环境**: 使用最新版本（如 1.31）
- **升级策略**: 每次升级一个版本（1.28 → 1.29 → 1.30）

```bash
# 查看可用版本
aws eks describe-cluster --name my-cluster --query 'cluster.version'

# 升级集群
aws eks update-cluster-version --name my-cluster --version 1.31
```

### Q: 如何删除 EKS 集群？

**A**: 删除前需要先清理所有资源：

```bash
# 1. 删除 Fargate profiles
aws eks delete-fargate-profile --cluster-name my-cluster --fargate-profile-name my-profile

# 2. 删除 addons
aws eks delete-addon --cluster-name my-cluster --addon-name vpc-cni

# 3. 删除 nodegroups
aws eks delete-nodegroup --cluster-name my-cluster --nodegroup-name my-nodegroup

# 4. 删除集群
aws eks delete-cluster --name my-cluster
```

---

## 2. 节点和节点组

### Q: 如何选择实例类型？

**A**: 根据工作负载类型选择：

| 工作负载类型 | 推荐实例 | 原因 |
|------------|---------|------|
| Web 应用 | t3.medium/large | 平衡成本和性能 |
| 数据库 | r5.large/xlarge | 高内存 |
| 批处理 | c5.large/xlarge | 高 CPU |
| GPU 训练 | g4dn.xlarge | GPU 加速 |
| 成本优化 | Spot 实例 | 节省 90% |

### Q: 如何扩缩节点组？

**A**: 使用 Cluster Autoscaler 或手动调整：

```bash
# 手动调整
aws eks update-nodegroup-config \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --scaling-config minSize=3,maxSize=10,desiredSize=5

# 使用 Cluster Autoscaler（自动）
helm install cluster-autoscaler autoscaler/cluster-autoscaler \
  --namespace kube-system \
  --set cloudProvider=aws \
  --set autoDiscovery.clusterName=my-cluster
```

### Q: 如何更新节点组？

**A**: 更新节点组版本：

```bash
# 更新节点组
aws eks update-nodegroup-version \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --version 1.30

# 等待更新完成
aws eks wait nodegroup-active \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup
```

---

## 3. 网络和负载均衡

### Q: 如何配置 LoadBalancer？

**A**: 使用 Service 或 Ingress：

```yaml
# Service 方式
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  type: LoadBalancer
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
```

```yaml
# Ingress 方式（需要 ALB Controller）
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-ingress
  annotations:
    kubernetes.io/ingress.class: alb
spec:
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: my-service
            port:
              number: 80
```

### Q: 如何配置 VPC CNI？

**A**: 默认配置通常足够，但可优化：

```bash
# 查看 VPC CNI 配置
kubectl get configmap aws-node -n kube-system -o yaml

# 启用自定义网络
kubectl set env daemonset/aws-node -n kube-system \
  AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG=true
```

### Q: 如何解决 DNS 解析问题？

**A**: 检查 CoreDNS 配置：

```bash
# 查看 CoreDNS 状态
kubectl get pods -n kube-system | grep coredns

# 扩容 CoreDNS
kubectl scale deployment coredns -n kube-system --replicas=3

# 测试 DNS
kubectl run dns-test --image=busybox --rm -it --restart=Never -- nslookup kubernetes.default
```

---

## 4. 存储

### Q: 如何选择存储类型？

**A**: 根据需求选择：

| 需求 | 存储类型 | 特点 |
|------|---------|------|
| 单 Pod 读写 | EBS gp3 | 低成本、高 IOPS |
| 多 Pod 读写 | EFS | 共享存储 |
| 高性能 | EBS io2 | 超高 IOPS |
| 临时存储 | emptyDir | 快速、易失 |

```yaml
# EBS gp3
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: gp3-pvc
spec:
  storageClassName: gp3
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 100Gi
```

### Q: 如何扩展 EBS 卷？

**A**: 启用自动扩展：

```bash
# 创建支持扩展的 StorageClass
kubectl apply -f - <<EOF
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3-expandable
parameters:
  type: gp3
provisioner: kubernetes.io/aws-ebs
allowVolumeExpansion: true
EOF

# 扩展 PVC
kubectl patch pvc my-pvc -p '{"spec":{"resources":{"requests":{"storage":"200Gi"}}}}'
```

---

## 5. 安全和权限

### Q: 如何配置 IAM 角色？

**A**: 使用 IRSA（推荐）：

```bash
# 1. 启用 OIDC 提供者
OIDC_URL=$(aws eks describe-cluster --name my-cluster --query 'cluster.identity.oidc.issuer' --output text | cut -d'/' -f3-)

aws iam create-open-id-connect-provider \
  --url https://$OIDC_URL \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list $(openssl s_client -servername oidc.eks.$(echo $OIDC_URL | cut -d'.' -f3-).amazonaws.com -showcerts -connect oidc.eks.$(echo $OIDC_URL | cut -d'.' -f3-).amazonaws.com:443 2>/dev/null </dev/null | openssl x509 -fingerprint -noout -in /dev/stdin | cut -d'=' -f2)

# 2. 创建 IAM 角色
cat > trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-east-1.amazonaws.com/id/${OIDC_ID}"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.eks.us-east-1.amazonaws.com/id/${OIDC_ID}:sub": "system:serviceaccount:my-namespace:my-service-account"
        }
      }
    }
  ]
}
EOF

aws iam create-role \
  --role-name MyServiceAccountRole \
  --assume-role-policy-document file://trust-policy.json

# 3. 附加策略
aws iam attach-role-policy \
  --role-name MyServiceAccountRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

# 4. 创建 ServiceAccount
kubectl create serviceaccount my-service-account -n my-namespace

kubectl annotate serviceaccount my-service-account \
  -n my-namespace \
  eks.amazonaws.com/role-arn=arn:aws:iam::123456789012:role/MyServiceAccountRole
```

### Q: 如何配置 Network Policies？

**A**: 使用 Calico 或 Cilium：

```yaml
# 默认拒绝所有入站流量
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: default
spec:
  podSelector: {}
  policyTypes:
  - Ingress
```

### Q: 如何启用 Secrets 加密？

**A**: 使用 KMS：

```bash
# 创建 KMS 密钥
KEY_ARN=$(aws kms create-key --description "EKS secrets encryption" --query 'KeyMetadata.Arn' --output text)

# 创建启用加密的集群
aws eks create-cluster \
  --name my-cluster \
  --encryption-config resources=secretEnvelopes,provider={keyArn=$KEY_ARN}
```

---

## 6. 监控和日志

### Q: 如何启用 CloudWatch 日志？

**A**: 启用控制平面日志：

```bash
# 启用所有日志类型
aws eks update-cluster-config \
  --name my-cluster \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'

# 安装 Fluent Bit
kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluent-bit-quickstart.yaml
```

### Q: 如何监控集群性能？

**A**: 使用 Prometheus + Grafana：

```bash
# 安装 Prometheus Operator
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --set grafana.adminPassword=admin
```

### Q: 如何查看 Pod 日志？

**A**: 使用 kubectl 或 stern：

```bash
# 查看单个 Pod 日志
kubectl logs my-pod

# 实时查看日志
kubectl logs -f my-pod

# 使用 stern 查看多个 Pod 日志
stern my-app
```

---

## 7. 自动扩缩容

### Q: 如何配置 HPA？

**A**: 创建 Horizontal Pod Autoscaler：

```bash
# 创建 HPA
kubectl autoscale deployment my-app \
  --cpu-percent=50 \
  --min=2 \
  --max=10

# 或使用 YAML
kubectl apply -f - <<EOF
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 50
EOF
```

### Q: 如何配置 Cluster Autoscaler？

**A**: 安装并配置：

```bash
# 安装 Cluster Autoscaler
helm install cluster-autoscaler autoscaler/cluster-autoscaler \
  --namespace kube-system \
  --set cloudProvider=aws \
  --set autoDiscovery.clusterName=my-cluster \
  --set awsRegion=us-east-1

# 为节点组添加自动发现标签
aws eks create-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --labels k8s.io/cluster-autoscaler/enabled=true,k8s.io/cluster-autoscaler/my-cluster=true
```

---

## 8. 故障排查

### Q: Pod 一直处于 Pending 状态？

**A**: 检查原因：

```bash
# 查看 Pod 详情
kubectl describe pod <pod-name>

# 检查节点资源
kubectl top nodes

# 查看事件
kubectl get events --sort-by='.lastTimestamp'

# 检查 Cluster Autoscaler 日志
kubectl logs -n kube-system deployment/cluster-autoscaler
```

### Q: 无法访问 LoadBalancer？

**A**: 检查配置：

```bash
# 查看 Service
kubectl get svc

# 检查安全组
aws ec2 describe-security-groups --group-ids <sg-id>

# 允许 HTTP 流量
aws ec2 authorize-security-group-ingress \
  --group-id <sg-id> \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0
```

### Q: ImagePullBackOff 错误？

**A**: 检查镜像和权限：

```bash
# 查看 Pod 日志
kubectl logs <pod-name>

# 检查镜像是否存在
aws ecr describe-images --repository-name <repo-name> --image-ids imageTag=latest

# 更新 ECR 权限
aws ecr set-repository-policy \
  --repository-name <repo-name> \
  --policy-text file://policy.json
```

---

## 9. 成本优化

### Q: 如何降低 EKS 成本？

**A**: 主要优化策略：

| 策略 | 节省 | 难度 |
|------|------|------|
| 使用 Spot 实例 | 90% | 中 |
| 使用 Graviton | 20-40% | 中 |
| 启用自动缩放 | 30-50% | 低 |
| 使用 gp3 存储 | 10-20% | 低 |
| 优化资源请求 | 20-40% | 中 |

### Q: 如何估算 EKS 成本？

**A**: 使用 AWS 成本估算器：

```bash
# 使用 Cost Explorer
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --filter '{"Dimensions": {"Key": "SERVICE", "Values": ["Amazon EKS"]}}'
```

---

## 10. 最佳实践

### Q: 生产环境推荐配置？

**A**: 关键配置：

1. **高可用**: 3 个可用区，至少 3 个节点
2. **安全性**: 启用 Secrets 加密、Network Policies
3. **监控**: CloudWatch + Prometheus + Grafana
4. **备份**: 定期备份 etcd 和应用数据
5. **自动扩缩容**: HPA + Cluster Autoscaler

### Q: 如何升级 EKS 集群？

**A**: 分步升级：

```bash
# 1. 备份集群
velero backup create pre-upgrade-backup

# 2. 升级集群版本
aws eks update-cluster-version --name my-cluster --version 1.31

# 3. 升级 addons
aws eks update-addon --cluster-name my-cluster --addon-name vpc-cni

# 4. 升级节点组
aws eks update-nodegroup-version --cluster-name my-cluster --nodegroup-name my-nodegroup --version 1.31
```

### Q: 如何优化性能？

**A**: 关键优化点：

1. **资源请求**: 设置合理的 requests 和 limits
2. **调度策略**: 使用亲和性和反亲和性
3. **存储**: 使用 gp3/io2 高性能存储
4. **网络**: 启用 VPC CNI 自定义网络
5. **DNS**: 扩容 CoreDNS

---

## 11. 常见问题速查

### 集群问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 集群创建失败 | 权限不足 | 检查 IAM 角色 |
| 集群无法访问 | 网络配置错误 | 检查安全组 |
| 节点无法加入 | 版本不匹配 | 升级节点组 |

### 应用问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| Pod 无法启动 | 资源不足 | 增加节点或调整请求 |
| 服务无法访问 | 配置错误 | 检查 Service/Ingress |
| 数据丢失 | 未持久化 | 使用 PVC |

### 性能问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 响应慢 | 资源不足 | 扩容或优化 |
| 高延迟 | 跨 AZ | 同 AZ 部署 |
| I/O 瓶颈 | 存储类型 | 使用高性能存储 |

---

## 12. 资源和链接

### 官方文档
- [EKS 官方文档](https://docs.aws.amazon.com/eks/)
- [Kubernetes 官方文档](https://kubernetes.io/docs/)
- [AWS CLI 文档](https://docs.aws.amazon.com/cli/)

### 工具
- [eksctl](https://eksctl.io/)
- [kubectl](https://kubernetes.io/docs/reference/kubectl/)
- [Helm](https://helm.sh/)

### 社区
- [AWS 论坛](https://forums.aws.amazon.com/)
- [Stack Overflow](https://stackoverflow.com/questions/tagged/amazon-eks)
- [GitHub Issues](https://github.com/aws/containers-roadmap/issues)

---

## 13. 获取帮助

### 如何提问

1. **提供详细信息**:
   - EKS 版本
   - 区域
   - 错误消息
   - 相关配置

2. **使用代码块**:
   ```bash
   # 命令示例
   aws eks describe-cluster --name my-cluster
   ```

3. **提供日志**:
   ```bash
   # 查看日志
   kubectl logs <pod-name>
   ```

### 联系支持

- **AWS Support**: https://console.aws.amazon.com/support/
- **Stack Overflow**: 使用 `amazon-eks` 标签
- **GitHub**: https://github.com/aws/containers-roadmap

---

**提示**: 如果问题未在此文档中列出，请查看 [Troubleshooting](troubleshooting.md) 文档或联系 AWS 支持。