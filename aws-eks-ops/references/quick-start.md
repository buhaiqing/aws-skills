# Quick Start Guide — EKS

## 概述

本指南帮助您在 10 分钟内创建并运行第一个 EKS 集群。

## 前置条件

### 必需工具

```bash
# 检查 AWS CLI
aws --version
# 应显示: aws-cli/2.x.x

# 检查 kubectl
kubectl version --client
# 应显示: Client Version: v1.30.x

# 检查 eksctl（可选，但推荐）
eksctl version
# 应显示: 0.x.x
```

### AWS 凭证配置

```bash
# 配置 AWS 凭证
aws configure

# 验证凭证
aws sts get-caller-identity

# 输出示例:
# {
#   "UserId": "AIDAI...",
#   "Account": "123456789012",
#   "Arn": "arn:aws:iam::123456789012:user/username"
# }
```

### 安装工具（如未安装）

```bash
# 安装 AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# 安装 kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# 安装 eksctl（推荐）
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin/
```

---

## 场景 1: 使用 eksctl 创建集群（推荐，5分钟）

### 步骤 1: 创建集群配置文件

```bash
cat > cluster-config.yaml <<EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-eks-cluster
  region: us-east-1
  version: "1.30"

managedNodeGroups:
  - name: nodegroup-1
    instanceType: t3.medium
    desiredCapacity: 2
    minSize: 1
    maxSize: 3
    volumeSize: 20
    ssh:
      allow: false
    labels:
      role: worker
    tags:
      Environment: dev
EOF
```

### 步骤 2: 创建集群

```bash
# 创建集群（约 10-15 分钟）
eksctl create cluster -f cluster-config.yaml

# 等待创建完成...
# 你会看到类似输出:
# [✓] EKS cluster "my-eks-cluster" in "us-east-1" region is ready
```

### 步骤 3: 验证集群

```bash
# 更新 kubeconfig
aws eks update-kubeconfig --name my-eks-cluster --region us-east-1

# 验证连接
kubectl get nodes

# 输出示例:
# NAME                                         STATUS   ROLES    AGE   VERSION
# ip-10-0-1-123.ec2.internal                  Ready    <none>   5m    v1.30.0
# ip-10-0-2-234.ec2.internal                  Ready    <none>   5m    v1.30.0

# 检查集群信息
kubectl cluster-info
kubectl get pods -A
```

### 步骤 4: 部署示例应用

```bash
# 部署 Nginx 应用
kubectl create deployment nginx --image=nginx:latest --replicas=2

# 暴露服务
kubectl expose deployment nginx --port=80 --type=LoadBalancer

# 等待 LoadBalancer 创建
sleep 60

# 获取外部 IP
kubectl get svc nginx

# 访问应用
curl http://$(kubectl get svc nginx -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# 输出示例:
# <!DOCTYPE html>
# <html>
# <head>
# <title>Welcome to nginx!</title>
# ...
```

---

## 场景 2: 使用 AWS CLI 创建集群（10分钟）

### 步骤 1: 创建 IAM 角色

```bash
# 创建集群 IAM 角色
cat > cluster-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "eks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

aws iam create-role \
  --role-name eksClusterRole \
  --assume-role-policy-document file://cluster-trust-policy.json

aws iam attach-role-policy \
  --role-name eksClusterRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy

# 创建节点 IAM 角色
cat > node-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

aws iam create-role \
  --role-name eksNodeRole \
  --assume-role-policy-document file://node-trust-policy.json

aws iam attach-role-policy \
  --role-name eksNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy

aws iam attach-role-policy \
  --role-name eksNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly

aws iam attach-role-policy \
  --role-name eksNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy

# 获取角色 ARN
CLUSTER_ROLE_ARN=$(aws iam get-role --role-name eksClusterRole --query 'Role.Arn' --output text)
NODE_ROLE_ARN=$(aws iam get-role --role-name eksNodeRole --query 'Role.Arn' --output text)
```

### 步骤 2: 创建 VPC 和子网

```bash
# 使用 eksctl 创建 VPC（推荐）
eksctl utils create-vpc-cluster \
  --region us-east-1 \
  --name my-eks-vpc \
  --vpc-cidr 10.0.0.0/16

# 或使用现有的 VPC
# 获取子网 ID
aws ec2 describe-subnets --filters "Name=vpc-id,Values=vpc-xxx" --query 'Subnets[*].SubnetId' --output text
```

### 步骤 3: 创建 EKS 集群

```bash
# 创建集群
aws eks create-cluster \
  --name my-eks-cluster \
  --region us-east-1 \
  --version 1.30 \
  --role-arn $CLUSTER_ROLE_ARN \
  --resources-vpc-config subnetIds=subnet-aaa,subnet-bbb,subnet-ccc,securityGroupIds=sg-xxx \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator"],"enabled":true}]}'

# 等待集群创建完成（约 10-15 分钟）
aws eks wait cluster-active --name my-eks-cluster --region us-east-1

# 验证集群状态
aws eks describe-cluster --name my-eks-cluster --query 'cluster.status'
```

### 步骤 4: 创建节点组

```bash
# 创建托管节点组
aws eks create-nodegroup \
  --cluster-name my-eks-cluster \
  --nodegroup-name my-nodegroup \
  --node-role $NODE_ROLE_ARN \
  --subnets subnet-aaa,subnet-bbb,subnet-ccc \
  --scaling-config minSize=1,maxSize=3,desiredSize=2 \
  --instance-types t3.medium \
  --ami-type AL2_x86_64 \
  --disk-size 20

# 等待节点组激活
aws eks wait nodegroup-active \
  --cluster-name my-eks-cluster \
  --nodegroup-name my-nodegroup \
  --region us-east-1

# 验证节点
kubectl get nodes
```

### 步骤 5: 更新 kubeconfig 并验证

```bash
# 更新 kubeconfig
aws eks update-kubeconfig --name my-eks-cluster --region us-east-1

# 验证
kubectl get nodes
kubectl get pods -A
```

---

## 场景 3: 部署完整的应用栈（5分钟）

### 步骤 1: 创建命名空间

```bash
kubectl create namespace my-app
```

### 步骤 2: 创建 Deployment

```bash
cat > deployment.yaml <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: my-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
      - name: nginx
        image: nginx:1.25
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
        livenessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 5
EOF

kubectl apply -f deployment.yaml
```

### 步骤 3: 创建 Service

```bash
cat > service.yaml <<EOF
apiVersion: v1
kind: Service
metadata:
  name: web-service
  namespace: my-app
spec:
  type: LoadBalancer
  selector:
    app: web-app
  ports:
  - port: 80
    targetPort: 80
    protocol: TCP
EOF

kubectl apply -f service.yaml
```

### 步骤 4: 配置自动扩缩容

```bash
# 创建 HPA
kubectl autoscale deployment web-app \
  --namespace my-app \
  --cpu-percent=50 \
  --min=3 \
  --max=10

# 验证 HPA
kubectl get hpa -n my-app
```

### 步骤 5: 创建 Ingress（可选）

```bash
cat > ingress.yaml <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-ingress
  namespace: my-app
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
spec:
  rules:
  - host: my-app.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-service
            port:
              number: 80
EOF

kubectl apply -f ingress.yaml
```

### 步骤 6: 验证应用

```bash
# 检查 Pod 状态
kubectl get pods -n my-app

# 检查 Service
kubectl get svc -n my-app

# 获取外部 IP
EXTERNAL_IP=$(kubectl get svc web-service -n my-app -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# 测试应用
curl http://$EXTERNAL_IP

# 查看日志
kubectl logs -n my-app -l app=web-app --tail=20

# 进入 Pod
kubectl exec -n my-app -it $(kubectl get pod -n my-app -l app=web-app -o jsonpath='{.items[0].metadata.name}') -- /bin/bash
```

---

## 场景 4: 清理资源

### 使用 eksctl 清理

```bash
# 删除集群
eksctl delete cluster --name my-eks-cluster --region us-east-1

# 确认删除
aws eks list-clusters --region us-east-1
```

### 使用 AWS CLI 清理

```bash
# 1. 删除服务
kubectl delete svc web-service -n my-app
kubectl delete ingress web-ingress -n my-app

# 2. 删除 Deployment
kubectl delete deployment web-app -n my-app

# 3. 删除命名空间
kubectl delete namespace my-app

# 4. 删除节点组
aws eks delete-nodegroup \
  --cluster-name my-eks-cluster \
  --nodegroup-name my-nodegroup \
  --region us-east-1

# 等待节点组删除
aws eks wait nodegroup-deleted \
  --cluster-name my-eks-cluster \
  --nodegroup-name my-nodegroup \
  --region us-east-1

# 5. 删除集群
aws eks delete-cluster \
  --name my-eks-cluster \
  --region us-east-1

# 等待集群删除
aws eks wait cluster-deleted \
  --name my-eks-cluster \
  --region us-east-1

# 6. 删除 IAM 角色（可选）
aws iam detach-role-policy \
  --role-name eksClusterRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy

aws iam delete-role --role-name eksClusterRole

aws iam detach-role-policy \
  --role-name eksNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy

aws iam detach-role-policy \
  --role-name eksNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly

aws iam detach-role-policy \
  --role-name eksNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy

aws iam delete-role --role-name eksNodeRole
```

---

## 常见问题排查

### 问题 1: kubectl 命令超时

**症状**: `kubectl get nodes` 超时

**原因**: kubeconfig 配置错误或网络问题

**解决方案**:
```bash
# 重新更新 kubeconfig
aws eks update-kubeconfig --name my-eks-cluster --region us-east-1

# 检查当前 context
kubectl config current-context

# 检查集群端点
aws eks describe-cluster --name my-eks-cluster --query 'cluster.endpoint'
```

### 问题 2: Pod 一直处于 Pending 状态

**症状**: `kubectl get pods` 显示状态为 Pending

**原因**: 节点资源不足或调度失败

**解决方案**:
```bash
# 查看详情
kubectl describe pod <pod-name>

# 查看事件
kubectl get events --sort-by='.lastTimestamp'

# 检查节点资源
kubectl top nodes
```

### 问题 3: 无法访问 LoadBalancer

**症状**: `curl http://<external-ip>` 失败

**原因**: 安全组规则或网络配置问题

**解决方案**:
```bash
# 检查 Service
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

### 问题 4: ImagePullBackOff 错误

**症状**: Pod 状态为 ImagePullBackOff

**原因**: ECR 权限或镜像不存在

**解决方案**:
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

## 下一步

### 学习资源

1. **EKS 官方文档**: https://docs.aws.amazon.com/eks/
2. **Kubernetes 官方文档**: https://kubernetes.io/docs/
3. **EKS 最佳实践**: https://aws.github.io/aws-eks-best-practices/

### 进阶主题

- [集群自动扩缩容](cluster-autoscaler.md)
- [监控和日志](monitoring-logging.md)
- [安全最佳实践](security-best-practices.md)
- [EKS 2024 新特性](eks-2024-features.md)

### 常见使用场景

1. **Web 应用部署**
   - 使用 Deployment + Service + Ingress
   - 配置 HPA 自动扩缩容
   - 使用 ALB 进行负载均衡

2. **批处理作业**
   - 使用 Job 或 CronJob
   - 使用 Spot 实例降低成本
   - 配置合理的资源限制

3. **微服务架构**
   - 使用多个命名空间隔离
   - 配置 Network Policies
   - 使用 Service Mesh (Istio, AWS App Mesh)

4. **无服务器架构**
   - 使用 Fargate 运行 Pod
   - 配置 Fargate Profile
   - 使用 Lambda 触发 Kubernetes 操作

---

## 参考命令速查

### 常用 kubectl 命令

```bash
# 获取资源
kubectl get pods -A
kubectl get nodes
kubectl get svc
kubectl get deployments

# 查看详情
kubectl describe pod <pod-name>
kubectl describe node <node-name>

# 查看日志
kubectl logs <pod-name>
kubectl logs -f <pod-name>  # 实时查看

# 执行命令
kubectl exec -it <pod-name> -- /bin/bash

# 应用配置
kubectl apply -f <file.yaml>
kubectl delete -f <file.yaml>

# 扩缩容
kubectl scale deployment <name> --replicas=5
```

### 常用 AWS CLI 命令

```bash
# 集群操作
aws eks list-clusters
aws eks describe-cluster --name <cluster-name>
aws eks create-cluster ...
aws eks delete-cluster --name <cluster-name>

# 节点组操作
aws eks list-nodegroups --cluster-name <cluster-name>
aws eks describe-nodegroup ...
aws eks create-nodegroup ...
aws eks delete-nodegroup ...

# Addon 操作
aws eks list-addons --cluster-name <cluster-name>
aws eks create-addon ...
aws eks update-addon ...
```

---

## 技巧和提示

### 1. 使用 kubectl 别名

```bash
# 在 ~/.bashrc 或 ~/.zshrc 中添加
alias k=kubectl
alias kgp='kubectl get pods'
alias kgn='kubectl get nodes'
alias kgs='kubectl get svc'
alias kd='kubectl describe'
alias kl='kubectl logs'
```

### 2. 使用 kubectl 自动补全

```bash
# Bash
source <(kubectl completion bash)
echo "source <(kubectl completion bash)" >> ~/.bashrc

# Zsh
source <(kubectl completion zsh)
echo "source <(kubectl completion zsh)" >> ~/.zshrc
```

### 3. 使用 k9s（交互式 Kubernetes 管理工具）

```bash
# 安装 k9s
brew install k9s  # macOS
# 或从 GitHub 下载

# 使用
k9s
```

### 4. 使用 stern（多 Pod 日志查看）

```bash
# 安装 stern
brew install stern  # macOS

# 查看所有 Pod 的日志
stern <app-name>

# 查看特定命名空间的日志
stern -n <namespace> <app-name>
```

---

## 成本估算

### 免费试用

- **EKS 控制平面**: 前 750 小时/月免费（约 30 天）
- **EC2 实例**: 首年 12 个月每月 750 小时的 t2.micro/t3.micro 实例免费

### 生产环境成本估算（月度）

| 组件 | 配置 | 成本 |
|------|------|------|
| EKS 控制平面 | 1 个集群 | $73/月 |
| EC2 节点 | 3 x t3.medium | ~$90/月 |
| EBS 存储 | 3 x 20 GB gp3 | ~$9/月 |
| CloudWatch | 日志和指标 | ~$20/月 |
| Load Balancer | ALB | ~$19/月 |
| **总计** | | **~$211/月** |

### 成本优化建议

1. 使用 Spot 实例节省高达 90%
2. 使用 Graviton 实例（ARM64）节省 20-40%
3. 使用 Fargate 节省节点管理成本
4. 配置自动缩容以减少空闲资源
5. 使用 CloudWatch 指标优化资源使用

---

## 总结

恭喜！您已经成功：

✅ 创建了第一个 EKS 集群
✅ 部署了示例应用
✅ 配置了自动扩缩容
✅ 学会了基本操作和故障排查

现在您可以：

- 部署自己的应用程序
- 探索更多 EKS 功能
- 实施生产环境最佳实践
- 优化成本和性能

祝您使用 EKS 愉快！