# Cluster Autoscaler — EKS

## 概述

Cluster Autoscaler 是 Kubernetes 的自动扩缩容组件，可以自动调整 EKS 节点组的规模以满足 Pod 的资源需求。

## 工作原理

```
Pod Pending → 调度失败 → CA 检测 → 扩容节点组 → Pod 运行
Node 空闲 → CA 检测 → 缩容节点组 → 节点删除
```

## 安装 Cluster Autoscaler

### 使用 Helm 安装

```bash
# 添加 Helm 仓库
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm repo update

# 安装 Cluster Autoscaler
helm install cluster-autoscaler autoscaler/cluster-autoscaler \
  --namespace kube-system \
  --set cloudProvider=aws \
  --set autoDiscovery.clusterName=my-cluster \
  --set awsRegion=us-east-1 \
  --set rbac.create=true \
  --set rbac.serviceAccount.create=true \
  --set rbac.serviceAccount.name=cluster-autoscaler \
  --set image.tag=v9.30.0

# 验证安装
kubectl get deployment -n kube-system cluster-autoscaler
kubectl logs -n kubesystem deployment/cluster-autoscaler
```

### 使用 kubectl 安装（YAML）

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/autoscaler/master/cluster-autoscaler/cloudprovider/aws/examples/cluster-autoscaler-autodiscover.yaml

# 或者使用自定义配置
kubectl apply -f - <<EOF
apiVersion: v1
kind: ServiceAccount
metadata:
  name: cluster-autoscaler
  namespace: kube-system
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/ClusterAutoscalerRole
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: cluster-autoscaler
rules:
  - apiGroups: [""]
    resources: ["events", "endpoints"]
    verbs: ["create", "patch"]
  - apiGroups: [""]
    resources: ["pods/eviction"]
    verbs: ["create"]
  - apiGroups: [""]
    resources: ["pods/status"]
    verbs: ["update"]
  - apiGroups: [""]
    resources: ["endpoints"]
    resourceNames: ["cluster-autoscaler"]
    verbs: ["get", "update"]
  - apiGroups: [""]
    resources: ["nodes"]
    verbs: ["watch", "list", "get", "update"]
  - apiGroups: [""]
    resources:
      - "pods"
      - "services"
      - "replicationcontrollers"
      - "persistentvolumeclaims"
      - "persistentvolumes"
    verbs: ["watch", "list", "get"]
  - apiGroups: ["extensions"]
    resources: ["replicasets", "daemonsets"]
    verbs: ["watch", "list", "get"]
  - apiGroups: ["policy"]
    resources: ["poddisruptionbudgets"]
    verbs: ["watch", "list"]
  - apiGroups: ["apps"]
    resources: ["statefulsets", "replicasets", "daemonsets"]
    verbs: ["watch", "list", "get"]
  - apiGroups: ["storage.k8s.io"]
    resources: ["storageclasses", "csinodes"]
    verbs: ["watch", "list", "get"]
  - apiGroups: ["batch", "extensions"]
    resources: ["jobs"]
    verbs: ["watch", "list", "get"]
  - apiGroups: ["coordination.k8s.io"]
    resources: ["leases"]
    verbs: ["watch", "list", "get", "update", "create"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: cluster-autoscaler
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-autoscaler
subjects:
  - kind: ServiceAccount
    name: cluster-autoscaler
    namespace: kube-system
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cluster-autoscaler
  namespace: kube-system
  labels:
    app: cluster-autoscaler
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cluster-autoscaler
  template:
    metadata:
      labels:
        app: cluster-autoscaler
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8085"
    spec:
      serviceAccountName: cluster-autoscaler
      containers:
        - image: registry.k8s.io/autoscaling/cluster-autoscaler:v9.30.0
          name: cluster-autoscaler
          resources:
            limits:
              cpu: 100m
              memory: 300Mi
            requests:
              cpu: 100m
              memory: 300Mi
          command:
            - ./cluster-autoscaler
            - --v=4
            - --stderrthreshold=info
            - --cloud-provider=aws
            - --skip-nodes-with-local-storage=false
            - --expander=priority
            - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/my-cluster
            - --balance-similar-node-groups
            - --skip-nodes-with-system-pods=false
          env:
            - name: AWS_REGION
              value: us-east-1
          volumeMounts:
            - name: ssl-cert
              mountPath: /etc/ssl/certs/ca-certificates.crt
              readOnly: true
      volumes:
        - name: ssl-cert
          hostPath:
            path: /etc/ssl/certs/ca-certificates.crt
      terminationGracePeriodSeconds: 30
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchExpressions:
                  - key: app
                    operator: In
                    values:
                      - cluster-autoscaler
              topologyKey: "kubernetes.io/hostname"
EOF
```

## IAM 权限

### 创建 IAM Role（IRSA）

```bash
# 创建 IAM Role
cat <<'EOF' > trust-policy.json
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
          "oidc.eks.us-east-1.amazonaws.com/id/${OIDC_ID}:sub": "system:serviceaccount:kube-system:cluster-autoscaler"
        }
      }
    }
  ]
}
EOF

aws iam create-role \
  --role-name ClusterAutoscalerRole \
  --assume-role-policy-document file://trust-policy.json

# 附加策略
aws iam attach-role-policy \
  --role-name ClusterAutoscalerRole \
  --policy-arn arn:aws:iam::aws:policy/AutoScalingFullAccess

# 更新 ServiceAccount
kubectl annotate serviceaccount cluster-autoscaler \
  -n kube-system \
  eks.amazonaws.com/role-arn=arn:aws:iam::123456789012:role/ClusterAutoscalerRole
```

### IAM 策略（AWS 托管）

| 策略 | 用途 |
|------|------|
| `AutoScalingFullAccess` | 管理自动扩缩容组（推荐） |
| `AmazonEKSClusterPolicy` | EKS 集群权限 |

## Node Group 配置

### 自动发现标签

```bash
# 创建节点组时添加自动发现标签
aws eks create-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --node-role arn:aws:iam::123456789012:role/eksNodeRole \
  --subnets subnet-aaa,subnet-bbb \
  --scaling-config minSize=1,maxSize=10,desiredSize=2 \
  --instance-types t3.medium \
  --labels k8s.io/cluster-autoscaler/enabled=true,k8s.io/cluster-autoscaler/my-cluster=true \
  --tags k8s.io/cluster-autoscaler/enabled=true,k8s.io/cluster-autoscaler/my-cluster=true
```

### 扩展器策略

```bash
# priority 扩展器（基于优先级）
kubectl set env deployment/cluster-autoscaler -n kube-system -- \
  --expander=priority

# least-waste 扩展器（最小资源浪费）
kubectl set env deployment/cluster-autoscaler -n kube-system -- \
  --expander=least-waste

# most-pods 扩展器（最多 Pod 数量）
kubectl set env deployment/cluster-autoscaler -n kube-system -- \
  --expander=most-pods

# random 扩展器（随机选择）
kubectl set env deployment/cluster-autoscaler -n kube-system -- \
  --expander=random
```

### 节点组优先级

```bash
# 为节点组设置优先级（数字越大优先级越高）
aws eks create-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name priority-high \
  --labels k8s.io/cluster-autoscaler/enabled=true,k8s.io/cluster-autoscaler/my-cluster=true,cluster-autoscaler.kubernetes.io/safe-to-evict=true \
  --tags cluster-autoscaler.kubernetes.io/priority=10

aws eks create-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name priority-low \
  --labels k8s.io/cluster-autoscaler/enabled=true,k8s.io/cluster-autoscaler/my-cluster=true,cluster-autoscaler.kubernetes.io/safe-to-evict=true \
  --tags cluster-autoscaler.kubernetes.io/priority=1
```

## Pod Disruption Budgets

### 保护关键 Pod

```bash
# 创建 PDB，确保至少有 2 个 Pod 运行
kubectl apply -f - <<EOF
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: my-app-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: my-app
EOF

# 或者使用百分比
kubectl apply -f - <<EOF
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: my-app-pdb
spec:
  minAvailable: 50%
  selector:
    matchLabels:
      app: my-app
EOF
```

### 查看 PDB

```bash
kubectl get pdb
kubectl describe pdb my-app-pdb
```

## 监控和日志

### 查看日志

```bash
kubectl logs -n kube-system deployment/cluster-autoscaler -f

# 查看扩容事件
kubectl get events -n kube-system --field-selector reason=TriggeredScaleUp

# 查看缩容事件
kubectl get events -n kube-system --field-selector reason=TriggeredScaleDown
```

### 监控指标

```bash
# Cluster Autoscaler 暴露 Prometheus 指标
kubectl port-forward -n kube-system deployment/cluster-autoscaler 8085:8085

# 访问指标
curl http://localhost:8085/metrics
```

### 关键指标

| 指标 | 描述 |
|------|------|
| `cluster_autoscaler_cluster_safe_to_autoscale` | 集群是否可以自动扩缩容 |
| `cluster_autoscaler_cluster_current_nodes` | 当前节点数量 |
| `cluster_autoscaler_cluster_desired_nodes` | 期望节点数量 |
| `cluster_autoscaler_cluster_max_nodes` | 最大节点数量 |
| `cluster_autoscaler_cluster_min_nodes` | 最小节点数量 |
| `cluster_autoscaler_unschedulable_pods_count` | 无法调度的 Pod 数量 |
| `cluster_autoscaler_scaled_up_nodes_total` | 扩容的节点总数 |
| `cluster_autoscaler_scaled_down_nodes_total` | 缩容的节点总数 |

## 高级配置

### 跳过节点

```bash
# 标记节点为不可缩容
kubectl annotate node my-node cluster-autoscaler.kubernetes.io/safe-to-evict=false

# 标记 Pod 为不可驱逐
kubectl annotate pod my-pod cluster-autoscaler.kubernetes.io/safe-to-evict=false
```

### Scale Down Delay

```bash
# 设置缩容延迟（避免频繁缩容）
kubectl set env deployment/cluster-autoscaler -n kube-system -- \
  --scale-down-delay-after-add=10m \
  --scale-down-delay-after-delete=10m \
  --scale-down-delay-after-failure=5m \
  --scale-down-unneeded-time=10m
```

### Scale Down Utilization Threshold

```bash
# 设置缩容阈值（CPU 和内存利用率）
kubectl set env deployment/cluster-autoscaler -n kube-system -- \
  --scale-down-utilization-threshold=0.5
```

### Max Graceful Termination Seconds

```bash
# 设置优雅终止时间
kubectl set env deployment/cluster-autoscaler -n kube-system -- \
  --max-graceful-termination-sec=600
```

## 故障排查

### Pod 持续 Pending

```bash
# 检查 Pod 事件
kubectl describe pod <pod-name>

# 检查 Cluster Autoscaler 日志
kubectl logs -n kube-system deployment/cluster-autoscaler | grep -i pending

# 检查节点组是否已达最大值
aws eks describe-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --query 'nodegroup.scalingConfig'
```

### 节点无法缩容

```bash
# 检查节点上运行的 Pod
kubectl get pods -o wide --field-selector spec.nodeName=<node-name>

# 检查是否有 PDB 阻止
kubectl get pdb -o jsonpath='{.items[*].spec.minAvailable}' | xargs

# 检查 Pod 是否有禁止驱逐的注解
kubectl get pod <pod-name> -o jsonpath='{.metadata.annotations}'
```

### Cluster Autoscaler 无法启动

```bash
# 检查 IAM 权限
aws iam get-role --role-name ClusterAutoscalerRole

# 检查 ServiceAccount
kubectl get sa cluster-autoscaler -n kube-system -o yaml

# 检查日志
kubectl logs -n kube-system deployment/cluster-autoscaler --previous
```

## 最佳实践

### 扩容策略

1. **多节点组策略**
   - 不同实例类型的节点组
   - Spot 和 On-Demand 混合
   - 优先级配置

2. **合理的阈值**
   - minSize：至少 2 个节点（高可用）
   - maxSize：根据负载需求
   - desiredSize：平衡成本和性能

3. **Pod 资源请求**
   - 为所有 Pod 设置合理的 requests
   - 使用 limits 限制资源使用
   - 避免过度分配

### 缩容策略

1. **保护关键应用**
   - 使用 PDB 保护关键 Pod
   - 标记关键节点为不可驱逐

2. **设置合理延迟**
   - 避免频繁扩缩容
   - 根据应用特性调整

3. **监控缩容行为**
   - 定期检查 Cluster Autoscaler 日志
   - 监控 Pod 调度情况

### 安全性

1. **最小权限原则**
   - 只授予必要的 IAM 权限
   - 使用 IRSA 而非实例配置文件

2. **资源限制**
   - 设置 Pod 资源限制
   - 防止资源耗尽

3. **审计和日志**
   - 启用 Cluster Autoscaler 日志
   - 监控扩缩容事件

## 示例场景

### 场景 1：Web 应用自动扩缩容

```bash
# 部署应用
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
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
      - name: web
        image: nginx:latest
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 1Gi
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: web-app
EOF

# 设置 HPA（Horizontal Pod Autoscaler）
kubectl autoscale deployment web-app --cpu-percent=50 --min=3 --max=10
```

### 场景 2：批处理作业使用 Spot 实例

```bash
# 创建 Spot 节点组
aws eks create-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name spot-batch \
  --node-role arn:aws:iam::123456789012:role/eksNodeRole \
  --subnets subnet-aaa,subnet-bbb \
  --scaling-config minSize=0,maxSize=50,desiredSize=5 \
  --capacity-type SPOT \
  --instance-types m5.large,m5a.large,m5d.large \
  --labels capacity-type=spot,node-type=batch \
  --taints key=spot,value=true,effect=NoSchedule

# 部署批处理作业
kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: batch-job
spec:
  template:
    spec:
      tolerations:
      - key: spot
        operator: Equal
        value: "true"
        effect: NoSchedule
      nodeSelector:
        capacity-type: spot
        node-type: batch
      containers:
      - name: batch
        image: python:3.9
        command: ["python", "-c", "print('Batch job completed')"]
        resources:
          requests:
            cpu: 1000m
            memory: 2Gi
      restartPolicy: Never
EOF
```

## 参考文档

- [Cluster Autoscaler Documentation](https://github.com/kubernetes/autoscaler/tree/master/cluster-autoscaler)
- [AWS EKS Cluster Autoscaler](https://docs.aws.amazon.com/eks/latest/userguide/cluster-autoscaler.html)
- [Kubernetes PDB](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)