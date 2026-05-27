# Core Concepts — EKS

## What is AWS EKS

- **Purpose**: Elastic Kubernetes Service — managed Kubernetes control plane on AWS
- **Category**: Containers & Compute
- **Console**: https://console.aws.amazon.com/eks/home
- **Docs**: https://docs.aws.amazon.com/eks/

## EKS Architecture

| Component | Description | Managed By |
|-----------|-------------|------------|
| Control Plane | Kubernetes API Server, etcd, scheduler | AWS (fully managed) |
| Data Plane | Worker nodes that run pods | Customer or AWS (Fargate) |
| Worker Nodes | EC2 instances running pods | Customer (managed node groups) |
| Fargate | Serverless compute for pods | AWS (serverless) |

## Cluster Components

### Control Plane
| Component | Description |
|-----------|-------------|
| API Server | Kubernetes API endpoint |
| etcd | Distributed key-value store |
| Scheduler | Assigns pods to nodes |
| Controller Manager | Runs controllers |
| Cloud Controller | AWS integration |

### Data Plane Options
| Type | Description | Use Case |
|------|-------------|----------|
| Managed Node Group | EC2 instances managed by EKS | Standard workloads |
| Self-managed Nodes | EC2 instances you manage | Custom configurations |
| Fargate | Serverless pods | No node management |
| Bottlerocket Nodes | Minimal OS for containers | Security-focused |

## Node Group Types

| Type | Description | Pros | Cons |
|------|-------------|------|------|
| Managed Node Group | EKS manages lifecycle | Easy management, auto-healing | Less customization |
| Self-managed Nodes | Manual EC2 management | Full customization | More operational overhead |
| Fargate Profile | Serverless pods | No node management | Higher cost, limitations |
| Bottlerocket | Minimal container OS | Security, efficiency | Limited customization |

## EKS Add-ons

| Add-on | Description | Required |
|--------|-------------|----------|
| vpc-cni | AWS VPC CNI plugin | Yes |
| coredns | DNS service | Yes |
| kube-proxy | Network proxy | Yes |
| aws-ebs-csi-driver | EBS volume support | Optional |
| aws-efs-csi-driver | EFS volume support | Optional |

## Kubernetes Versions

| Version | Status | Release | EOL |
|---------|--------|---------|-----|
| 1.32 | Latest | 2025 Q1 | 2026 Q4 |
| 1.31 | Stable | 2024 Q3 | 2026 Q2 |
| 1.30 | Stable | 2024 Q2 | 2026 Q1 |
| 1.29 | Standard | 2024 Q1 | 2025 Q4 |
| 1.28 | Extended Support | 2023 Q3 | 2025 Q2 |
| 1.27 | Extended Support | 2023 Q2 | 2025 Q1 |
| 1.26 | Deprecated | 2023 Q1 | 2024 Q4 |

**Note**: EKS provides extended support for older versions at additional cost ($0.60/hour).

## Cluster Endpoints

| Endpoint Type | Description | Access |
|---------------|-------------|--------|
| Public Endpoint | Internet-accessible API | 0.0.0.0/0 or CIDRs |
| Private Endpoint | VPC-only API | VPC internal only |

**Recommended**: Enable both, restrict public CIDRs to known IPs.

## IAM Integration

### IAM Roles for Service Accounts (IRSA)
| Component | Purpose |
|-----------|---------|
| OIDC Provider | Link IAM to Kubernetes SA |
| Service Account | Kubernetes pod identity |
| IAM Role | AWS permissions for pods |

### Required IAM Roles
| Role | Purpose |
|------|---------|
| Cluster Role | EKS control plane permissions |
| Node Role | Worker node permissions |
| Fargate Role | Fargate pod execution |
| Add-on Roles | Add-on service accounts |

## Networking

### VPC Requirements
| Requirement | Description |
|-------------|-------------|
| Subnets | Minimum 2 AZs, 3 recommended |
| IP Addresses | Enough IPs for nodes and pods |
| VPC CNI | Pods get VPC IP addresses |
| Security Groups | Control plane and node SGs |

### Service IP Range
| CIDR | Description | Conflict Check |
|------|-------------|----------------|
| 10.100.0.0/16 | Default service CIDR | Check VPC CIDR |
| Custom | User-defined | Avoid VPC overlap |

## Quotas

| Quota | Default | Adjustable |
|-------|---------|------------|
| Clusters per Region | 100 | Yes |
| Managed Node Groups per Cluster | 30 | Yes |
| Nodes per Managed Node Group | 100 | Yes |
| Fargate Profiles per Cluster | 10 | No |
| Pods per Fargate Profile | Selectors define | — |
| Control Plane Logs | 5 types | — |

## Fargate Profile Selectors

| Selector Field | Description |
|----------------|-------------|
| namespace | Kubernetes namespace |
| labels | Pod labels (match) |

**Matching**: Pods matching namespace AND labels run on Fargate.

## Node Group Scaling

| Parameter | Description |
|-----------|-------------|
| minSize | Minimum nodes |
| maxSize | Maximum nodes |
| desiredSize | Target node count |

**Auto-scaling**: Kubernetes Cluster Autoscaler adjusts desiredSize.

## Node Group Capacity Types

| Type | Description | Cost |
|------|-------------|------|
| ON_DEMAND | Standard EC2 | Higher |
| SPOT | Spot instances | Lower (may be interrupted) |

## Node Group AMI Types

| AMI Type | Architecture | Use Case |
|----------|--------------|----------|
| AL2_x86_64 | x86_64 | Standard |
| AL2_x86_64_GPU | x86_64 with GPU | ML/GPU workloads |
| AL2_ARM_64 | ARM64 | Graviton processors |
| CUSTOM | Custom launch template | Specialized configs |
| BOTTLEROCKET_x86_64 | Bottlerocket | Security-focused |
| BOTTLEROCKET_ARM_64 | Bottlerocket ARM | Security + efficiency |

## Storage Options

| Storage | Driver | Use Case |
|---------|--------|----------|
| EBS | aws-ebs-csi-driver | Block storage |
| EFS | aws-efs-csi-driver | Shared file storage |
| S3 | Not CSI | Object storage (external) |
| Instance Store | Default | Temporary storage |

## Load Balancer Integration

| LB Type | Controller | Annotations |
|---------|------------|-------------|
| ALB | AWS Load Balancer Controller | `kubernetes.io/ingress.class: alb` |
| NLB | AWS Load Balancer Controller | `service.beta.kubernetes.io/aws-load-balancer-type: nlb` |
| CLB | kube-proxy (legacy) | Deprecated |

## Monitoring & Logging

### Control Plane Logs
| Log Type | Description |
|----------|-------------|
| api | API server logs |
| audit | Audit logs |
| authenticator | IAM authenticator logs |
| controllerManager | Controller manager logs |
| scheduler | Scheduler logs |

### Metrics
| Source | Metrics |
|--------|---------|
| CloudWatch | EKS metrics, container insights |
| Prometheus | Application metrics |
| Kubernetes Metrics Server | Resource metrics |

## Security Features

| Feature | Description |
|---------|-------------|
| Encryption at Rest | KMS encryption for secrets |
| Secrets Encryption | Envelope encryption with KMS |
| RBAC | Kubernetes RBAC |
| IAM Authentication | IAM users/roles to Kubernetes |
| Pod Security Standards | PSP/PSS policies |
| Network Policies | Pod network isolation |

## Cluster Access Modes

| Mode | Description |
|------|-------------|
| API_AND_CONFIG_MAP | IAM + ConfigMap (traditional) |
| API | IAM only (recommended) |
| CONFIG_MAP | ConfigMap only (deprecated) |

## Best Practices

### Cluster Creation
- Use 3+ AZs for high availability
- Enable both public and private endpoints
- Restrict public endpoint CIDRs
- Enable control plane logging
- Enable secrets encryption

### Node Management
- Use managed node groups for simplicity
- Set appropriate min/max/desired sizes
- Use Spot for cost optimization (with fallback)
- Enable node auto-recovery

### Security
- Use IRSA for pod permissions
- Enable secrets encryption
- Use private endpoints when possible
- Implement network policies

### Networking
- Ensure enough VPC IPs
- Use VPC CNI with custom networking if needed
- Deploy AWS Load Balancer Controller

### Upgrades
- Upgrade incrementally (1.28 → 1.29 → 1.30)
- Test upgrades on dev first
- Update addons after cluster upgrade

## Pricing

| Component | Cost |
|-----------|------|
| Control Plane | $0.10/hour per cluster |
| Worker Nodes | EC2 pricing |
| Fargate | $0.042/vCPU/hour + $0.0096/GB/hour |
| Extended Support | $0.60/hour (after standard support) |
| Add-ons | No additional EKS cost |

## Related Services

| Service | Integration |
|---------|-------------|
| EC2 | Worker nodes |
| VPC | Cluster networking |
| IAM | Authentication, IRSA |
| CloudWatch | Logging, metrics |
| ECR | Container images |
| ELB | Service exposure |
| KMS | Secrets encryption |
| Fargate | Serverless pods |
| Auto Scaling | Node scaling |

## Advanced Concepts

### Cluster Autoscaler

**Purpose**: Automatically adjusts the number of nodes in a node group based on pod resource requests.

**How It Works**:
```
Pod Pending → Scheduler cannot find node → CA detects → Scale up node group → Pod scheduled
Node idle → CA detects → Scale down node group → Node terminated
```

**Key Configuration**:
| Parameter | Description | Default |
|-----------|-------------|---------|
| scale-down-delay-after-add | Wait time after scale-up before scale-down | 10m |
| scale-down-unneeded-time | How long node must be unneeded | 10m |
| scale-down-utilization-threshold | CPU/memory threshold for scale-down | 0.5 |
| max-graceful-termination-sec | Max wait time for pod termination | 600 |

**Deployment**: Install via Helm or kubectl. Requires IAM permissions (AutoScalingFullAccess).

### Pod Disruption Budgets (PDB)

**Purpose**: Ensure minimum number of pods available during voluntary disruptions (node maintenance, updates).

**Types**:
| Type | Description | Example |
|------|-------------|---------|
| minAvailable | Minimum pods that must be available | `minAvailable: 2` |
| minAvailable % | Minimum percentage of pods | `minAvailable: 50%` |

**Use Case**: Protect critical applications from downtime during node maintenance.

### Resource Quotas

**Purpose**: Limit aggregate resource consumption per namespace.

**Example**:
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: compute-resources
  namespace: dev
spec:
  hard:
    requests.cpu: "4"
    requests.memory: 8Gi
    limits.cpu: "8"
    limits.memory: 16Gi
    persistentvolumeclaims: 4
```

**Benefits**:
- Prevent namespace resource exhaustion
- Fair resource allocation
- Cost control

### Limit Ranges

**Purpose**: Set default and limit constraints for pod resources per namespace.

**Example**:
```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: resource-limits
  namespace: dev
spec:
  limits:
  - type: Container
    default:
      cpu: 500m
      memory: 512Mi
    defaultRequest:
      cpu: 250m
      memory: 256Mi
    max:
      cpu: "2"
      memory: 2Gi
```

### Network Policies

**Purpose**: Control network traffic between pods at the IP address level.

**Default Policy**: Kubernetes allows all traffic. Network policies restrict it.

**Key Concepts**:
| Concept | Description |
|---------|-------------|
| Ingress | Incoming traffic to pod |
| Egress | Outgoing traffic from pod |
| Namespace isolation | Control traffic between namespaces |
| Label-based rules | Match pods using labels |

**Requirement**: Network plugin with support (Calico, Cilium, Weave Net).

### Pod Security Standards (PSS)

**Purpose**: Enforce security standards at the pod level (replaces deprecated Pod Security Policies).

**Levels**:
| Level | Description | Use Case |
|-------|-------------|----------|
| privileged | Unrestricted, allows everything | Not recommended |
| baseline | Minimal security restrictions | Standard workloads |
| restricted | Strict security controls | High-security applications |

**Features**:
- Prevent privileged containers
- Block host path mounts
- Restrict capabilities
- Enforce non-root users

### EKS Access Entries

**Purpose**: Native IAM-based access control for EKS clusters (replaces aws-auth ConfigMap).

**Benefits**:
- No ConfigMap management
- Native AWS integration
- Better security
- Supports IAM users, roles, and groups

**Components**:
| Component | Description |
|-----------|-------------|
| Access Entry | Mapping of IAM principal to cluster |
| Access Policy | Kubernetes RBAC permissions |
| Access Scope | Cluster-wide or namespace-specific |

**Predefined Policies**:
- `AmazonEKSClusterAdminPolicy` - Full cluster access
- `AmazonEKSEditPolicy` - Edit permissions
- `AmazonEKSViewPolicy` - Read-only access

### Horizontal Pod Autoscaler (HPA)

**Purpose**: Automatically scale the number of pods based on CPU/memory or custom metrics.

**How It Works**:
```
High CPU Usage → HPA detects → Increase replicas → Load distributed → CPU decreases
Low CPU Usage → HPA detects → Decrease replicas → Cost savings
```

**Example**:
```yaml
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
```

### Vertical Pod Autoscaler (VPA)

**Purpose**: Automatically adjust pod CPU and memory resource requests.

**Benefits**:
- Right-size resources
- Reduce costs
- Improve performance

**Modes**:
| Mode | Description |
|------|-------------|
| Off | VPA does nothing |
| Initial | Sets resource requests on pod creation only |
| Auto | Updates resource requests during pod lifecycle |
| Recreate | Recreates pods when resource requests change |

## Resource Management Best Practices

### Cluster Autoscaler + HPA + VPA

```
User Load → HPA scales pods → More pods → Cluster Autoscaler scales nodes
VPA adjusts pod resources → Better resource utilization
```

**Configuration Tips**:
1. Set appropriate HPA metrics (CPU, memory, custom)
2. Configure Cluster Autoscaler with priority expander
3. Use VPA in "Auto" mode for stateless apps
4. Combine with PDB to protect critical services

### Cost Optimization

| Strategy | Description | Savings |
|----------|-------------|---------|
| Spot instances | Use Spot for interruptible workloads | Up to 90% |
| Right-sizing | Use VPA to optimize resources | 20-30% |
| Cluster autoscaler | Scale down idle nodes | 30-50% |
| Multiple instance types | Use cost-effective types | 10-20% |

### Resource Limits

| Resource | Default Limit | Recommended |
|----------|--------------|-------------|
| Pods per node | 110 | 50-70 |
| Nodes per cluster | 100 | 50-100 |
| Services per cluster | 5000 | 1000-2000 |
| Namespaces per cluster | 1000 | 50-100 |