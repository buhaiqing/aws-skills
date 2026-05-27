# EKS 2024 Features

## EKS Access Entries (新认证机制)

### 概述
EKS Access Entries 是 EKS 推荐的新认证方式，替代传统的 `aws-auth ConfigMap`。

### 优势
- 原生集成，无需管理 ConfigMap
- 支持 IAM 用户、角色和组
- 更好的权限管理
- 符合 Kubernetes RBAC 最佳实践

### CLI 示例

```bash
# 创建 Access Entry (IAM 用户)
aws eks create-access-entry \
  --cluster-name my-cluster \
  --principalArn arn:aws:iam::123456789012:user/admin \
  --type STANDARD

# 创建 Access Entry (IAM 角色)
aws eks create-access-entry \
  --cluster-name my-cluster \
  --principalArn arn:aws:iam::123456789012:role/eks-admin \
  --type STANDARD

# 列出所有 Access Entries
aws eks list-access-entries \
  --cluster-name my-cluster

# 描述 Access Entry
aws eks describe-access-entry \
  --cluster-name my-cluster \
  --principalArn arn:aws:iam::123456789012:user/admin

# 关联 Kubernetes 组
aws eks associate-access-policy \
  --cluster-name my-cluster \
  --principalArn arn:aws:iam::123456789012:user/admin \
  --policyArn arn:aws:eks:us-east-1:123456789012:access-policy/AmazonEKSEditPolicy \
  --access-scope type=cluster

# 关联到特定命名空间
aws eks associate-access-policy \
  --cluster-name my-cluster \
  --principalArn arn:aws:iam::123456789012:user/developer \
  --policyArn arn:aws:eks:us-east-1:123456789012:access-policy/AmazonEKSViewPolicy \
  --access-scope type=namespace,namespaces=dev

# 取消关联
aws eks dissociate-access-policy \
  --cluster-name my-cluster \
  --principalArn arn:aws:iam::123456789012:user/admin \
  --policyArn arn:aws:eks:us-east-1:123456789012:access-policy/AmazonEKSEditPolicy \
  --access-scope type=cluster

# 删除 Access Entry
aws eks delete-access-entry \
  --cluster-name my-cluster \
  --principalArn arn:aws:iam::123456789012:user/admin
```

### boto3 示例

```python
import boto3

client = boto3.client('eks', region_name='us-east-1')

# 创建 Access Entry
response = client.create_access_entry(
    clusterName='my-cluster',
    principalArn='arn:aws:iam::123456789012:user/admin',
    type='STANDARD'
)

# 关联访问策略
response = client.associate_access_policy(
    clusterName='my-cluster',
    principalArn='arn:aws:iam::123456789012:user/admin',
    policyArn='arn:aws:eks:us-east-1:123456789012:access-policy/AmazonEKSEditPolicy',
    accessScope={
        'type': 'cluster'
    }
)

# 关联到命名空间
response = client.associate_access_policy(
    clusterName='my-cluster',
    principalArn='arn:aws:iam::123456789012:user/developer',
    policyArn='arn:aws:eks:us-east-1:123456789012:access-policy/AmazonEKSViewPolicy',
    accessScope={
        'type': 'namespace',
        'namespaces': ['dev']
    }
)

# 列出 Access Entries
response = client.list_access_entries(clusterName='my-cluster')

# 获取关联的策略
response = client.list_associated_access_policies(
    clusterName='my-cluster',
    principalArn='arn:aws:iam::123456789012:user/admin'
)
```

### 预定义的访问策略

| 策略名称 | 描述 |
|---------|------|
| AmazonEKSClusterAdminPolicy | 集群管理员权限 |
| AmazonEKSEditPolicy | 编辑权限（大部分资源） |
| AmazonEKSViewPolicy | 只读权限 |
| AmazonEKSEditFargateProfilePolicy | 管理 Fargate 配置文件 |

## EKS Pod Identity Agent

### 概述
EKS Pod Identity Agent 简化了 Pod 访问 AWS 服务的流程，是 IRSA 的新替代方案。

### CLI 示例

```bash
# 在 EKS 集群上启用 Pod Identity Agent
aws eks associate-pod-identity-agent-config \
  --cluster-name my-cluster

# 描述 Pod Identity Agent 配置
aws eks describe-pod-identity-agent-config \
  --cluster-name my-cluster

# 删除 Pod Identity Agent 配置
aws eks disassociate-pod-identity-agent-config \
  --cluster-name my-cluster
```

### 使用方式（kubectl）

```bash
# 创建 IAM 角色和信任策略（Pod Identity 自动创建）
# 通过 kubectl 创建 Pod Identity 关联
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      serviceAccountName: my-service-account
      containers:
      - name: my-container
        image: my-app:latest
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-service-account
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/MyPodRole
EOF
```

## EKS Cluster Provider

### 概述
EKS Cluster Provider 允许第三方工具直接管理 EKS 集群。

### 支持的 Provider
- AWS Elastic Beanstalk
- AWS Serverless Application Repository
- AWS App Mesh
- AWS Cloud Map

## EKS 1.31 新特性

### 概述
EKS 1.31（2024年最新版本）包含以下新特性：

| 特性 | 描述 |
|------|------|
| Enhanced Security | 默认启用更严格的安全策略 |
| Improved VPC CNI | 性能优化和新的网络模式 |
| Better Auto-scaling | 集群自动扩缩容改进 |
| Addon Updates | 多个 add-on 的版本更新 |

### 升级检查

```bash
# 检查可用版本
aws eks describe-cluster \
  --name my-cluster \
  --query 'cluster.version'

# 检查可用更新
aws eks describe-cluster \
  --name my-cluster \
  --query 'cluster.upgradePolicy'
```

## EKS Add-on Auto-Update

### 概述
配置 EKS add-on 自动更新策略，减少手动维护。

### CLI 示例

```bash
# 创建启用自动更新的 addon
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --addon-version v1.16.0-eksbuild.1 \
  --service-account-role-arn arn:aws:iam::123456789012:role/eksVPCCniRole \
  --resolve-conflicts OVERWRITE \
  --configuration-values '{"autoScaling":true}' \
  --auto-scaling-config \
      minimumNodeCount=1,maximumNodeCount=100,desiredNodeCount=10

# 更新 addon 配置
aws eks update-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --auto-scaling-config \
      minimumNodeCount=2,maximumNodeCount=50,desiredNodeCount=5
```

## EKS Local Clusters (EKS Anywhere)

### 概述
EKS Anywhere 允许在本地数据中心运行 EKS 集群。

### 使用工具

```bash
# 安装 eksctl-anywhere
curl "https://anywhere-assets.eks.amazonaws.com/releases/eks-a/0.15.0/eksctl-anywhere-linux-amd64" \
  -o eksctl-anywhere
chmod +x eksctl-anywhere
sudo mv eksctl-anywhere /usr/local/bin/

# 创建本地集群
eksctl-anywhere create cluster \
  --config my-cluster.yaml

# 集群配置示例
# my-cluster.yaml
apiVersion: anywhere.eks.amazonaws.com/v1alpha1
kind: Cluster
metadata:
  name: my-cluster
spec:
  clusterNetwork:
    pods:
      cidrBlocks:
      - 192.168.0.0/16
    services:
      cidrBlocks:
      - 10.96.0.0/12
  controlPlaneConfiguration:
    count: 3
    endpoint:
      host: 192.168.1.100
    machineGroupRef:
      name: my-cluster-cp
  datacenterRef:
    kind: DockerDatacenterConfig
    name: my-cluster
  kubernetesVersion: "1.29"
  workerNodeGroupConfigurations:
  - count: 3
    machineGroupRef:
      name: my-cluster-workers
```

## Bottlerocket OS

### 概述
Bottlerocket 是专为容器运行的最小化操作系统，提供增强的安全性。

### CLI 示例

```bash
# 创建 Bottlerocket 节点组
aws eks create-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name bottlerocket-ng \
  --node-role arn:aws:iam::123456789012:role/eksNodeRole \
  --subnets subnet-aaa,subnet-bbb \
  --scaling-config minSize=1,maxSize=5,desiredSize=2 \
  --ami-type BOTTLEROCKET_x86_64 \
  --instance-types t3.medium \
  --labels os=bottlerocket

# Bottlerocket 特性
# - 更小的攻击面
# - 自动更新
# - 不可变基础设施
# - 专为容器优化
```

### Boot 配置

```bash
# 通过 user-data 配置 Bottlerocket
cat <<EOF > user-data.toml
[settings.kubernetes]
cluster-name = "my-cluster"
cluster-certificate = "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----\n"
api-server = "https://API_ENDPOINT"
[settings.kubernetes.node-labels]
os = "bottlerocket"
[settings.kubernetes.node-taints]
special = "dedicated:NoSchedule"
EOF
```

## EKS Service Discovery

### 概述
使用 AWS Cloud Map 进行服务发现。

### CLI 示例

```bash
# 创建服务发现
aws servicediscovery create-service \
  --name my-service \
  --dns-config '{
    "DnsRecords": [
      {"Type": "A", "TTL": 60},
      {"Type": "SRV", "TTL": 60}
    ]
  }' \
  --namespace-id ns-xxx

# 在 Kubernetes 中使用 ExternalDNS
kubectl apply -f - <<EOF
apiVersion: v1
kind: Service
metadata:
  name: my-service
  annotations:
    external-dns.alpha.kubernetes.io/hostname: my-service.example.com
spec:
  type: LoadBalancer
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
EOF
```

## EKS 优化建议

### 成本优化

1. **使用 Spot 实例**
   - 对于可中断的工作负载
   - 节省高达 90% 的成本

2. **混合使用容量类型**
   - 关键工作负载使用 On-Demand
   - 批处理工作使用 Spot
   - 自动调度到合适的实例类型

3. **Right-sizing**
   - 使用 CloudWatch Insights 监控资源使用
   - 调整 instance types 和节点数量

### 性能优化

1. **VPC CNI 自定义网络**
   - 为不同工作负载使用不同的子网
   - 更好的 IP 地址管理

2. **Warm Pools**
   - 预热节点，减少启动时间
   - 适用于突发工作负载

3. **优化 kube-proxy 模式**
   - 使用 IPVS 替代 iptables
   - 更好的大规模集群性能

### 安全性优化

1. **启用加密**
   - Secret encryption with KMS
   - EBS volume encryption
   - ENI encryption

2. **网络隔离**
   - 使用 Network Policies
   - 隔离不同的命名空间
   - 限制 pod-to-pod 通信

3. **审计和合规**
   - 启用所有控制平面日志
   - 使用 CloudTrail 记录 API 调用
   - 定期审计 IAM 权限

## 参考文档

- [EKS Access Entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-id.html)
- [EKS Add-ons](https://docs.aws.amazon.com/eks/latest/userguide/eks-add-ons.html)
- [Bottlerocket](https://github.com/bottlerocket-os/bottlerocket)
- [EKS Anywhere](https://docs.aws.amazon.com/eks/latest/userguide/eks-anywhere.html)