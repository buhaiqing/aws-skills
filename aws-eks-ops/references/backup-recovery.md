# Backup and Recovery — EKS

## 概述

备份和恢复是 Kubernetes 集群运维的关键环节，确保在意外情况下能够快速恢复服务和数据。

## 备份策略

### 备份层次

```
┌─────────────────────────────────────────┐
│         应用数据备份                    │
│  (数据库、对象存储、配置)               │
├─────────────────────────────────────────┤
│         Kubernetes 资源备份              │
│  (Deployment、Service、ConfigMap)       │
├─────────────────────────────────────────┤
│         etcd 备份                       │
│  (Kubernetes 集群状态)                  │
├─────────────────────────────────────────┤
│         基础设施备份                     │
│  (VPC、子网、安全组)                    │
└─────────────────────────────────────────┘
```

### 备份频率

| 数据类型 | 备份频率 | 保留期 | RPO | RTO |
|---------|---------|--------|-----|-----|
| 应用数据 | 每小时 | 7 天 | 1 小时 | 15 分钟 |
| Kubernetes 资源 | 每次 | 30 天 | 实时 | 5 分钟 |
| etcd | 每小时 | 7 天 | 1 小时 | 30 分钟 |
| 基础设施 | 每天 | 30 天 | 24 小时 | 2 小时 |

---

## 1. 应用数据备份

### 数据库备份

#### RDS 自动备份

```bash
# 创建 RDS 实例时启用自动备份
aws rds create-db-instance \
  --db-instance-identifier mydb \
  --db-instance-class db.t3.medium \
  --engine mysql \
  --master-username admin \
  --master-user-password SecurePassword123! \
  --allocated-storage 20 \
  --backup-retention-period 7 \
  --preferred-backup-window 03:00-04:00 \
  --multi-az \
  --region us-east-1
```

#### RDS 手动快照

```bash
# 创建手动快照
aws rds create-db-snapshot \
  --db-instance-identifier mydb \
  --db-snapshot-identifier mydb-snapshot-$(date +%Y%m%d%H%M%S) \
  --region us-east-1

# 恢复快照
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier mydb-restored \
  --db-snapshot-identifier mydb-snapshot-20240127120000 \
  --db-instance-class db.t3.medium \
  --region us-east-1
```

#### DynamoDB 备份

```bash
# 创建按需备份
aws dynamodb create-backup \
  --table-name Users \
  --backup-name Users-backup-$(date +%Y%m%d)

# 列出备份
aws dynamodb list-backups --table-name Users

# 恢复备份
aws dynamodb restore-table-from-backup \
  --target-table-name Users-restored \
  --backup-arn arn:aws:dynamodb:us-east-1:123456789012:table/Users/backup/arn:aws:dynamodb:us-east-1:123456789012:table/Users/backup/0123456789-abcdef

# 启用时间点恢复 (PITR)
aws dynamodb update-continuous-backups \
  --table-name Users \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
```

### ECR 镜像备份

#### 镜像生命周期策略

```bash
# 创建 ECR 生命周期策略
aws ecr put-lifecycle-policy \
  --repository-name my-app \
  --policy-content '{
    "rules": [
      {
        "rulePriority": 1,
        "description": "Keep last 10 images",
        "selection": {
          "tagStatus": "tagged",
          "tagPrefixList": ["v"],
          "countType": "imageCountMoreThan",
          "countNumber": 10
        },
        "action": {
          "type": "expire"
        }
      },
      {
        "rulePriority": 2,
        "description": "Delete untagged images older than 7 days",
        "selection": {
          "tagStatus": "untagged",
          "countType": "sinceImagePushed",
          "countUnit": "days",
          "countNumber": 7
        },
        "action": {
          "type": "expire"
        }
      }
    ]
  }'
```

#### 镜像扫描和备份

```bash
# 扫描镜像漏洞
aws ecr start-image-scan \
  --repository-name my-app \
  --image-id sha256:abc123...

# 查看扫描结果
aws ecr describe-image-scan-findings \
  --repository-name my-app \
  --image-id sha256:abc123...
```

### S3 数据备份

#### 跨区域复制

```bash
# 创建跨区域复制规则
aws s3api put-bucket-replication \
  --bucket source-bucket \
  --replication-configuration '{
    "Role": "arn:aws:iam::123456789012:role/s3-replication-role",
    "Rules": [
      {
        "Id": "BackupRule",
        "Priority": 1,
        "Status": "Enabled",
        "Prefix": "",
        "Destination": {
          "Bucket": "arn:aws:s3:::destination-bucket",
          "ReplicationTime": {
            "Status": "Enabled",
            "Time": {
              "Minutes": 15
            }
          }
        }
      }
    ]
  }' \
  --region us-east-1

# 启用版本控制
aws s3api put-bucket-versioning \
  --bucket source-bucket \
  --versioning-configuration Status=Enabled
```

#### S3 生命周期策略

```bash
# 创建生命周期策略
aws s3api put-bucket-lifecycle-configuration \
  --bucket my-app-data \
  --lifecycle-configuration '{
    "Rules": [
      {
        "ID": "BackupRule",
        "Status": "Enabled",
        "Prefix": "",
        "Transitions": [
          {
            "Days": 30,
            "StorageClass": "STANDARD_IA"
          },
          {
            "Days": 90,
            "StorageClass": "GLACIER"
          }
        ],
        "Expiration": {
          "Days": 365
        }
      }
    ]
  }'
```

---

## 2. Kubernetes 资源备份

### 使用 Velero

#### 安装 Velero

```bash
# 下载 Velero
wget https://github.com/vmware-tanzu/velero/releases/download/v1.13.0/velero-v1.13.0-linux-amd64.tar.gz
tar -xvf velero-v1.13.0-linux-amd64.tar.gz
sudo mv velero-v1.13.0-linux-amd64/velero /usr/local/bin/

# 创建 S3 存储桶
aws s3api create-bucket \
  --bucket velero-backups \
  --region us-east-1

# 创建 IAM 角色
cat > velero-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeVolumes",
        "ec2:DescribeSnapshots",
        "ec2:CreateTags",
        "ec2:CreateVolume",
        "ec2:DeleteSnapshot"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:PutObject",
        "s3:ListBucket",
        "s3:GetBucketVersioning",
        "s3:PutBucketVersioning"
      ],
      "Resource": [
        "arn:aws:s3:::velero-backups/*",
        "arn:aws:s3:::velero-backups"
      ]
    }
  ]
}
EOF

aws iam create-role \
  --role-name VeleroRole \
  --assume-role-policy-document file://velero-trust-policy.json

aws iam put-role-policy \
  --role-name VeleroRole \
  --policy-name VeleroPolicy \
  --policy-document file://velero-policy.json

# 安装 Velero
velero install \
  --provider aws \
  --plugins velero/velero-plugin-for-aws:v1.8.0 \
  --bucket velero-backups \
  --secret-file ./credentials-velero \
  --backup-location-config region=us-east-1 \
  --use-volume-snapshots=true \
  --snapshot-location-config region=us-east-1
```

#### 创建备份

```bash
# 备份整个集群
velero backup create full-backup-$(date +%Y%m%d) \
  --include-cluster-resources=true \
  --wait

# 备份特定命名空间
velero backup create production-backup \
  --include-namespaces=production \
  --wait

# 备份特定资源
velero backup create deployment-backup \
  --include-namespaces=default \
  --selector app=my-app \
  --wait

# 定时备份
velero schedule create daily-backup \
  --schedule="0 3 * * *" \
  --include-namespaces=production \
  --ttl=720h0m0s
```

#### 恢复备份

```bash
# 列出所有备份
velero backup get

# 查看备份详情
velero backup describe full-backup-20240127

# 恢复整个集群
velero restore create full-restore \
  --from-backup full-backup-20240127 \
  --wait

# 恢复到新命名空间
velero restore create production-restore \
  --from-backup production-backup \
  --namespace-mappings default:restored-default \
  --wait

# 恢复特定资源
velero restore create app-restore \
  --from-backup deployment-backup \
  --include-resources=deployments,services
```

### 使用 ArgoCD 备份

#### ArgoCD 配置

```yaml
# ArgoCD ApplicationSet 用于备份
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: backup-applications
  namespace: argocd
spec:
  generators:
  - git:
      repoURL: https://github.com/yourorg/your-apps
      revision: main
      directories:
      - path: k8s/*
  template:
    metadata:
      name: '{{path.basename}}'
    spec:
      project: default
      source:
        repoURL: https://github.com/yourorg/your-apps
        targetRevision: main
        path: '{{path}}'
      destination:
        server: https://kubernetes.default.svc
        namespace: '{{path.basename}}'
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
```

### 使用 kubectl 备份

#### 脚本化备份

```bash
#!/bin/bash
# backup-resources.sh

NAMESPACE=${1:-default}
BACKUP_DIR="./backups/$(date +%Y%m%d)"

mkdir -p $BACKUP_DIR

# 备份所有资源
kubectl get all -n $NAMESPACE -o yaml > $BACKUP_DIR/all-resources.yaml

# 备份 ConfigMaps
kubectl get configmaps -n $NAMESPACE -o yaml > $BACKUP_DIR/configmaps.yaml

# 备份 Secrets
kubectl get secrets -n $NAMESPACE -o yaml > $BACKUP_DIR/secrets.yaml

# 备份 Ingress
kubectl get ingress -n $NAMESPACE -o yaml > $BACKUP_DIR/ingress.yaml

# 备份 PVC
kubectl get pvc -n $NAMESPACE -o yaml > $BACKUP_DIR/pvc.yaml

echo "Backup completed: $BACKUP_DIR"
```

```bash
# 运行备份
chmod +x backup-resources.sh
./backup-resources.sh production
```

---

## 3. etcd 备份

### etcd 手动备份

#### 备份 etcd 数据

```bash
# 在控制平面节点上备份 etcd
ETCDCTL_API=3 etcdctl snapshot save snapshot.db \
  --cacert /etc/kubernetes/pki/etcd/ca.crt \
  --cert /etc/kubernetes/pki/etcd/server.crt \
  --key /etc/kubernetes/pki/etcd/server.key

# 验证备份
ETCDCTL_API=3 etcdctl snapshot status snapshot.db \
  --cacert /etc/kubernetes/pki/etcd/ca.crt \
  --cert /etc/kubernetes/pki/etcd/server.crt \
  --key /etc/kubernetes/pki/etcd/server.key

# 上传到 S3
aws s3 cp snapshot.db s3://etcd-backups/snapshot-$(date +%Y%m%d).db
```

#### 定期备份脚本

```bash
#!/bin/bash
# backup-etcd.sh

DATE=$(date +%Y%m%d)
SNAPSHOT_FILE="etcd-snapshot-$DATE.db"

# 备份 etcd
ETCDCTL_API=3 etcdctl snapshot save $SNAPSHOT_FILE \
  --cacert /etc/kubernetes/pki/etcd/ca.crt \
  --cert /etc/kubernetes/pki/etcd/server.crt \
  --key /etc/kubernetes/pki/etcd/server.key

# 上传到 S3
aws s3 cp $SNAPSHOT_FILE s3://etcd-backups/

# 清理旧备份（保留 7 天）
aws s3 ls s3://etcd-backups/ | grep "etcd-snapshot-" | \
  awk '{print $4}' | while read file; do
    date=$(echo $file | cut -d'-' -f3)
    file_date=$(date -d $date +%s)
    current_date=$(date +%s)
    age_days=$(( (current_date - file_date) / 86400 ))
    
    if [ $age_days -gt 7 ]; then
      aws s3 rm s3://etcd-backups/$file
    fi
  done

echo "etcd backup completed: $SNAPSHOT_FILE"
```

### etcd 恢复

#### 从快照恢复

```bash
# 停止 kube-apiserver
systemctl stop kube-apiserver

# 恢复 etcd 快照
ETCDCTL_API=3 etcdctl snapshot restore snapshot.db \
  --cacert /etc/kubernetes/pki/etcd/ca.crt \
  --cert /etc/kubernetes/pki/etcd/server.crt \
  --key /etc/kubernetes/pki/etcd/server.key \
  --data-dir /var/lib/etcd

# 重启 kube-apiserver
systemctl start kube-apiserver
```

---

## 4. 基础设施备份

### VPC 备份

#### 导出 VPC 配置

```bash
# 使用 AWS CLI 导出 VPC 配置
aws ec2 describe-vpcs --vpc-ids vpc-xxx > vpc-config.json

# 导出子网配置
aws ec2 describe-subnets --filters "Name=vpc-id,Values=vpc-xxx" > subnets-config.json

# 导出安全组配置
aws ec2 describe-security-groups --filters "Name=vpc-id,Values=vpc-xxx" > security-groups.json

# 导出路由表配置
aws ec2 describe-route-tables --filters "Name=vpc-id,Values=vpc-xxx" > route-tables.json
```

#### 使用 Terraform

```bash
# 导出当前状态
terraform show > terraform-state.json

# 导出配置
terraform show -json > terraform-config.json

# 提交到版本控制
git add .
git commit -m "Backup infrastructure state"
git push
```

### EKS 集群配置备份

#### 导出集群配置

```bash
# 导出集群配置
aws eks describe-cluster \
  --name my-eks-cluster \
  --query 'cluster' \
  --output json > cluster-config.json

# 导出节点组配置
aws eks describe-nodegroup \
  --cluster-name my-eks-cluster \
  --nodegroup-name my-nodegroup \
  --output json > nodegroup-config.json

# 导出 addon 配置
aws eks list-addons --cluster-name my-eks-cluster
aws eks describe-addon \
  --cluster-name my-eks-cluster \
  --addon-name vpc-cni \
  --output json > addon-config.json
```

---

## 5. 灾难恢复

### 恢复流程

#### 阶段 1: 评估和准备（5 分钟）

```bash
#!/bin/bash
# disaster-recovery-checklist.sh

echo "=== Disaster Recovery Checklist ==="

# 1. 检查备份完整性
echo "1. Checking backup integrity..."
velero backup get
aws s3 ls s3://etcd-backups/
aws rds describe-db-snapshots

# 2. 检查目标区域资源
echo "2. Checking target region resources..."
aws eks list-clusters --region us-west-2
aws ec2 describe-vpcs --region us-west-2

# 3. 验证备份可访问性
echo "3. Verifying backup accessibility..."
velero backup describe latest-backup
aws s3 ls s3://velero-backups/

echo "=== Check complete ==="
```

#### 阶段 2: 恢复基础设施（15 分钟）

```bash
#!/bin/bash
# restore-infrastructure.sh

echo "=== Restoring Infrastructure ==="

# 1. 创建 VPC
aws cloudformation create-stack \
  --stack-name vpc-stack \
  --template-body file://vpc-template.yaml \
  --region us-west-2

# 2. 创建 EKS 集群
eksctl create cluster \
  --config-file backup-cluster.yaml \
  --region us-west-2

# 3. 等待集群就绪
aws eks wait cluster-active \
  --name backup-cluster \
  --region us-west-2

echo "=== Infrastructure restored ==="
```

#### 阶段 3: 恢复应用数据（30 分钟）

```bash
#!/bin/bash
# restore-data.sh

echo "=== Restoring Application Data ==="

# 1. 恢复数据库快照
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier mydb-restored \
  --db-snapshot-identifier mydb-snapshot-latest \
  --region us-west-2

# 2. 恢复 S3 数据
aws s3 sync s3://source-bucket s3://destination-bucket

# 3. 恢复 ECR 镜像
aws ecr get-login-password --region us-west-2 | \
  docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-west-2.amazonaws.com

echo "=== Application data restored ==="
```

#### 阶段 4: 恢复 Kubernetes 资源（10 分钟）

```bash
#!/bin/bash
# restore-k8s-resources.sh

echo "=== Restoring Kubernetes Resources ==="

# 1. 使用 Velero 恢复
velero restore create full-restore \
  --from-backup full-backup-latest \
  --wait

# 2. 验证资源恢复
kubectl get all -A

# 3. 验证应用状态
kubectl get pods -A

echo "=== Kubernetes resources restored ==="
```

### 验证和测试

```bash
#!/bin/bash
# verify-recovery.sh

echo "=== Verifying Recovery ==="

# 1. 检查 Pod 状态
kubectl get pods -A
kubectl get nodes

# 2. 测试应用连接
curl -I http://my-service.default.svc.cluster.local:8080/health

# 3. 测试数据库连接
kubectl run test-mysql --image=mysql:latest --rm -it --restart=Never -- \
  mysql -h mydb-restored.xxxxx.us-west-2.rds.amazonaws.com -u admin -pSecurePassword123!

# 4. 运行集成测试
kubectl run test-integration --image=my-test:latest --rm -it --restart=Never

echo "=== Verification complete ==="
```

---

## 6. 备份最佳实践

### 3-2-1 备份规则

```
生产环境:
- 3 份副本（1 原始 + 2 备份）
- 2 种介质（S3 + EBS 快照）
- 1 份异地备份（跨区域）

开发/测试环境:
- 2 份副本
- 1 种介质
- 无异地备份
```

### 备份清单

| 备份项 | 频率 | 位置 | 恢复时间 |
|--------|------|------|---------|
| 应用数据库 | 每小时 | 本地 + S3 | 15 分钟 |
| 应用配置 | 每次 | Git + S3 | 5 分钟 |
| Kubernetes 资源 | 每次 | Velero | 10 分钟 |
| etcd 数据 | 每小时 | S3 | 30 分钟 |
| ECR 镜像 | 每天 | ECR | 1 小时 |
| 基础设施 | 每天 | Terraform + Git | 2 小时 |

### 加密备份

```bash
# 加密备份文件
openssl enc -aes-256-cbc -salt -in backup.tar.gz -out backup.tar.gz.enc

# 解密备份文件
openssl enc -d -aes-256-cbc -in backup.tar.gz.enc -out backup.tar.gz
```

---

## 7. 备份监控

### 备份状态监控

#### CloudWatch 告警

```bash
# 创建备份失败告警
aws cloudwatch put-metric-alarm \
  --alarm-name VeleroBackupFailed \
  --alarm-description "Alert when Velero backup fails" \
  --metric-name BackupFailed \
  --namespace Velero \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:backup-alerts
```

#### 备份验证脚本

```bash
#!/bin/bash
# verify-backups.sh

echo "=== Verifying Backups ==="

# 1. 验证 Velero 备份
velero backup get --output json | \
  jq -r '.items[] | "\(.metadata.name): \(.status.phase)"'

# 2. 验证 RDS 快照
aws rds describe-db-snapshots \
  --query 'DBSnapshots[?DBSnapshotIdentifier!=`null`].[DBSnapshotIdentifier,DBInstanceIdentifier,SnapshotCreateTime]' \
  --output table

# 3. 验证 S3 备份
aws s3 ls s3://velero-backups/ | grep "BACKUP" | wc -l

# 4. 验证 etcd 备份
aws s3 ls s3://etcd-backups/ | grep "etcd-snapshot" | wc -l

echo "=== Verification complete ==="
```

---

## 8. 灾难恢复演练

### 演练计划

#### 每月演练

```bash
#!/bin/bash
# monthly-drill.sh

MONTH=$(date +%Y%m)
DRILL_NAME="monthly-drill-$MONTH"

echo "=== Monthly Disaster Recovery Drill: $DRILL_NAME ==="

# 1. 创建演练环境
echo "1. Creating drill environment..."
# 在测试区域创建集群

# 2. 模拟故障
echo "2. Simulating failure..."
# 停止主集群节点

# 3. 执行恢复
echo "3. Executing recovery..."
./restore-infrastructure.sh
./restore-data.sh
./restore-k8s-resources.sh

# 4. 验证恢复
echo "4. Verifying recovery..."
./verify-recovery.sh

# 5. 记录结果
echo "5. Recording results..."
echo "DRILL_COMPLETE_TIME=$(date)" > drill-report-$MONTH.txt

echo "=== Drill complete ==="
```

---

## 参考资源

### AWS 官方文档
- [EKS Backup and Restore](https://docs.aws.amazon.com/eks/latest/userguide/backup-restore.html)
- [RDS Backup](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Backup.html)
- [DynamoDB Backup](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/BackupRestore.html)

### 工具和服务
- [Velero](https://velero.io/)
- [ArgoCD](https://argoproj.github.io/argo-cd/)
- [Terraform](https://www.terraform.io/)
- [AWS Backup](https://aws.amazon.com/backup/)

### 社区资源
- [Kubernetes Backup and Restore](https://kubernetes.io/docs/tasks/administer-cluster/configure-upgrade-etcd/)
- [CNCF Velero](https://velero.io/)
- [AWS Well-Architected Framework - Reliability](https://aws.amazon.com/architecture/well-architected/reliability-pillar/)