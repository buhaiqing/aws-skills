# Multi-Region High Availability — EKS

## 概述

多区域高可用（Multi-Region HA）确保 EKS 集群和应用程序在单个区域故障时能够继续运行，提供企业级的可靠性和灾难恢复能力。

## 架构模式

### 模式 1: 主备架构（Primary-Backup）

```
Primary Region (us-east-1)
├── EKS Cluster (Active)
├── Applications
└── Database (Primary)

Backup Region (us-west-2)
├── EKS Cluster (Standby)
└── Database (Read Replica)

Traffic
└── Route 53 → Primary Region
```

**优点**:
- 实现简单
- 成本较低
- 数据一致性好

**缺点**:
- 故障切换时间较长
- 备用区域资源利用率低

### 模式 2: 活跃-活跃架构（Active-Active）

```
Primary Region (us-east-1)
├── EKS Cluster (Active)
├── Applications (50% Traffic)
└── Database (Primary)

Secondary Region (us-west-2)
├── EKS Cluster (Active)
├── Applications (50% Traffic)
└── Database (Read/Write)

Traffic
└── Route 53 → Both Regions (Latency-based)
```

**优点**:
- 零停机故障切换
- 资源利用率高
- 更好的性能

**缺点**:
- 实现复杂
- 成本较高
- 数据一致性挑战

### 模式 3: 全球架构（Global）

```
Region 1 (us-east-1)
├── EKS Cluster
└── Applications

Region 2 (eu-west-1)
├── EKS Cluster
└── Applications

Region 3 (ap-southeast-1)
├── EKS Cluster
└── Applications

Traffic
└── CloudFront → Route 53 → Nearest Region
```

**优点**:
- 最佳用户体验
- 全球覆盖
- 区域故障隔离

**缺点**:
- 最复杂
- 最高成本
- 数据同步挑战

---

## 1. 创建跨区域 EKS 集群

### 使用 eksctl 创建主集群

```yaml
# primary-cluster.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: primary-cluster
  region: us-east-1
  version: "1.30"

vpc:
  id: "vpc-primary"
  cidr: "10.0.0.0/16"
  subnets:
    private:
      us-east-1a:
        id: "subnet-private-1a"
        cidr: "10.0.1.0/24"
      us-east-1b:
        id: "subnet-private-1b"
        cidr: "10.0.2.0/24"
      us-east-1c:
        id: "subnet-private-1c"
        cidr: "10.0.3.0/24"
    public:
      us-east-1a:
        id: "subnet-public-1a"
        cidr: "10.0.101.0/24"
      us-east-1b:
        id: "subnet-public-1b"
        cidr: "10.0.102.0/24"

managedNodeGroups:
  - name: primary-ng
    instanceType: t3.large
    minSize: 2
    maxSize: 5
    desiredSize: 3
    labels:
      role: worker
      region: us-east-1
    tags:
      Environment: production
      Region: us-east-1
```

```bash
# 创建主集群
eksctl create cluster -f primary-cluster.yaml

# 验证集群
aws eks describe-cluster --name primary-cluster --region us-east-1
```

### 创建备用集群

```yaml
# backup-cluster.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: backup-cluster
  region: us-west-2
  version: "1.30"

vpc:
  cidr: "10.1.0.0/16"
  subnets:
    private:
      us-west-2a:
        cidr: "10.1.1.0/24"
      us-west-2b:
        cidr: "10.1.2.0/24"
      us-west-2c:
        cidr: "10.1.3.0/24"
    public:
      us-west-2a:
        cidr: "10.1.101.0/24"
      us-west-2b:
        cidr: "10.1.102.0/24"

managedNodeGroups:
  - name: backup-ng
    instanceType: t3.large
    minSize: 1
    maxSize: 3
    desiredSize: 2
    labels:
      role: worker
      region: us-west-2
    tags:
      Environment: production
      Region: us-west-2
```

```bash
# 创建备用集群
eksctl create cluster -f backup-cluster.yaml

# 验证集群
aws eks describe-cluster --name backup-cluster --region us-west-2
```

---

## 2. 跨区域数据同步

### RDS 跨区域副本

#### 创建主数据库

```bash
# 创建主 RDS 实例
aws rds create-db-instance \
  --db-instance-identifier mydb-primary \
  --db-instance-class db.t3.medium \
  --engine mysql \
  --master-username admin \
  --master-user-password SecurePassword123! \
  --allocated-storage 20 \
  --storage-type gp3 \
  --vpc-security-group-ids sg-primary \
  --db-subnet-group-name mydb-subnet-group \
  --region us-east-1 \
  --multi-az \
  --backup-retention-period 7
```

#### 创建跨区域只读副本

```bash
# 创建跨区域副本
aws rds create-db-instance-read-replica \
  --db-instance-identifier mydb-replica \
  --source-db-instance-identifier mydb-primary \
  --region us-west-2 \
  --db-instance-class db.t3.medium \
  --vpc-security-group-ids sg-backup \
  --db-subnet-group-name mydb-subnet-group-backup
```

#### 验证复制状态

```bash
# 检查复制状态
aws rds describe-db-instances \
  --db-instance-identifier mydb-replica \
  --region us-west-2 \
  --query 'DBInstances[0].ReadReplicaSourceDBInstanceIdentifier'

# 查看复制延迟
aws rds describe-db-instances \
  --db-instance-identifier mydb-replica \
  --region us-west-2 \
  --query 'DBInstances[0].StatusInfos'
```

### DynamoDB 全局表

#### 创建全局表

```bash
# 在主区域创建表
aws dynamodb create-table \
  --table-name Users \
  --attribute-definitions AttributeName=userId,AttributeType=S \
  --key-schema AttributeName=userId,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1 \
  --global-secondary-indexes '[
    {
      "IndexName": "EmailIndex",
      "KeySchema": [{"AttributeName":"email","KeyType":"HASH"}],
      "Projection": {"ProjectionType":"ALL"}
    }
  ]'

# 创建全局表副本
aws dynamodb update-table \
  --table-name Users \
  --replica-updates '[
    {
      "Create": {
        "RegionName": "us-west-2"
      }
    }
  ]' \
  --region us-east-1

# 验证全局表
aws dynamodb describe-table --table-name Users --region us-east-1
```

#### 应用配置

```yaml
# 使用 AWS SDK 访问全局表
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  AWS_REGION: us-east-1
  DYNAMODB_TABLE: Users
  DYNAMODB_ENDPOINT: ""  # 留空使用全局表
```

### S3 跨区域复制

#### 配置 S3 复制

```bash
# 创建源存储桶
aws s3api create-bucket \
  --bucket myapp-source-bucket \
  --region us-east-1 \
  --create-bucket-configuration LocationConstraint=us-east-1

# 创建目标存储桶
aws s3api create-bucket \
  --bucket myapp-destination-bucket \
  --region us-west-2 \
  --create-bucket-configuration LocationConstraint=us-west-2

# 配置跨区域复制
aws s3api put-bucket-replication \
  --bucket myapp-source-bucket \
  --replication-configuration '{
    "Role": "arn:aws:iam::123456789012:role/s3-replication-role",
    "Rules": [
      {
        "Id": "ReplicationRule",
        "Status": "Enabled",
        "Prefix": "",
        "Destination": {
          "Bucket": "arn:aws:s3:::myapp-destination-bucket",
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
  --bucket myapp-source-bucket \
  --versioning-configuration Status=Enabled \
  --region us-east-1

aws s3api put-bucket-versioning \
  --bucket myapp-destination-bucket \
  --versioning-configuration Status=Enabled \
  --region us-west-2
```

---

## 3. 跨区域流量路由

### Route 53 健康检查

#### 创建健康检查

```bash
# 主区域健康检查
PRIMARY_HEALTH_CHECK_ID=$(aws route53 create-health-check \
  --caller-reference primary-$(date +%s) \
  --health-check-config '{
    "IPAddress": "10.0.1.100",
    "Port": 80,
    "Type": "HTTP",
    "ResourcePath": "/health",
    "RequestInterval": 30,
    "FailureThreshold": 3,
    "FullyQualifiedDomainName": "app.example.com"
  }' \
  --query 'HealthCheck.Id' \
  --output text)

# 备用区域健康检查
BACKUP_HEALTH_CHECK_ID=$(aws route53 create-health-check \
  --caller-reference backup-$(date +%s) \
  --health-check-config '{
    "IPAddress": "10.1.1.100",
    "Port": 80,
    "Type": "HTTP",
    "ResourcePath": "/health",
    "RequestInterval": 30,
    "FailureThreshold": 3,
    "FullyQualifiedDomainName": "app.example.com"
  }' \
  --query 'HealthCheck.Id' \
  --output text)
```

### 创建主备路由策略

```bash
# 创建主备路由
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch '{
    "Changes": [
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "app.example.com",
          "Type": "A",
          "SetIdentifier": "primary",
          "Region": "us-east-1",
          "Failover": "PRIMARY",
          "TTL": 60,
          "ResourceRecords": [
            {"Value": "10.0.1.100"}
          ],
          "HealthCheckId": "'$PRIMARY_HEALTH_CHECK_ID'"
        }
      },
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "app.example.com",
          "Type": "A",
          "SetIdentifier": "backup",
          "Region": "us-west-2",
          "Failover": "SECONDARY",
          "TTL": 60,
          "ResourceRecords": [
            {"Value": "10.1.1.100"}
          ],
          "HealthCheckId": "'$BACKUP_HEALTH_CHECK_ID'"
        }
      }
    ]
  }'
```

### 创建延迟路由策略（活跃-活跃）

```bash
# 创建延迟路由
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch '{
    "Changes": [
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "app.example.com",
          "Type": "A",
          "SetIdentifier": "us-east-1",
          "Region": "us-east-1",
          "TTL": 60,
          "ResourceRecords": [
            {"Value": "10.0.1.100"}
          ]
        }
      },
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "app.example.com",
          "Type": "A",
          "SetIdentifier": "us-west-2",
          "Region": "us-west-2",
          "TTL": 60,
          "ResourceRecords": [
            {"Value": "10.1.1.100"}
          ]
        }
      }
    ]
  }'
```

### 使用 AWS Global Accelerator

```bash
# 创建加速器
ACCELERATOR_ARN=$(aws globalaccelerator create-accelerator \
  --name my-app-accelerator \
  --IpAddresses '["10.0.1.100", "10.1.1.100"]' \
  --Enabled \
  --query 'Accelerator.AcceleratorArn' \
  --output text)

# 创建监听器
LISTENER_ARN=$(aws globalaccelerator create-listener \
  --accelerator-arn $ACCELERATOR_ARN \
  --protocol TCP \
  --port-ranges '[{"FromPort":80,"ToPort":80}]' \
  --query 'Listener.ListenerArn' \
  --output text)

# 创建端点组（主区域）
PRIMARY_ENDPOINT_GROUP_ARN=$(aws globalaccelerator create-endpoint-group \
  --listener-arn $LISTENER_ARN \
  --endpoint-group-region us-east-1 \
  --health-check-path /health \
  --health-check-port 80 \
  --health-check-protocol HTTP \
  --query 'EndpointGroup.EndpointGroupArn' \
  --output text)

# 添加端点
aws globalaccelerator add-endpoints \
  --endpoint-group-arn $PRIMARY_ENDPOINT_GROUP_ARN \
  --endpoint-configurations '[
    {"EndpointId": "i-1234567890abcdef0","Weight": 100}
  ]'

# 创建端点组（备用区域）
BACKUP_ENDPOINT_GROUP_ARN=$(aws globalaccelerator create-endpoint-group \
  --listener-arn $LISTENER_ARN \
  --endpoint-group-region us-west-2 \
  --health-check-path /health \
  --health-check-port 80 \
  --health-check-protocol HTTP \
  --query 'EndpointGroup.EndpointGroupArn' \
  --output text)
```

---

## 4. 跨区域应用部署

### 使用 ArgoCD 进行多集群管理

#### 安装 ArgoCD（主集群）

```bash
# 创建命名空间
kubectl create namespace argocd

# 安装 ArgoCD
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 暴露 ArgoCD UI
kubectl create ingress argocd-server \
  --namespace argocd \
  --rule="host=argocd.example.com" \
  --service=argocd-server \
  --port=443
```

#### 添加备用集群

```bash
# 在主集群添加备用集群
aws eks update-kubeconfig --name backup-cluster --region us-west-2 --alias backup-cluster

argocd cluster add backup-cluster --name backup-cluster

# 验证集群
argocd cluster list
```

#### 创建应用（多集群）

```yaml
# app-multi-cluster.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app-multi-cluster
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/yourorg/your-app.git
    targetRevision: main
    path: k8s
  destinations:
  - name: primary-cluster
    namespace: production
  - name: backup-cluster
    namespace: production
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
```

```bash
# 应用配置
kubectl apply -f app-multi-cluster.yaml

# 查看应用状态
argocd app get my-app-multi-cluster
```

### 使用 Helm 进行多集群部署

#### 创建部署脚本

```bash
#!/bin/bash
# deploy-multi-region.sh

APP_NAME=my-app
VERSION=1.0.0

# 部署到主集群
aws eks update-kubeconfig --name primary-cluster --region us-east-1
helm upgrade --install $APP_NAME ./helm-chart \
  --namespace production \
  --set image.tag=$VERSION \
  --set region=us-east-1 \
  --set database.host=mydb-primary.xxxxx.us-east-1.rds.amazonaws.com \
  --create-namespace

# 部署到备用集群
aws eks update-kubeconfig --name backup-cluster --region us-west-2
helm upgrade --install $APP_NAME ./helm-chart \
  --namespace production \
  --set image.tag=$VERSION \
  --set region=us-west-2 \
  --set database.host=mydb-replica.xxxxx.us-west-2.rds.amazonaws.com \
  --create-namespace

echo "Deployment completed"
```

```bash
# 运行部署
chmod +x deploy-multi-region.sh
./deploy-multi-region.sh
```

---

## 5. 故障切换和恢复

### 自动故障切换

#### 使用 Route 53 自动故障切换

```bash
# Route 53 会自动检测健康检查失败并切换到备用区域
# 无需手动干预

# 查看当前路由
aws route53 get-health-check-status \
  --health-check-id $PRIMARY_HEALTH_CHECK_ID

# 监控健康检查状态
watch -n 5 "aws route53 get-health-check-status --health-check-id $PRIMARY_HEALTH_CHECK_ID"
```

#### 应用层故障切换

```python
# 应用配置示例
import boto3
import random

def get_database_endpoint():
    """根据健康状态选择数据库端点"""
    route53 = boto3.client('route53')

    # 检查主区域健康状态
    primary_status = route53.get_health_check_status(
        HealthCheckId=PRIMARY_HEALTH_CHECK_ID
    )

    if primary_status['HealthCheckStatus'] == 'Success':
        return 'mydb-primary.xxxxx.us-east-1.rds.amazonaws.com'
    else:
        return 'mydb-replica.xxxxx.us-west-2.rds.amazonaws.com'

def get_cluster_endpoint():
    """根据健康状态选择集群端点"""
    route53 = boto3.client('route53')

    primary_status = route53.get_health_check_status(
        HealthCheckId=PRIMARY_HEALTH_CHECK_ID
    )

    if primary_status['HealthCheckStatus'] == 'Success':
        return 'https://primary-cluster.gr7.us-east-1.eks.amazonaws.com'
    else:
        return 'https://backup-cluster.gr7.us-west-2.eks.amazonaws.com'
```

### 手动故障切换

#### 使用 AWS CLI 切换流量

```bash
#!/bin/bash
# failover.sh

# 更新 Route 53 记录指向备用区域
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch '{
    "Changes": [
      {
        "Action": "UPSERT",
        "ResourceRecordSet": {
          "Name": "app.example.com",
          "Type": "CNAME",
          "TTL": 60,
          "ResourceRecords": [
            {"Value": "backup-app.example.com"}
          ]
        }
      }
    ]
  }'

echo "Traffic routed to backup region"
```

```bash
# 执行故障切换
chmod +x failover.sh
./failover.sh
```

#### 脚本化故障恢复

```bash
#!/bin/bash
# recover.sh

# 更新 Route 53 记录指向主区域
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch '{
    "Changes": [
      {
        "Action": "UPSERT",
        "ResourceRecordSet": {
          "Name": "app.example.com",
          "Type": "CNAME",
          "TTL": 60,
          "ResourceRecords": [
            {"Value": "primary-app.example.com"}
          ]
        }
      }
    ]
  }'

echo "Traffic restored to primary region"
```

---

## 6. 数据同步和一致性

### 事件流复制

#### 使用 EventBridge 跨区域事件

```bash
# 创建事件规则（主区域）
aws events put-rule \
  --name replicate-to-backup \
  --event-pattern '{
    "source": ["com.myapp.events"],
    "detail-type": ["UserCreated"]
  }' \
  --region us-east-1

# 创建目标（跨区域）
aws events put-targets \
  --rule replicate-to-backup \
  --targets '[
    {
      "Id": "1",
      "Arn": "arn:aws:events:us-west-2:123456789012:event-bus/backup-bus"
    }
  ]' \
  --region us-east-1

# 在备用区域创建事件总线
aws events create-event-bus \
  --name backup-bus \
  --region us-west-2

# 创建目标处理事件
aws events put-targets \
  --rule process-replicated-events \
  --event-bus-name backup-bus \
  --targets '[
    {
      "Id": "1",
      "Arn": "arn:aws:lambda:us-west-2:123456789012:function:ProcessUserEvent"
    }
  ]' \
  --region us-west-2
```

### 消息队列复制

#### 使用 SQS 跨区域消息

```bash
# 创建主队列
aws sqs create-queue \
  --queue-name primary-queue.fifo \
  --attributes FifoQueue=true,ContentBasedDeduplication=true \
  --region us-east-1

PRIMARY_QUEUE_URL=$(aws sqs get-queue-url --queue-name primary-queue.fifo --region us-east-1 --query 'QueueUrl' --output text)

# 创建备用队列
aws sqs create-queue \
  --queue-name backup-queue.fifo \
  --attributes FifoQueue=true,ContentBasedDeduplication=true \
  --region us-west-2

BACKUP_QUEUE_URL=$(aws sqs get-queue-url --queue-name backup-queue.fifo --region us-west-2 --query 'QueueUrl' --output text)

# 创建复制 Lambda
cat > replicate-sqs.py <<EOF
import boto3
import json

sqs = boto3.client('sqs')

def lambda_handler(event, context):
    for record in event['Records']:
        message = json.loads(record['body'])
        sqs.send_message(
            QueueUrl='$BACKUP_QUEUE_URL',
            MessageBody=json.dumps(message),
            MessageGroupId='replicated'
        )
    return {'statusCode': 200}
EOF

# 部署 Lambda
aws lambda create-function \
  --function-name ReplicateSQS \
  --runtime python3.9 \
  --role arn:aws:iam::123456789012:role/LambdaRole \
  --handler replicate-sqs.lambda_handler \
  --zip-file fileb://replicate-sqs.zip \
  --region us-east-1

# 创建事件源映射
aws lambda create-event-source-mapping \
  --function-name ReplicateSQS \
  --batch-size 10 \
  --maximum-batching-window-in-seconds 5 \
  --event-source-arn $(echo $PRIMARY_QUEUE_URL | sed 's/https:\/\/sqs\.us-east-1\.amazonaws\.com\//arn:aws:sqs:us-east-1:123456789012:/') \
  --region us-east-1
```

---

## 7. 监控和告警

### 跨区域监控

#### 使用 CloudWatch 跨区域仪表板

```bash
# 创建跨区域仪表板
aws cloudwatch put-dashboard \
  --dashboard-name MultiRegionHA \
  --dashboard-body '{
    "widgets": [
      {
        "type": "metric",
        "x": 0,
        "y": 0,
        "width": 12,
        "height": 6,
        "properties": {
          "metrics": [
            ["AWS/EKS", "cluster_cpu_utilization", "ClusterName", "primary-cluster", {"region": "us-east-1"}],
            [".", ".", "ClusterName", "backup-cluster", {"region": "us-west-2"}]
          ],
          "period": 300,
          "stat": "Average",
          "region": "us-east-1",
          "title": "EKS Cluster CPU Utilization"
        }
      },
      {
        "type": "metric",
        "x": 0,
        "y": 6,
        "width": 12,
        "height": 6,
        "properties": {
          "metrics": [
            ["AWS/EKS", "node_count", "ClusterName", "primary-cluster", {"region": "us-east-1"}],
            [".", ".", "ClusterName", "backup-cluster", {"region": "us-west-2"}]
          ],
          "period": 300,
          "stat": "Average",
          "region": "us-east-1",
          "title": "Node Count"
        }
      }
    ]
  }'
```

### 跨区域告警

#### 创建区域故障告警

```bash
# 主区域健康检查告警
aws cloudwatch put-metric-alarm \
  --alarm-name PrimaryRegionHealthCheck \
  --alarm-description "Alert when primary region health check fails" \
  --metric-name HealthCheckStatus \
  --namespace AWS/Route53 \
  --dimensions Name=HealthCheckId,Value=$PRIMARY_HEALTH_CHECK_ID \
  --statistic Minimum \
  --period 60 \
  --evaluation-periods 3 \
  --threshold 0 \
  --comparison-operator LessThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:ha-alerts \
  --region us-east-1

# 备用区域告警
aws cloudwatch put-metric-alarm \
  --alarm-name BackupRegionHealthCheck \
  --alarm-description "Alert when backup region health check fails" \
  --metric-name HealthCheckStatus \
  --namespace AWS/Route53 \
  --dimensions Name=HealthCheckId,Value=$BACKUP_HEALTH_CHECK_ID \
  --statistic Minimum \
  --period 60 \
  --evaluation-periods 3 \
  --threshold 0 \
  --comparison-operator LessThanThreshold \
  --alarm-actions arn:aws:sns:us-west-2:123456789012:ha-alerts \
  --region us-west-2
```

### 数据复制延迟告警

```bash
# RDS 复制延迟告警
aws cloudwatch put-metric-alarm \
  --alarm-name RDSCopyDelay \
  --alarm-description "Alert when RDS replication delay exceeds 5 seconds" \
  --metric-name ReadLag \
  --namespace AWS/RDS \
  --dimensions Name=DBInstanceIdentifier,Value=mydb-replica \
  --statistic Maximum \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:ha-alerts \
  --region us-west-2
```

---

## 8. 灾难恢复演练

### 模拟区域故障

#### 停止主集群（演练）

```bash
#!/bin/bash
# simulate-failure.sh

echo "Starting disaster recovery drill..."

# 1. 停止主集群所有节点
aws eks update-nodegroup-config \
  --cluster-name primary-cluster \
  --nodegroup-name primary-ng \
  --scaling-config minSize=0,maxSize=0,desiredSize=0 \
  --region us-east-1

# 2. 等待节点停止
echo "Waiting for nodes to terminate..."
sleep 120

# 3. 验证备用集群
aws eks describe-cluster --name backup-cluster --region us-west-2

# 4. 验证数据库副本
aws rds describe-db-instances \
  --db-instance-identifier mydb-replica \
  --region us-west-2

# 5. 测试应用访问
curl -I https://backup-app.example.com/health

echo "Disaster recovery drill completed"
```

### 恢复流程

```bash
#!/bin/bash
# recovery-drill.sh

echo "Starting recovery..."

# 1. 恢复主集群节点
aws eks update-nodegroup-config \
  --cluster-name primary-cluster \
  --nodegroup-name primary-ng \
  --scaling-config minSize=2,maxSize=5,desiredSize=3 \
  --region us-east-1

# 2. 等待集群就绪
echo "Waiting for cluster to be ready..."
aws eks wait cluster-active --name primary-cluster --region us-east-1

# 3. 验证集群状态
kubectl get nodes --context primary-cluster

# 4. 恢复流量
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch '{
    "Changes": [
      {
        "Action": "UPSERT",
        "ResourceRecordSet": {
          "Name": "app.example.com",
          "Type": "CNAME",
          "TTL": 60,
          "ResourceRecords": [
            {"Value": "primary-app.example.com"}
          ]
        }
      }
    ]
  }'

echo "Recovery completed"
```

---

## 9. 最佳实践

### 设计原则

1. **最小化故障域**
   - 使用多可用区部署
   - 隔离不同层级的资源

2. **自动化故障切换**
   - 使用健康检查自动切换
   - 减少手动干预

3. **数据一致性**
   - 选择合适的复制策略
   - 监控复制延迟

4. **成本优化**
   - 备用区域使用较小规模
   - 使用 Spot 实例

5. **定期演练**
   - 每季度进行一次演练
   - 记录恢复时间目标（RTO）

### 配置清单

| 配置项 | 主备架构 | 活跃-活跃 | 全球 |
|--------|---------|----------|------|
| EKS 集群 | 2 个 | 2 个 | 3+ 个 |
| 数据库副本 | 是 | 是 | 是 |
| 健康检查 | 是 | 是 | 是 |
| 自动故障切换 | 是 | 是 | 是 |
| 流量分配 | 100/0 | 50/50 | 33/33/33 |
| 成本倍数 | ~1.5x | ~2x | ~3x |

### 常见错误

❌ **避免**:
1. 只部署单区域
2. 不进行灾难恢复演练
3. 忽略数据一致性
4. 手动故障切换
5. 不监控复制延迟

✅ **推荐**:
1. 多区域部署
2. 自动故障切换
3. 定期演练
4. 监控和告警
5. 文档化流程

---

## 参考资源

### AWS 官方文档
- [EKS Multi-Region](https://docs.aws.amazon.com/eks/latest/userguide/multi-region.html)
- [Route 53 Health Checks](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/health-checks.html)
- [Global Accelerator](https://docs.aws.amazon.com/global-accelerator/latest/dg/what-is-global-accelerator.html)
- [RDS Cross-Region Replication](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ReadRepl.html)

### 工具和服务
- [ArgoCD](https://argoproj.github.io/argo-cd/)
- [Helm](https://helm.sh/)
- [Terraform](https://www.terraform.io/)
- [Kubernetes Federation](https://kubernetes.io/docs/concepts/cluster-administration/federation/)

### 社区资源
- [AWS Well-Architected Framework - Reliability](https://aws.amazon.com/architecture/well-architected/reliability-pillar/)
- [Multi-Region Kubernetes](https://aws.amazon.com/blogs/containers/building-a-multi-region-kubernetes-architecture/)
- [Disaster Recovery on AWS](https://aws.amazon.com/blogs/architecture/disaster-recovery-dr-architecture-on-aws/)