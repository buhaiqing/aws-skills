# Performance Optimization — EKS

## 概述

EKS 性能优化涉及从基础设施层到应用层的全面优化，确保 Kubernetes 集群和应用程序以最佳性能运行。

## 性能优化层次

```
┌─────────────────────────────────────────┐
│         应用层优化                      │
│  (代码优化、缓存、连接池)               │
├─────────────────────────────────────────┤
│         Kubernetes 层优化                │
│  (资源请求、调度策略、H/VPA)            │
├─────────────────────────────────────────┤
│         节点层优化                       │
│  (实例类型、内核优化、NUMA)             │
├─────────────────────────────────────────┤
│         网络层优化                       │
│  (VPC CNI、网络策略、DNS)               │
├─────────────────────────────────────────┤
│         存储层优化                       │
│  (EBS、EFS、IO 优化)                    │
└─────────────────────────────────────────┘
```

---

## 1. 节点层性能优化

### 实例类型选择

#### CPU 密集型工作负载

| 实例类型 | vCPU | 内存 (GiB) | 网络带宽 | 适用场景 |
|---------|------|-----------|---------|---------|
| c5.large | 2 | 4 | Up to 10 Gbps | 计算密集 |
| c5.xlarge | 4 | 8 | Up to 10 Gbps | 高性能计算 |
| c5.2xlarge | 8 | 16 | Up to 10 Gbps | 批处理 |

#### 内存密集型工作负载

| 实例类型 | vCPU | 内存 (GiB) | 网络带宽 | 适用场景 |
|---------|------|-----------|---------|---------|
| r5.large | 2 | 16 | Up to 10 Gbps | 数据库 |
| r5.xlarge | 4 | 32 | Up to 10 Gbps | 缓存 |
| r5.2xlarge | 8 | 64 | Up to 10 Gbps | 大数据 |

#### 网络密集型工作负载

| 实例类型 | vCPU | 内存 (GiB) | 网络带宽 | 适用场景 |
|---------|------|-----------|---------|---------|
| c5n.large | 2 | 4 | 25 Gbps | 高吞吐 |
| c5n.xlarge | 4 | 8 | 50 Gbps | 视频流 |
| c5n.18xlarge | 72 | 144 | 100 Gbps | 超高吞吐 |

#### GPU 工作负载

| 实例类型 | vCPU | 内存 (GiB) | GPU | 适用场景 |
|---------|------|-----------|-----|---------|
| g4dn.xlarge | 4 | 16 | 1 T4 | 推理 |
| g4dn.2xlarge | 8 | 32 | 1 T4 | 训练 |
| g4dn.8xlarge | 32 | 128 | 1 T4 | 深度学习 |

### 实例配置优化

#### 启用增强网络

```yaml
launch_template:
  name: enhanced-networking
  instance_type: c5n.large
  network_interfaces:
    - device_index: 0
      interface_type: ena
      delete_on_termination: true
```

#### CPU 优化

```bash
# 创建 CPU 优化的实例类型
aws ec2 run-instances \
  --image-id ami-xxx \
  --count 1 \
  --instance-type c5n.large \
  --cpu-options 'CoreCount=2,ThreadsPerCore=1'
```

#### 内存优化

```yaml
nodegroup:
  instance_types:
    - r5.large
  labels:
    memory-optimized: "true"
```

---

## 2. Kubernetes 层性能优化

### 资源请求和限制

#### 最佳实践

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: optimized-pod
spec:
  containers:
  - name: app
    image: my-app:latest
    resources:
      requests:
        cpu: "500m"      # 基于实际使用设置
        memory: "512Mi"
      limits:
        cpu: "1000m"     # 限制为请求的 2 倍
        memory: "1Gi"     # 限制为请求的 2 倍
```

#### 资源请求优化策略

| 使用率 | 请求设置 | 限制设置 |
|--------|---------|---------|
| CPU < 30% | 降低 50% | 保持 2x |
| CPU 30-70% | 保持 | 保持 2x |
| CPU > 70% | 增加 50% | 增加 50% |

### Pod 优先级和抢占

#### Pod Priority Class

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000
globalDefault: false
description: "High priority pods"
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: low-priority
value: 100
globalDefault: true
description: "Low priority pods"
```

#### 使用优先级

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: critical-pod
spec:
  priorityClassName: high-priority
  containers:
  - name: app
    image: my-app:latest
```

### 调度优化

#### 节点亲和性

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: optimized-pod
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: memory-optimized
            operator: In
            values:
            - "true"
```

#### Pod 反亲和性

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: distributed-pod
spec:
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchLabels:
            app: my-app
        topologyKey: "kubernetes.io/hostname"
```

#### 拓扑分布约束

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: distributed-pod
spec:
  topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: "topology.kubernetes.io/zone"
    whenUnsatisfiable: ScheduleAnyway
    labelSelector:
      matchLabels:
        app: my-app
```

### 水平和垂直自动扩缩容

#### HPA 配置

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: optimized-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 30
```

#### VPA 配置

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: optimized-vpa
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
        memory: 128Mi
      maxAllowed:
        cpu: 4
        memory: 8Gi
      controlledResources: ["cpu", "memory"]
```

### 容器优化

#### 多阶段构建

```dockerfile
# 第一阶段：构建
FROM golang:1.21 AS builder
WORKDIR /app
COPY . .
RUN CGO_ENABLED=0 go build -o myapp

# 第二阶段：运行
FROM scratch
COPY --from=builder /app/myapp /myapp
CMD ["/myapp"]
```

#### 镜像优化

```bash
# 使用多架构镜像
docker buildx build --platform linux/amd64,linux/arm64 \
  -t myapp:multi-arch --push .

# 使用 .dockerignore
cat > .dockerignore <<EOF
node_modules
npm-debug.log
.git
*.md
EOF

# 优化镜像大小
docker build --squash -t myapp:optimized .
```

---

## 3. 网络层性能优化

### VPC CNI 优化

#### 自定义网络

```yaml
# 启用 VPC CNI 自定义网络
apiVersion: v1
kind: ConfigMap
metadata:
  name: aws-node
  namespace: kube-system
data:
  AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG: "true"
  ENI_CONFIG_LABEL_DEF: "topology.kubernetes.io/zone"
```

#### 创建 ENI Config

```yaml
apiVersion: v1
kind: ENIConfig
metadata:
  name: us-east-1a
  labels:
    topology.kubernetes.io/zone: us-east-1a
spec:
  subnet: subnet-aaa
  securityGroups:
    - sg-eks-node
```

#### 优化 VPC CNI 参数

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: aws-node
  namespace: kube-system
data:
  ENABLE_V4_IPV6_DUALSTACK: "false"
  ENABLE_IPv6: "false"
  WARM_ENI_TARGET: "2"
  WARM_PREFIX_TARGET: "1"
```

### DNS 优化

#### CoreDNS 调优

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: coredns
  namespace: kube-system
data:
  Corefile: |
    .:53 {
        errors
        health {
          lameduck 5s
        }
        ready
        kubernetes cluster.local in-addr.arpa ip6.arpa {
          pods insecure
          fallthrough in-addr.arpa ip6.arpa
          ttl 30
        }
        prometheus :9153
        forward . /etc/resolv.conf {
          max_concurrent 1000
        }
        cache 30
        loop
        reload
        loadbalance
    }
```

#### CoreDNS HPA

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: coredns-hpa
  namespace: kube-system
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: coredns
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 80
```

### 网络策略优化

#### 允许 DNS 查询

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: default
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
```

#### 优化网络策略

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: optimized-network-policy
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: my-app
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - namespaceSelector: {}
    - podSelector:
        matchLabels:
          app: backend
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - namespaceSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
```

### Load Balancer 优化

#### NLB 配置

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
    service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "true"
    service.beta.kubernetes.io/aws-load-balancer-scheme: "internal"
spec:
  type: LoadBalancer
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
    protocol: TCP
```

#### ALB 配置

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-ingress
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/healthcheck-path: /health
    alb.ingress.kubernetes.io/healthcheck-interval-seconds: "30"
    alb.ingress.kubernetes.io/healthcheck-timeout-seconds: "5"
    alb.ingress.kubernetes.io/healthy-threshold-count: "2"
    alb.ingress.kubernetes.io/unhealthy-threshold-count: "2"
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

---

## 4. 存储层性能优化

### EBS 优化

#### gp3 配置

```yaml
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
allowVolumeExpansion: true
```

#### io2 配置

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: io2-optimized
parameters:
  type: io2
  iops: "10000"
  encrypted: "true"
provisioner: kubernetes.io/aws-ebs
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Delete
```

#### EBS 优化示例

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: high-performance-pvc
spec:
  storageClassName: io2-optimized
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 100Gi
```

### EFS 优化

#### EFS 配置

```bash
# 创建 EFS 文件系统
aws efs create-file-system \
  --creation-token my-eks-efs \
  --performance-mode generalPurpose \
  --throughput-mode bursting \
  --tags Key=Name,Value=my-eks-efs

# 设置吞吐量模式（高吞吐量场景）
aws efs update-file-system \
  --file-system-id fs-xxx \
  --throughput-mode provisioned \
  --provisioned-throughput-in-mibps 100
```

#### EFS StorageClass

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-xxx
  directoryPerms: "700"
  gidRangeStart: "1000"
  gidRangeEnd: "2000"
```

### 存储访问模式优化

#### ReadWriteMany vs ReadWriteOnce

| 访问模式 | 使用场景 | 存储类型 |
|---------|---------|---------|
| ReadWriteOnce | 单 Pod 写入 | EBS |
| ReadOnlyMany | 多 Pod 读取 | EFS |
| ReadWriteMany | 多 Pod 读写 | EFS |

#### 存储缓存

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: cached-storage
spec:
  containers:
  - name: app
    image: my-app:latest
    volumeMounts:
    - name: cache
      mountPath: /cache
  volumes:
  - name: cache
    emptyDir:
      medium: Memory
      sizeLimit: 1Gi
```

---

## 5. 应用层性能优化

### 代码优化

#### 连接池配置

```go
// Go 连接池优化示例
db.SetMaxOpenConns(100)
db.SetMaxIdleConns(10)
db.SetConnMaxLifetime(time.Hour)
```

```python
# Python 连接池优化示例
from sqlalchemy import create_engine
engine = create_engine(
    'postgresql://user:pass@localhost/db',
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=3600
)
```

#### 缓存策略

```yaml
# 使用 Redis 缓存
apiVersion: v1
kind: Deployment
metadata:
  name: cached-app
spec:
  template:
    spec:
      containers:
      - name: app
        image: my-app:latest
        env:
        - name: REDIS_HOST
          value: "redis-service"
        - name: REDIS_PORT
          value: "6379"
        - name: CACHE_TTL
          value: "300"
```

#### 异步处理

```yaml
# 使用消息队列异步处理
apiVersion: v1
kind: Deployment
metadata:
  name: async-worker
spec:
  template:
    spec:
      containers:
      - name: worker
        image: my-worker:latest
        env:
        - name: SQS_QUEUE_URL
          value: "https://sqs.us-east-1.amazonaws.com/123456789012/my-queue"
```

### Kubernetes 配置优化

#### Liveness 和 Readiness 探针

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: optimized-pod
spec:
  containers:
  - name: app
    image: my-app:latest
    livenessProbe:
      httpGet:
        path: /healthz
        port: 8080
      initialDelaySeconds: 30
      periodSeconds: 10
      timeoutSeconds: 5
      successThreshold: 1
      failureThreshold: 3
    readinessProbe:
      httpGet:
        path: /ready
        port: 8080
      initialDelaySeconds: 5
      periodSeconds: 5
      timeoutSeconds: 3
      successThreshold: 1
      failureThreshold: 3
```

#### 启动探针

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: slow-startup-pod
spec:
  containers:
  - name: app
    image: my-app:latest
    startupProbe:
      httpGet:
        path: /startup
        port: 8080
      initialDelaySeconds: 0
      periodSeconds: 5
      timeoutSeconds: 3
      successThreshold: 1
      failureThreshold: 30
    readinessProbe:
      httpGet:
        path: /ready
        port: 8080
      initialDelaySeconds: 5
      periodSeconds: 5
```

### 并发控制

#### 并发限制

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  MAX_CONCURRENT_REQUESTS: "100"
  CONNECTION_POOL_SIZE: "50"
```

#### 限流配置

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: rate-limiter
data:
  RATE_LIMIT: "1000"
  RATE_WINDOW: "60"
```

---

## 6. 监控和分析

### 性能指标

#### 关键指标

| 指标 | 阈值 | 操作 |
|------|------|------|
| CPU 使用率 | < 70% | 正常 |
| CPU 使用率 | > 90% | 扩容 |
| 内存使用率 | < 80% | 正常 |
| 内存使用率 | > 95% | 扩容 |
| Pod 重启次数 | < 5 | 正常 |
| Pod 重启次数 | > 10 | 调查 |
| 响应时间 | < 1s | 正常 |
| 响应时间 | > 5s | 优化 |

#### Prometheus 查询

```promql
# CPU 使用率
sum(rate(container_cpu_usage_seconds_total{pod=~"my-app-.*"}[5m])) by (pod)

# 内存使用率
sum(container_memory_working_set_bytes{pod=~"my-app-.*"}) by (pod) / sum(container_spec_memory_limit_bytes{pod=~"my-app-.*"}) by (pod)

# Pod 重启次数
increase(kube_pod_container_status_restarts_total{pod=~"my-app-.*"}[1h])

# 响应时间
rate(http_request_duration_seconds_sum{pod=~"my-app-.*"}[5m]) / rate(http_request_duration_seconds_count{pod=~"my-app-.*"}[5m])
```

### 性能分析工具

#### kubectl top

```bash
# 查看 Pod 资源使用
kubectl top pods -A

# 查看节点资源使用
kubectl top nodes
```

#### Kubernetes Metrics Server

```bash
# 安装 Metrics Server
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# 验证
kubectl get pods -n kube-system | grep metrics-server
```

---

## 7. 性能优化最佳实践

### 立即可实施的优化

| 优化 | 难度 | 性能提升 | 优先级 |
|------|------|---------|--------|
| 启用 gp3 | 低 | +20% | 高 |
| 调整资源请求 | 中 | +30% | 高 |
| 启用 HPA | 中 | +50% | 高 |
| 优化探针 | 低 | +10% | 中 |
| 使用 Graviton | 中 | +20% | 中 |
| CoreDNS 调优 | 低 | +15% | 中 |
| 启用 VPA | 高 | +25% | 中 |
| 网络策略优化 | 中 | +10% | 低 |

### 性能优化路线图

#### 阶段 1: 快速获胜（1周）
1. ✅ 启用 gp3 存储
2. ✅ 优化资源请求和限制
3. ✅ 启用 HPA
4. ✅ 优化探针配置

#### 阶段 2: 中等优化（2-4周）
1. 🔄 使用 Graviton 实例
2. 🔄 CoreDNS 调优
3. 🔄 VPC CNI 优化
4. 🔄 存储优化

#### 阶段 3: 高级优化（1-3个月）
1. 📋 实施性能监控
2. 📋 应用层优化
3. 📋 网络优化
4. 📋 建立性能基准

### 常见性能问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| Pod 启动慢 | 镜像大、拉取慢 | 多阶段构建、本地缓存 |
| 高 CPU 使用率 | 资源请求不足、代码效率低 | 调整请求、代码优化 |
| 内存泄漏 | 应用 bug、配置错误 | 修复 bug、调整限制 |
| 网络延迟 | 跨 AZ、网络策略 | 同 AZ 部署、优化策略 |
| I/O 瓶颈 | 存储类型选择错误 | 使用 gp3/io2 |
| DNS 解析慢 | CoreDNS 不足 | 扩容 CoreDNS |

---

## 8. 性能测试

### 负载测试

#### 使用 Apache Bench

```bash
# 安装 Apache Bench
brew install ab  # macOS
# 或
apt-get install apache2-utils  # Ubuntu

# 负载测试
ab -n 1000 -c 10 http://my-service.default.svc.cluster.local:8080/

# 输出示例:
# Requests per second:    123.45 [#/sec] (mean)
# Time per request:       81.046 [ms] (mean)
```

#### 使用 wrk

```bash
# 安装 wrk
brew install wrk  # macOS
# 或从 GitHub 编译

# 负载测试
wrk -t12 -c400 -d30s http://my-service.default.svc.cluster.local:8080/

# 输出示例:
# Requests/sec:  12345.67
# Transfer/sec:   12.34MB
```

#### 使用 k6

```bash
# 安装 k6
brew install k6  # macOS

# 创建测试脚本
cat > load-test.js <<EOF
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '2m', target: 100 },
    { duration: '5m', target: 100 },
    { duration: '2m', target: 0 },
  ],
};

export default function () {
  let res = http.get('http://my-service.default.svc.cluster.local:8080/');
  check(res, {
    'status was 200': (r) => r.status == 200,
    'response time <500ms': (r) => r.timings.duration < 500,
  });
  sleep(1);
}
EOF

# 运行测试
k6 run load-test.js
```

### 压力测试

#### 使用 vegeta

```bash
# 安装 vegeta
brew install vegeta  # macOS

# 创建目标
echo "GET http://my-service.default.svc.cluster.local:8080/" | \
  vegeta attack -rate=100 -duration=30s | \
  tee results.bin | \
  vegeta report

# 生成报告
vegeta report -type=json results.bin > report.json
```

---

## 参考资源

### AWS 官方文档
- [EKS Performance Optimization](https://docs.aws.amazon.com/eks/latest/userguide/performance.html)
- [VPC CNI Performance](https://docs.aws.amazon.com/eks/latest/userguide/cni-performance.html)
- [EBS Performance](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-volume-types.html)

### 工具和服务
- [Prometheus](https://prometheus.io/)
- [Grafana](https://grafana.com/)
- [Kubernetes Metrics Server](https://github.com/kubernetes-sigs/metrics-server)
- [Velero](https://velero.io/)

### 社区资源
- [Kubernetes Performance Tuning](https://kubernetes.io/docs/tasks/debug/debug-application/resource-usage-monitoring/)
- [AWS Well-Architected Framework - Performance Efficiency](https://aws.amazon.com/architecture/well-architected/performance-efficiency-pillar/)
- [CNCF Performance Best Practices](https://github.com/cncf/performance-working-group)