# Security Best Practices — EKS

## 概述

EKS 安全性涉及多层防护：集群安全、节点安全、网络安全、应用安全和数据安全。

## EKS 访问控制

### EKS Access Entries（推荐）

EKS Access Entries 是推荐的访问控制方式，替代传统的 `aws-auth ConfigMap`。

#### 创建和管理访问条目

```bash
# 创建访问条目（IAM 用户）
aws eks create-access-entry \
  --cluster-name my-cluster \
  --principal-arn arn:aws:iam::123456789012:user/admin \
  --type STANDARD

# 创建访问条目（IAM 角色）
aws eks create-access-entry \
  --cluster-name my-cluster \
  --principal-arn arn:aws:iam::123456789012:role/eks-developer \
  --type STANDARD

# 列出所有访问条目
aws eks list-access-entries --cluster-name my-cluster

# 描述访问条目
aws eks describe-access-entry \
  --cluster-name my-cluster \
  --principal-arn arn:aws:iam::123456789012:user/admin
```

#### 关联访问策略

```bash
# 关联集群管理员策略
aws eks associate-access-policy \
  --cluster-name my-cluster \
  --principal-arn arn:aws:iam::123456789012:user/admin \
  --policy-arn arn:aws:eks:us-east-1:123456789012:access-policy/AmazonEKSClusterAdminPolicy \
  --access-scope type=cluster

# 关联编辑策略
aws eks associate-access-policy \
  --cluster-name my-cluster \
  --principal-arn arn:aws:iam::123456789012:user/developer \
  --policy-arn arn:aws:eks:us-east-1:123456789012:access-policy/AmazonEKSEditPolicy \
  --access-scope type=cluster

# 关联到特定命名空间
aws eks associate-access-policy \
  --cluster-name my-cluster \
  --principal-arn arn:aws:iam::123456789012:user/dev-team \
  --policy-arn arn:aws:eks:us-east-1:123456789012:access-policy/AmazonEKSViewPolicy \
  --access-scope type=namespace,namespaces=dev
```

#### 预定义访问策略

| 策略名称 | 描述 | 适用场景 |
|---------|------|---------|
| AmazonEKSClusterAdminPolicy | 集群管理员权限 | 完全控制集群 |
| AmazonEKSEditPolicy | 编辑权限 | 修改大部分资源 |
| AmazonEKSViewPolicy | 只读权限 | 查看资源 |
| AmazonEKSEditFargateProfilePolicy | 管理 Fargate 配置文件 | Fargate 管理 |
| AmazonEKSDeleteClusterPolicy | 删除集群权限 | 集群删除 |

### 传统 aws-auth ConfigMap（已弃用）

```bash
# 查看 ConfigMap
kubectl get configmap aws-auth -n kube-system -o yaml

# 更新 ConfigMap（不推荐，使用 Access Entries）
kubectl patch configmap aws-auth -n kube-system --type merge \
  -p '{"data":{"mapRoles":"- rolearn: arn:aws:iam::123456789012:role/eks-admin\n  username: admin\n  groups:\n  - system:masters\n- rolearn: arn:aws:iam::123456789012:role/eks-node-role\n  username: system:node:{{EC2PrivateDNSName}}\n  groups:\n  - system:bootstrappers\n  - system:nodes"}}'
```

## 集群端点安全

### Private Only 集群（推荐）

```bash
# 创建仅私有端点的集群
aws eks create-cluster \
  --name private-eks-cluster \
  --version 1.30 \
  --role-arn arn:aws:iam::123456789012:role/eksClusterRole \
  --resources-vpc-config \
      subnetIds=subnet-private-aaa,subnet-private-bbb,subnet-private-ccc,securityGroupIds=sg-xxx,endpointPrivateAccess=true,endpointPublicAccess=false \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator"],"enabled":true}]}'

# 验证端点配置
aws eks describe-cluster \
  --name private-eks-cluster \
  --query 'cluster.resourcesVpcConfig.endpointPublicAccess,cluster.resourcesVpcConfig.endpointPrivateAccess'
```

### 混合端点配置

```bash
# 创建混合端点集群（公共+私有）
aws eks create-cluster \
  --name mixed-eks-cluster \
  --version 1.30 \
  --role-arn arn:aws:iam::123456789012:role/eksClusterRole \
  --resources-vpc-config \
      subnetIds=subnet-public-aaa,subnet-private-bbb,securityGroupIds=sg-xxx,endpointPublicAccess=true,endpointPrivateAccess=true,publicAccessCidrs=10.0.0.0/8

# 验证 CIDR 限制
aws eks describe-cluster \
  --name mixed-eks-cluster \
  --query 'cluster.resourcesVpcConfig.publicAccessCidrs'
```

### 从私有集群访问

```bash
# 通过堡垒机或 VPN 访问
aws eks update-kubeconfig \
  --name private-eks-cluster \
  --region us-east-1 \
  --role-arn arn:aws:iam::123456789012:role/BastionHostRole

# 验证连接
kubectl cluster-info
kubectl get nodes
```

## Secrets 加密

### 启用 Secrets 加密

```bash
# 创建 KMS 密钥
aws kms create-key \
  --description "EKS cluster secrets encryption key" \
  --tags TagKey=Name,TagValue=eks-secrets-key

# 获取密钥 ARN
KEY_ARN=$(aws kms describe-key --key-id <key-id> --query 'KeyMetadata.Arn' --output text)

# 创建启用加密的集群
aws eks create-cluster \
  --name secure-eks-cluster \
  --version 1.30 \
  --role-arn arn:aws:iam::123456789012:role/eksClusterRole \
  --resources-vpc-config subnetIds=subnet-aaa,subnet-bbb,securityGroupIds=sg-xxx \
  --encryption-config resources=secretEnvelopes,provider={keyArn=$KEY_ARN}

# 为现有集群启用加密
aws eks associate-encryption-config \
  --cluster-name my-cluster \
  --encryption-config resources=secretEnvelopes,provider={keyArn=$KEY_ARN}
```

### 使用 AWS Secrets Manager CSI Driver

```bash
# 安装 Secrets Manager CSI Driver
kubectl apply -f https://raw.githubusercontent.com/aws/secrets-store-csi-driver-provider-aws/main/deployment/aws-provider-installer.yaml

# 创建 SecretProviderClass
kubectl apply -f - <<EOF
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: aws-secrets
spec:
  provider: aws
  parameters:
    objects: |
      - objectName: "my-secret"
        objectType: "secretsmanager"
    objects: |
      - objectName: "arn:aws:secretsmanager:us-east-1:123456789012:secret:my-secret"
        objectType: "secretsmanager"
  secretObjects:
  - secretName: my-secret
    type: Opaque
    data:
    - objectName: my-secret
      key: password
EOF

# 在 Pod 中使用
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
spec:
  containers:
  - name: my-container
    image: nginx
    volumeMounts:
    - name: secrets-store-inline
      mountPath: "/mnt/secrets-store"
      readOnly: true
  volumes:
  - name: secrets-store-inline
    csi:
      driver: secrets-store.csi.k8s.io
      readOnly: true
      volumeAttributes:
        secretProviderClass: "aws-secrets"
EOF
```

## Pod Security Standards

### 启用 Pod Security Admission

```bash
# 创建 Pod Security Admission 配置
kubectl label ns default \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/audit=restricted \
  pod-security.kubernetes.io/warn=restricted

# 创建命名空间时设置
kubectl create namespace secure-ns \
  --overwrite=true \
  --dry-run=client \
  -o yaml | kubectl apply -f -

# 查看策略状态
kubectl describe namespace default | grep -A 10 "Labels:"
```

### Pod Security 策略级别

| 策略级别 | 描述 | 适用场景 |
|---------|------|---------|
| privileged | 无限制 | 不推荐生产环境 |
| baseline | 基本安全 | 标准工作负载 |
| restricted | 严格安全 | 高安全要求 |

### 自定义 Pod Security Policy

```bash
# 创建 Pod Security Policy（已弃用，使用 PSS）
kubectl apply -f - <<EOF
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: restricted
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  hostNetwork: false
  hostIPC: false
  hostPID: false
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'MustRunAs'
    ranges:
      - min: 1
        max: 65535
  supplementalGroups:
    rule: 'MustRunAs'
    ranges:
      - min: 1
        max: 65535
  readOnlyRootFilesystem: false
EOF
```

## Network Policies

### 安装 CNI 网络策略支持

```bash
# 安装 Calico（支持网络策略）
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.26.1/manifests/calico.yaml

# 验证安装
kubectl get pods -n kube-system | grep calico
```

### 创建网络策略

```bash
# 默认拒绝所有入站流量
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: default
spec:
  podSelector: {}
  policyTypes:
  - Ingress
EOF

# 允许同一命名空间内的 Pod 通信
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-same-namespace
  namespace: default
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector: {}
EOF

# 允许特定命名空间访问
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-frontend
  namespace: backend
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: frontend
    ports:
    - protocol: TCP
      port: 8080
EOF

# 允许出站流量到特定命名空间
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-to-database
  namespace: frontend
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: database
    ports:
    - protocol: TCP
      port: 5432
EOF
```

### 查看网络策略

```bash
# 列出所有网络策略
kubectl get networkpolicies --all-namespaces

# 描述网络策略
kubectl describe networkpolicy default-deny-ingress -n default

# 测试网络策略
kubectl run test-pod --image=busybox --rm -it --restart=Never -- wget -O- http://backend-service:8080
```

## IAM Roles for Service Accounts (IRSA)

### 启用 OIDC 提供者

```bash
# 获取集群 OIDC 提供者 URL
OIDC_URL=$(aws eks describe-cluster \
  --name my-cluster \
  --query 'cluster.identity.oidc.issuer' \
  --output text | cut -d'/' -f3-)

# 创建 OIDC 提供者
aws iam create-open-id-connect-provider \
  --url https://$OIDC_URL \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list $(openssl s_client -servername oidc.eks.$(echo $OIDC_URL | cut -d'.' -f3-).amazonaws.com -showcerts -connect oidc.eks.$(echo $OIDC_URL | cut -d'.' -f3-).amazonaws.com:443 2>/dev/null </dev/null | openssl x509 -fingerprint -noout -in /dev/stdin | cut -d'=' -f2)
```

### 创建 IAM 角色和策略

```bash
# 创建信任策略
cat <<EOF > trust-policy.json
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

# 创建 IAM 角色
aws iam create-role \
  --role-name MyServiceAccountRole \
  --assume-role-policy-document file://trust-policy.json

# 附加策略
aws iam attach-role-policy \
  --role-name MyServiceAccountRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
```

### 创建 ServiceAccount

```bash
# 创建带有 IAM 角色的 ServiceAccount
kubectl create serviceaccount my-service-account -n my-namespace

kubectl annotate serviceaccount my-service-account \
  -n my-namespace \
  eks.amazonaws.com/role-arn=arn:aws:iam::123456789012:role/MyServiceAccountRole

# 验证
kubectl describe serviceaccount my-service-account -n my-namespace
```

### 在 Pod 中使用

```bash
# 创建使用 ServiceAccount 的 Pod
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
  namespace: my-namespace
spec:
  serviceAccountName: my-service-account
  containers:
  - name: my-container
    image: amazon/aws-cli:latest
    command: ["aws", "s3", "ls"]
EOF
```

## 安全组配置

### 集群安全组

```bash
# 创建集群安全组
SG_ID=$(aws ec2 create-security-group \
  --group-name eks-cluster-sg \
  --description "EKS cluster security group" \
  --vpc-id vpc-xxx \
  --query 'GroupId' --output text)

# 允许节点访问控制平面
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 443 \
  --cidr 10.0.0.0/16

# 限制公共访问（如果使用公共端点）
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 443 \
  --cidr 10.0.0.0/8
```

### 节点安全组

```bash
# 创建节点安全组
NODE_SG_ID=$(aws ec2 create-security-group \
  --group-name eks-node-sg \
  --description "EKS node security group" \
  --vpc-id vpc-xxx \
  --query 'GroupId' --output text)

# 允许集群控制平面访问节点
aws ec2 authorize-security-group-ingress \
  --group-id $NODE_SG_ID \
  --protocol tcp \
  --port 1025-65535 \
  --source-group $SG_ID

# 允许 Pod 间通信
aws ec2 authorize-security-group-ingress \
  --group-id $NODE_SG_ID \
  --protocol -1 \
  --source-group $NODE_SG_ID
```

## 加密 EBS 卷

```bash
# 创建加密的 EBS 卷
aws ec2 create-volume \
  --availability-zone us-east-1a \
  --size 100 \
  --volume-type gp3 \
  --encrypted \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:key/key-id

# 在 Pod 中使用加密卷
kubectl apply -f - <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: encrypted-pvc
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: gp3-encrypted
  resources:
    requests:
      storage: 100Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
spec:
  containers:
  - name: my-container
    image: nginx
    volumeMounts:
    - mountPath: /data
      name: encrypted-volume
  volumes:
  - name: encrypted-volume
    persistentVolumeClaim:
      claimName: encrypted-pvc
EOF
```

## 审计和合规

### 启用控制平面日志

```bash
# 启用所有日志类型
aws eks update-cluster-config \
  --name my-cluster \
  --logging '{
    "clusterLogging": [
      {
        "types": ["api", "audit", "authenticator", "controllerManager", "scheduler"],
        "enabled": true
      }
    ]
  }'

# 验证日志配置
aws eks describe-cluster --name my-cluster --query 'cluster.logging'
```

### CloudTrail 记录

```bash
# 创建 CloudTrail 跟踪
aws cloudtrail create-trail \
  --name eks-trail \
  --s3-bucket-name my-cloudtrail-bucket \
  --include-global-service-events \
  --is-multi-region-trail

# 启用日志文件验证
aws cloudtrail update-trail \
  --name eks-trail \
  --enable-log-file-validation

# 启用加密
aws cloudtrail update-trail \
  --name eks-trail \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:key/key-id
```

### Config Rules

```bash
# 创建 Config 规则
aws configservice put-config-rule \
  --config-rule-name eks-cluster-encryption \
  --source '{
    "Owner": "AWS",
    "SourceIdentifier": "EKS_CLUSTER_ENCRYPTION_ENABLED",
    "SourceDetails": [
      {
        "EventSource": "aws.config",
        "MessageType": "ConfigurationItemChangeNotification"
      }
    ]
  }' \
  --maximum-execution-frequency "One_Hour"

# 创建 Config 规则检查公共访问
aws configservice put-config-rule \
  --config-rule-name eks-cluster-public-access \
  --source '{
    "Owner": "AWS",
    "SourceIdentifier": "EKS_CLUSTER_PUBLIC_ACCESS_DISABLED",
    "SourceDetails": [
      {
        "EventSource": "aws.config",
        "MessageType": "ScheduledNotification"
      }
    ]
  }' \
  --maximum-execution-frequency "Six_Hours"
```

## 安全扫描

### 使用 Trivy 扫描镜像

```bash
# 安装 Trivy
brew install trivy

# 扫描镜像
trivy image nginx:latest

# 扫描本地镜像
docker build -t my-app:latest .
trivy image my-app:latest

# CI/CD 集成
trivy image --severity HIGH,CRITICAL --exit-code 1 my-app:latest
```

### 使用 kube-bench

```bash
# 安装 kube-bench
kubectl apply -f https://raw.githubusercontent.com/aquasecurity/kube-bench/main/job.yaml

# 查看结果
kubectl logs job/kube-bench
```

### 使用 Falco

```bash
# 安装 Falco
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm repo update

helm install falco falcosecurity/falco \
  --namespace falco \
  --set falco.jsonOutput=true

# 查看事件
kubectl logs -l app=falco -n falco -f
```

## 安全最佳实践总结

### 集群创建

1. 使用 3 个以上的可用区
2. 启用私有端点
3. 限制公共端点访问
4. 启用 Secrets 加密
5. 启用所有控制平面日志

### 访问控制

1. 使用 EKS Access Entries（而非 aws-auth ConfigMap）
2. 遵循最小权限原则
3. 定期审查 IAM 权限
4. 使用 IRSA 为 Pod 分配权限
5. 启用 MFA

### 网络安全

1. 使用 Network Policies 隔离命名空间
2. 限制安全组规则
3. 使用私有子网部署节点
4. 启用 VPC 流日志
5. 使用 Ingress Controller 管理入站流量

### 数据安全

1. 启用 Secrets 加密
2. 使用 AWS Secrets Manager 或 Parameter Store
3. 加密 EBS 卷
4. 使用 TLS 加密通信
5. 定期轮换密钥和证书

### 容器安全

1. 扫描镜像漏洞
2. 使用最小化基础镜像
3. 避免以 root 用户运行容器
4. 使用只读文件系统
5. 限制容器资源

### 监控和审计

1. 启用所有日志类型
2. 使用 CloudTrail 记录 API 调用
3. 配置安全告警
4. 定期审计集群配置
5. 使用 CIS 基准检查

## 参考文档

- [EKS Security Best Practices](https://docs.aws.amazon.com/eks/latest/userguide/security-best-practices.html)
- [EKS Access Entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [Kubernetes Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [CIS Kubernetes Benchmark](https://www.cisecurity.org/benchmark/kubernetes)