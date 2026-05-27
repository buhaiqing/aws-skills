# Cost Optimization — EKS

## 概述

EKS 成本优化是降低 Kubernetes 在 AWS 上运行成本的关键策略。本指南涵盖从基础设施到应用层的全面优化方法。

## EKS 成本组成

### 成本结构

| 组件 | 成本模型 | 优化潜力 |
|------|---------|---------|
| EKS 控制平面 | $0.10/小时/集群 (~$73/月) | 低 |
| EC2 工作节点 | 按实例类型和使用量 | 高（90%） |
| EBS 存储 | 按 GB 和 IOPS | 中（30-50%） |
| EFS 存储 | 按 GB 和吞吐量 | 中（20-40%） |
| Load Balancer | 按使用量和 LCU | 中（20-30%） |
| CloudWatch | 按日志和指标 | 中（30-50%） |
| ECR | 按 GB 和请求 | 低（10-20%） |
| VPC | 数据传输和 NAT | 中（20-40%） |

### 总成本估算（示例）

| 配置 | 月度成本 | 优化后成本 | 节省 |
|------|---------|-----------|------|
| 小型集群（2 个 t3.medium 节点） | ~$150 | ~$90 | 40% |
| 中型集群（5 个 t3.large 节点） | ~$350 | ~$180 | 49% |
| 大型集群（10 个 t3.xlarge 节点） | ~$700 | ~$300 | 57% |

---

## 1. Spot 实例优化

### 概述

Spot 实例可以节省高达 90% 的成本，但可能会被中断。

### 使用场景

✅ **适合使用 Spot**:
- 批处理作业
- CI/CD 流水线
- 数据处理
- 测试环境
- 无状态应用

❌ **不适合使用 Spot**:
- 关键生产应用
- 有状态应用
- 需要长时间运行的服务
- 对中断敏感的应用

### 创建 Spot 节点组

#### 使用 eksctl

```yaml
# spot-nodegroup.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-eks-cluster
  region: us-east-1

managedNodeGroups:
  - name: spot-nodegroup
    instanceTypes:
      - m5.large
      - m5a.large
      - m5d.large
      - m5n.large
    minSize: 0
    maxSize: 20
    desiredSize: 5
    capacityType: SPOT
    labels:
      capacity-type: spot
    taints:
      - key: spot
        value: "true"
        effect: NoSchedule
    tags:
      capacity-type: spot
```

```bash
# 创建 Spot 节点组
eksctl create nodegroup -f spot-nodegroup.yaml
```

#### 使用 AWS CLI

```bash
# 创建 Spot 节点组
aws eks create-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name spot-ng \
  --node-role arn:aws:iam::123456789012:role/eksNodeRole \
  --subnets subnet-aaa,subnet-bbb,subnet-ccc \
  --scaling-config minSize=0,maxSize=20,desiredSize=5 \
  --instance-types m5.large,m5a.large,m5d.large,m5n.large \
  --capacity-type SPOT \
  --labels capacity-type=spot \
  --taints key=spot,value=true,effect=NoSchedule \
  --tags capacity-type=spot
```

### 混合容量策略

#### On-Demand + Spot 混合

```yaml
# mixed-capacity.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-eks-cluster
  region: us-east-1

managedNodeGroups:
  - name: ondemand-ng
    instanceType: t3.large
    minSize: 2
    maxSize: 5
    desiredSize: 2
    capacityType: ON_DEMAND
    labels:
      capacity-type: ondemand

  - name: spot-ng
    instanceTypes:
      - t3.large
      - t3a.large
    minSize: 0
    maxSize: 20
    desiredSize: 8
    capacityType: SPOT
    labels:
      capacity-type: spot
    taints:
      - key: spot
        value: "true"
        effect: NoSchedule
```

### Spot 中断处理

#### 使用 Spot Instance Interruption Notices

```yaml
# spot-interruption-handler.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: spot-interruption-handler
  namespace: kube-system
spec:
  selector:
    matchLabels:
      app: spot-interruption-handler
  template:
    metadata:
      labels:
        app: spot-interruption-handler
    spec:
      serviceAccountName: spot-interruption-handler
      containers:
      - name: spot-handler
        image: public.ecr.aws/commercial-customer-success/eks-spot-interruption-handler:v0.8
        env:
        - name: NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
        - name: POD_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: NAMESPACE
          valueFrom:
            fieldRef:
              fieldPath: metadata.namespace
        volumeMounts:
        - name: metadata
          mountPath: /etc/podinfo
          readOnly: true
      volumes:
      - name: metadata
        downwardAPI:
          items:
          - path: labels
            fieldRef:
              fieldPath: metadata.labels
          - path: annotations
            fieldRef:
              fieldPath: metadata.annotations
```

```bash
# 部署中断处理器
kubectl apply -f spot-interruption-handler.yaml

# 创建 ServiceAccount 和 RBAC
kubectl create serviceaccount spot-interruption-handler -n kube-system
kubectl create clusterrolebinding spot-interruption-handler \
  --clusterrole=system:node-proxier \
  --serviceaccount=kube-system:spot-interruption-handler
```

### 容忍度配置

```yaml
# 在 Pod 中容忍 Spot 污点
apiVersion: apps/v1
kind: Deployment
metadata:
  name: batch-job
spec:
  replicas: 10
  selector:
    matchLabels:
      app: batch-job
  template:
    metadata:
      labels:
        app: batch-job
    spec:
      tolerations:
      - key: spot
        operator: Equal
        value: "true"
        effect: NoSchedule
      nodeSelector:
        capacity-type: spot
      containers:
      - name: worker
        image: my-app:latest
        resources:
          requests:
            cpu: 1000m
            memory: 2Gi
```

---

## 2. Right-Sizing 优化

### 概述

Right-Sizing 是确保使用合适大小的实例，既不浪费资源也不影响性能。

### 评估当前资源使用

```bash
# 使用 CloudWatch Container Insights
# 访问 EKS → Insights → Container Insights

# 使用 kubectl top
kubectl top nodes
kubectl top pods -A

# 使用 Prometheus 查询
# CPU 使用率
avg(rate(container_cpu_usage_seconds_total{pod=~"my-app-.*"}[5m])) by (pod)

# 内存使用率
avg(container_memory_working_set_bytes{pod=~"my-app-.*"}) by (pod)
```

### 实例类型选择指南

#### 基于 CPU 使用率

| 平均 CPU 使用率 | 建议操作 | 节省 |
|----------------|---------|------|
| < 20% | 降级实例类型 | 40-60% |
| 20-50% | 保持当前 | - |
| 50-80% | 当前合适 | - |
| > 80% | 升级实例类型 | - |

#### 实例类型对比

| 实例类型 | vCPU | 内存 (GiB) | 成本/小时 | 适用场景 |
|---------|------|-----------|----------|---------|
| t3.nano | 2 | 0.5 | $0.0042 | 微服务 |
| t3.micro | 2 | 1 | $0.0084 | 开发测试 |
| t3.small | 2 | 2 | $0.0168 | 轻量级应用 |
| t3.medium | 2 | 4 | $0.0336 | 标准应用 |
| t3.large | 2 | 8 | $0.0672 | 数据密集 |
| t3.xlarge | 4 | 16 | $0.1344 | 高性能 |
| m5.large | 2 | 8 | $0.096 | 通用计算 |
| m5.xlarge | 4 | 16 | $0.192 | 高吞吐 |
| c5.large | 2 | 4 | $0.085 | 计算密集 |

### 使用 Vertical Pod Autoscaler (VPA)

#### 安装 VPA

```bash
# 安装 VPA
kubectl apply -f https://raw.githubusercontent.com/kubernetes/autoscaler/master/vertical-pod-autoscaler/deploy/vpa-v0.14.0.yaml

# 验证安装
kubectl get pods -n kube-system | grep vpa
```

#### 创建 VPA

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: my-app-vpa
  namespace: default
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
    - containerName: "*"
      minAllowed:
        cpu: 100m
        memory: 100Mi
      maxAllowed:
        cpu: 2
        memory: 4Gi
      controlledResources: ["cpu", "memory"]
```

#### 查看 VPA 推荐

```bash
# 查看 VPA 推荐
kubectl describe vpa my-app-vpa

# 输出示例:
# Recommendation:
#   Container Recommendations:
#     Container: my-app
#     Lower Bound:
#       cpu: 100m
#       memory: 100Mi
#     Target:
#       cpu: 500m
#       memory: 512Mi
#     Upper Bound:
#       cpu: 2
#       memory: 4Gi
```

---

## 3. 自动缩放优化

### 概述

自动缩放确保集群根据负载动态调整，避免资源浪费。

### Horizontal Pod Autoscaler (HPA)

#### 创建 HPA

```bash
# 创建 HPA
kubectl autoscale deployment my-app \
  --cpu-percent=50 \
  --min=2 \
  --max=10 \
  --namespace default

# 使用 YAML
cat > hpa.yaml <<EOF
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-app-hpa
  namespace: default
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
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 70
EOF

kubectl apply -f hpa.yaml
```

### Cluster Autoscaler 配置

#### 安装和配置

```bash
# 安装 Cluster Autoscaler
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm repo update

helm install cluster-autoscaler autoscaler/cluster-autoscaler \
  --namespace kube-system \
  --set cloudProvider=aws \
  --set autoDiscovery.clusterName=my-cluster \
  --set awsRegion=us-east-1 \
  --set extraArgs.scale-down-unneeded-time=10m \
  --set extraArgs.scale-down-delay-after-add=10m \
  --set extraArgs.balance-similar-node-groups=true
```

#### 配置优先级

```bash
# 为节点组设置优先级
aws eks create-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name priority-high \
  --instance-types t3.large \
  --labels cluster-autoscaler.kubernetes.io/priority=10 \
  --tags cluster-autoscaler.kubernetes.io/priority=10

aws eks create-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name priority-low \
  --instance-types t3.medium \
  --labels cluster-autoscaler.kubernetes.io/priority=1 \
  --tags cluster-autoscaler.kubernetes.io/priority=1
```

### 节点组配置最佳实践

```yaml
# optimized-nodegroup.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-eks-cluster
  region: us-east-1

managedNodeGroups:
  - name: production-ng
    instanceType: t3.large
    minSize: 2
    maxSize: 10
    desiredSize: 3
    labels:
      role: production
    # 使用 gp3 而非 gp2（节省 20%）
    volumeSize: 20
    volumeType: gp3
    volumeEncrypted: true
```

---

## 4. Graviton 实例优化

### 概述

AWS Graviton 处理器（ARM64）可以节省 20-40% 的成本，同时提供更好的性能。

### Graviton 优势

| 特性 | x86_64 | Graviton (ARM64) |
|------|--------|-----------------|
| 成本 | 基准 | -20% ~ -40% |
| 性能 | 基准 | +10% ~ +40% |
| 能耗 | 基准 | -60% |
| 兼容性 | 全部 | 大部分 |

### 创建 Graviton 节点组

#### 使用 eksctl

```yaml
# graviton-nodegroup.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-eks-cluster
  region: us-east-1

managedNodeGroups:
  - name: graviton-ng
    instanceTypes:
      - m6g.medium
      - m6g.large
      - m6g.xlarge
    amiType: AL2_ARM_64
    minSize: 2
    maxSize: 10
    desiredSize: 3
    labels:
      arch: arm64
    tags:
      arch: arm64
```

```bash
# 创建 Graviton 节点组
eksctl create nodegroup -f graviton-nodegroup.yaml
```

#### 使用 AWS CLI

```bash
# 创建 Graviton 节点组
aws eks create-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name graviton-ng \
  --node-role arn:aws:iam::123456789012:role/eksNodeRole \
  --subnets subnet-aaa,subnet-bbb,subnet-ccc \
  --scaling-config minSize=2,maxSize=10,desiredSize=3 \
  --instance-types m6g.medium,m6g.large,m6g.xlarge \
  --ami-type AL2_ARM_64 \
  --labels arch=arm64
```

### 应用兼容性

#### 构建 ARM64 镜像

```dockerfile
# Dockerfile.arm64
FROM --platform=linux/arm64 nginx:latest

# 构建镜像
docker buildx build --platform linux/arm64 -t my-app:arm64 .

# 推送到 ECR
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app:arm64
```

#### 多架构镜像

```bash
# 构建多架构镜像
docker buildx create --use
docker buildx build --platform linux/amd64,linux/arm64 \
  -t 123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app:multi \
  --push .
```

#### 节点亲和性

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      nodeSelector:
        arch: arm64
      containers:
      - name: my-app
        image: 123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app:arm64
```

---

## 5. Fargate 优化

### 概述

Fargate 是无服务器容器运行方式，适合需要简化运维的场景。

### Fargate 成本对比

| 组件 | EC2 | Fargate |
|------|-----|---------|
| 节点管理 | 需要管理 | 无需管理 |
| CPU 成本 | $0.048/vCPU/hour | $0.040505/vCPU/hour |
| 内存成本 | $0.024/GiB/hour | $0.004445/GiB/hour |
| 最小运行成本 | ~$50/月 | ~$15/月 |
| 适用场景 | 持续工作负载 | 突发/不规律负载 |

### 创建 Fargate Profile

```bash
# 创建 Fargate Profile
aws eks create-fargate-profile \
  --cluster-name my-cluster \
  --fargate-profile-name my-profile \
  --pod-execution-role-arn arn:aws:iam::123456789012:role/eksFargateRole \
  --selectors namespace=default,labels=app=my-app \
  --subnets subnet-aaa,subnet-bbb,subnet-ccc
```

### Fargate 最佳实践

```yaml
# Fargate 优化的 Pod 配置
apiVersion: v1
kind: Pod
metadata:
  name: fargate-pod
  namespace: default
spec:
  nodeSelector:
    kubernetes.io/arch: arm64  # 使用 Graviton 节省成本
  containers:
  - name: my-app
    image: my-app:latest
    resources:
      requests:
        cpu: "256m"  # Fargate vCPU 最小 0.25
        memory: "512Mi"  # Fargate 内存最小 512Mi
      limits:
        cpu: "512m"
        memory: "1Gi"
    # 优化镜像大小（Fargate 拉取镜像更快）
    startupProbe:
      httpGet:
        path: /healthz
        port: 8080
      initialDelaySeconds: 5
      periodSeconds: 10
```

---

## 6. 存储优化

### EBS 卷优化

#### 使用 gp3 而非 gp2

| 特性 | gp2 | gp3 |
|------|-----|-----|
| 成本 | $0.08/GB/月 | $0.08/GB/月 |
| 基准 IOPS | 3/GB | 3,000 (免费) |
| 基准吞吐量 | 128 MiB/s/TB | 125 MiB/s (免费) |
| IOPS 成本 | 包含 | $0.005/IOPS |
| 吞吐量成本 | 包含 | $0.04/MiB/s |
| 节省 | - | 10-20% |

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: optimized-pvc
spec:
  storageClassName: gp3-optimized  # 使用 gp3
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 100Gi
```

```bash
# 创建 gp3 StorageClass
cat > gp3-sc.yaml <<EOF
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3-optimized
parameters:
  type: gp3
  iops: "3000"
  throughput: "125"
  encrypted: "true"
provisioner: kubernetes.io/aws-ebs
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Delete
EOF

kubectl apply -f gp3-sc.yaml
```

#### EBS 快照生命周期策略

```bash
# 创建快照生命周期策略
aws ec2 create-snapshot-lifecycle-policy \
  --policy-details '{
    "ResourceTypes": ["VOLUME"],
    "TargetTags": [
      {
        "Key": "Environment",
        "Value": "Production"
      }
    ],
    "Schedules": [
      {
        "Name": "DailySnapshots",
        "TagsToAdd": [
          {
            "Key": "Retention",
            "Value": "7Days"
          }
        ],
        "CreateRule": {
          "Interval": 24,
          "IntervalUnit": "HOURS",
          "Times": [
            "03:00"
          ]
        },
        "RetainRule": {
          "Count": 7
        }
      }
    ]
  }'
```

### EFS 优化

#### 使用 EFS Standard-IA

| 类型 | 成本/GB/月 | 适用场景 |
|------|-----------|---------|
| EFS Standard | $0.30 | 经常访问的数据 |
| EFS Standard-IA | $0.015 | 不经常访问的数据 |
| EFS One Zone | $0.16 | 单区域应用 |
| EFS One Zone-IA | $0.013 | 单区域不经常访问 |

```bash
# 创建 EFS 文件系统
FILE_SYSTEM_ID=$(aws efs create-file-system \
  --creation-token my-eks-efs \
  --performance-mode generalPurpose \
  --throughput-mode bursting \
  --tags Key=Name,Value=my-eks-efs \
  --query 'FileSystemId' --output text)

# 创建生命周期策略（30天后移到 IA）
aws efs put-lifecycle-configuration \
  --file-system-id $FILE_SYSTEM_ID \
  --lifecycle-policies '{"TransitionToIA":"AFTER_30_DAYS"}'
```

---

## 7. Load Balancer 优化

### ALB 优化

#### 使用 Network Load Balancer (NLB)

| 类型 | 成本 | 性能 | 适用场景 |
|------|------|------|---------|
| CLB (Classic) | $0.025/hour | 低 | 已弃用 |
| ALB | $0.025/hour | 中 | HTTP/HTTPS |
| NLB | $0.025/hour | 高 | TCP/UDP |

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"  # 使用 NLB
spec:
  type: LoadBalancer
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
```

#### 删除未使用的 Load Balancer

```bash
# 列出所有 Load Balancer
aws elb describe-load-balancers --query 'LoadBalancerDescriptions[*].LoadBalancerName'

# 删除未使用的 LB
aws elb delete-load-balancer --load-balancer-name <lb-name>
```

---

## 8. CloudWatch 优化

### 日志优化

#### 设置日志保留策略

```bash
# 设置日志保留策略（7天）
aws logs put-retention-policy \
  --log-group-name /aws/eks/my-cluster/application \
  --retention-in-days 7

# 设置不同的保留期
aws logs put-retention-policy \
  --log-group-name /aws/eks/my-cluster/cluster \
  --retention-in-days 30  # 控制平面日志保留更久

aws logs put-retention-policy \
  --log-group-name /aws/eks/my-cluster/application \
  --retention-in-days 7   # 应用日志保留较短
```

#### 使用 CloudWatch Logs Insights 过滤

```bash
# 创建指标过滤器（减少日志传输成本）
aws logs put-metric-filter \
  --log-group-name /aws/eks/my-cluster/application \
  --filter-name ErrorCount \
  --filter-pattern "[timestamp, request_id, level=ERROR, ...]" \
  --metric-transformations metricName=ErrorCount,metricNamespace=EKS,metricValue=1
```

### 指标优化

#### 使用 CloudWatch Agent 自定义指标

```yaml
# cwagent-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cwagentconfig
  namespace: amazon-cloudwatch
data:
  cwagentconfig.json: |
    {
      "agent": {
        "metrics_collection_interval": 60,
        "region": "us-east-1"
      },
      "metrics": {
        "namespace": "EKS/MyCluster",
        "metrics_collected": {
          "mem": {
            "measurement": [
              "mem_used_percent"
            ]
          },
          "cpu": {
            "measurement": [
              "cpu_usage_idle",
              "cpu_usage_iowait"
            ]
          }
        }
      }
    }
EOF

kubectl apply -f cwagent-config.yaml
```

---

## 9. 监控和报告

### 成本监控

#### 使用 Cost Explorer

```bash
# 启用 Cost Explorer
aws ce enable-cost-explorer

# 获取 EKS 成本报告
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --filter '{"Dimensions": {"Key": "SERVICE", "Values": ["Amazon EKS"]}}' \
  --group-by Type=DIMENSION,Key=USAGE_TYPE
```

#### 创建成本告警

```bash
# 创建每月成本告警
aws cloudwatch put-metric-alarm \
  --alarm-name EKSCostAlert \
  --alarm-description "Alert when EKS cost exceeds $500" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 21600 \
  --evaluation-periods 1 \
  --threshold 500 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=Currency,Value=USD \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:cost-alert-topic
```

### 成本优化检查清单

```bash
# 创建成本检查脚本
cat > cost-check.sh <<'EOF'
#!/bin/bash

CLUSTER_NAME=$1

echo "=== EKS Cost Optimization Checklist ==="
echo

# 1. 检查未使用的节点组
echo "1. Checking unused node groups..."
aws eks list-nodegroups --cluster-name $CLUSTER_NAME --output table
echo

# 2. 检查实例类型
echo "2. Checking instance types..."
aws eks describe-nodegroup --cluster-name $CLUSTER_NAME --nodegroup-name <ng-name> \
  --query 'nodegroup.instanceTypes'
echo

# 3. 检查节点数量
echo "3. Checking node count..."
kubectl get nodes --no-headers | wc -l
echo

# 4. 检查 Pod 资源使用
echo "4. Checking Pod resource usage..."
kubectl top pods -A --sort-by=cpu | head -20
echo

# 5. 检查未使用的 Load Balancer
echo "5. Checking unused load balancers..."
aws elb describe-load-balancers --query 'LoadBalancerDescriptions[?!Instances].[LoadBalancerName,DNSName]' \
  --output table
echo

echo "=== Check complete ==="
EOF

chmod +x cost-check.sh

# 运行检查
./cost-check.sh my-cluster
```

---

## 10. 成本优化最佳实践

### 立即可实施的优化

| 优化 | 难度 | 节省 | 优先级 |
|------|------|------|--------|
| 启用 gp3 | 低 | 10-20% | 高 |
| 设置日志保留策略 | 低 | 20-30% | 高 |
| 使用 Spot 实例 | 中 | 90% | 中 |
| 使用 Graviton | 中 | 20-40% | 中 |
| 启用自动缩放 | 中 | 30-50% | 高 |
| Right-Sizing | 高 | 20-40% | 高 |
| 使用 Fargate | 中 | 可变 | 中 |

### 成本优化路线图

#### 阶段 1: 快速获胜（1周）
1. ✅ 启用 gp3 存储
2. ✅ 设置日志保留策略
3. ✅ 启用自动缩放
4. ✅ 删除未使用的资源

#### 阶段 2: 中等优化（2-4周）
1. 🔄 迁移到 Spot 实例
2. 🔄 迁移到 Graviton
3. 🔄 实施 Right-Sizing
4. 🔄 优化 Load Balancer

#### 阶段 3: 高级优化（1-3个月）
1. 📋 实施成本监控
2. 📋 建立成本告警
3. 📋 优化网络传输
4. 📋 实施资源配额

### 常见错误

❌ **避免**:
1. 过度配置实例（过度分配）
2. 不使用自动缩放
3. 忽略日志和指标成本
4. 不定期审查资源使用
5. 不设置成本告警

✅ **推荐**:
1. 定期审查资源使用
2. 使用自动化工具（VPA, HPA）
3. 实施成本监控和告警
4. 使用成本估算工具
5. 建立成本优化文化

---

## 参考资源

### AWS 官方文档
- [EKS Cost Optimization](https://docs.aws.amazon.com/eks/latest/userguide/cost-optimization.html)
- [Spot Instances](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-spot-instances.html)
- [Graviton](https://aws.amazon.com/ec2/graviton/)
- [Cost Explorer](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/ce-using.html)

### 工具和服务
- [eksctl](https://eksctl.io/)
- [Cluster Autoscaler](https://github.com/kubernetes/autoscaler)
- [Karpenter](https://karpenter.sh/) - 高级自动缩放工具
- [Infracost](https://www.infracost.io/) - 基础设施成本估算

### 社区资源
- [AWS Well-Architected Framework - Cost Optimization](https://aws.amazon.com/architecture/well-architected/cost-optimization-pillar/)
- [Kubernetes Cost Management](https://kubernetes.io/docs/concepts/cluster-administration/system-metrics/)
- [EKS Spot最佳实践](https://github.com/aws-samples/eks-spot-workshop)