# AWS Skills Repository

AWS 云资源/云服务操作技能集合，用于 AI Agent 自动化运维场景。

🌐 [English Version](./README.md)

## 项目结构

```
aws-skills/
├── aws-skill-generator/           # Meta Skill (技能生成器)
│   ├── SKILL.md                   # 精简版 - What to do
│   ├── references/                # 详细实现 - How to do
│   │   ├── aws-skill-template.md  # 技能骨架模板
│   │   ├── aws-cli-conventions.md # CLI 行为规范
│   │   ├── boto3-sdk-usage.md     # SDK 使用模式
│   │   ├── integration.md         # 环境设置
│   │   ├── core-concepts-template.md
│   │   ├── troubleshooting-template.md
│   │   └── governance-review.md   # 检查清单
│   └── assets/
│       └── example-config.yaml

├── aws-ec2-ops/                   # EC2 操作技能
│   ├── SKILL.md                   # 精简版 - 触发/范围/流程
│   ├── references/
│   │   ├── aws-cli-usage.md       # EC2 CLI 命令详解
│   │   ├── boto3-sdk-usage.md     # EC2 SDK 代码示例
│   │   ├── core-concepts.md       # EC2 架构/配额
│   │   └── troubleshooting.md    # EC2 故障排查
│   └── assets/

├── aws-s3-ops/                    # S3 操作技能
│   ├── SKILL.md                   # 精简版 - Bucket/Object 操作
│   ├── references/
│   │   ├── aws-cli-usage.md       # S3 CLI 命令详解
│   │   ├── boto3-sdk-usage.md     # S3 SDK 代码示例
│   │   ├── core-concepts.md       # S3 存储类/配额
│   │   └── troubleshooting.md    # S3 故障排查
│   └── assets/
│       └── example-config.yaml    # Policy/Lifecycle 示例

├── aws-cloudwatch-ops/            # CloudWatch 操作技能
│   ├── SKILL.md                   # 精简版 - Metrics/Alarms 操作
│   ├── references/
│   │   ├── aws-cli-usage.md       # CloudWatch CLI 命令详解
│   │   ├── boto3-sdk-usage.md     # CloudWatch SDK 代码示例
│   │   ├── core-concepts.md       # Namespace/Metric 结构
│   │   └── troubleshooting.md    # CloudWatch 故障排查
│   └── assets/
│       └── example-config.yaml    # Alarm/Dashboard 示例

├── aws-iam-ops/             # IAM 操作技能
│   ├── SKILL.md             # 精简版 - User/Group/Role/Policy 操作
│   ├── references/
│   │   ├── aws-cli-usage.md # IAM CLI 命令详解
│   │   ├── boto3-sdk-usage.md # IAM SDK 代码示例
│   │   ├── core-concepts.md # IAM 组件/配额
│   │   └── troubleshooting.md # IAM 故障排查
│   └── assets/
│       └── example-config.yaml # Trust/Permission Policy 示例

├── aws-elb-ops/             # ELB 操作技能
│   ├── SKILL.md             # 精简版 - ALB/NLB/CLB 操作
│   ├── references/
│   │   ├── aws-cli-usage.md # ELB CLI 命令详解
│   │   ├── boto3-sdk-usage.md # ELB SDK 代码示例
│   │   ├── core-concepts.md # 负载均衡器类型/组件
│   │   └── troubleshooting.md # ELB 故障排查
│   └── assets/
│       └── example-config.yaml # Listener/Target Group 示例

├── aws-eks-ops/             # EKS 操作技能
│   ├── SKILL.md             # 精简版 - Cluster/NodeGroup/Fargate 操作
│   ├── references/
│   │   ├── aws-cli-usage.md # EKS CLI 命令详解
│   │   ├── boto3-sdk-usage.md # EKS SDK 代码示例
│   │   ├── core-concepts.md # Kubernetes 版本/组件
│   │   └── troubleshooting.md # EKS 故障排查
│   └── assets/
│       └── example-config.yaml # NodeGroup/Fargate/Addon 示例
│
├── aws-lambda-ops/          # Lambda 操作技能
│   ├── SKILL.md             # 精简版 - Function/Layer 操作
│   ├── references/
│   │   ├── aws-cli-usage.md # Lambda CLI 命令详解
│   │   ├── boto3-sdk-usage.md # Lambda SDK 代码示例
│   │   ├── core-concepts.md # Serverless 计算/运行时
│   │   └── troubleshooting.md # Lambda 故障排查
│   └── assets/
│       └── example-config.yaml # Function/Layer/EventSource 示例
│
├── aws-vpc-ops/             # VPC 操作技能
│   ├── SKILL.md             # 精简版 - VPC/Subnet/SecurityGroup 操作
│   ├── references/
│   │   ├── aws-cli-usage.md # VPC CLI 命令详解
│   │   ├── boto3-sdk-usage.md # VPC SDK 代码示例
│   │   ├── core-concepts.md # 网络架构/CIDR
│   │   └── troubleshooting.md # VPC 故障排查
│   └── assets/
│       └── example-config.yaml # VPC/Subnet/SG 示例
│
├── aws-rds-ops/             # RDS 操作技能
│   ├── SKILL.md             # 精简版 - DB Instance/Snapshot 操作
│   ├── references/
│   │   ├── aws-cli-usage.md # RDS CLI 命令详解
│   │   ├── boto3-sdk-usage.md # RDS SDK 代码示例
│   │   ├── core-concepts.md # 数据库引擎/高可用
│   │   └── troubleshooting.md # RDS 故障排查
│   └── assets/
│       └── example-config.yaml # DB/Snapshot/ParamGroup 示例
│
├── aws-elasticache-ops/     # ElastiCache 操作技能
│   ├── SKILL.md             # 精简版 - Redis/Memcached 操作
│   ├── references/
│   │   ├── aws-cli-usage.md # ElastiCache CLI 命令详解
│   │   ├── boto3-sdk-usage.md # ElastiCache SDK 代码示例
│   │   ├── core-concepts.md # Redis vs Memcached/节点类型
│   │   └── troubleshooting.md # ElastiCache 故障排查
│   └── assets/
│       └── example-config.yaml # Redis/Memcached 配置示例
│
├── aws-dynamodb-ops/              # DynamoDB 操作技能
│   ├── SKILL.md                   # 精简版 - Table/Item/GSI 操作
│   ├── references/
│   │   ├── aws-cli-usage.md       # DynamoDB CLI 命令详解
│   │   ├── boto3-sdk-usage.md     # DynamoDB SDK 代码示例
│   │   ├── core-concepts.md       # NoSQL, 容量模式, 索引
│   │   └── troubleshooting.md     # DynamoDB 故障排查
│   └── assets/
│       └── example-config.yaml    # Table/GSI/Item 配置示例
│
├── aws-cloudtrail-ops/            # CloudTrail 操作技能
│   ├── SKILL.md                   # 精简版 - Trail/Event 操作
│   ├── references/
│   │   ├── aws-cli-usage.md       # CloudTrail CLI 命令详解
│   │   ├── boto3-sdk-usage.md     # CloudTrail SDK 代码示例
│   │   ├── core-concepts.md       # 审计日志, 事件类型
│   │   └── troubleshooting.md     # CloudTrail 故障排查
│   └── assets/
│       └── example-config.yaml    # Trail/Event 配置示例
│
├── aws-kms-ops/                   # KMS 操作技能
│   ├── SKILL.md                   # 精简版 - Key/Encryption 操作
│   ├── references/
│   │   ├── aws-cli-usage.md       # KMS CLI 命令详解
│   │   ├── boto3-sdk-usage.md     # KMS SDK 代码示例
│   │   ├── core-concepts.md       # 加密密钥, 密钥生命周期
│   │   └── troubleshooting.md     # KMS 故障排查
│   └── assets/
│       └── example-config.yaml    # 密钥策略/配置示例
│
├── aws-route53-ops/               # Route53 操作技能
│   ├── SKILL.md                   # 精简版 - DNS/Hosted Zone 操作
│   ├── references/
│   │   ├── aws-cli-usage.md       # Route53 CLI 命令详解
│   │   ├── boto3-sdk-usage.md     # Route53 SDK 代码示例
│   │   ├── core-concepts.md       # DNS, 路由策略
│   │   └── troubleshooting.md     # Route53 故障排查
│   └── assets/
│       └── example-config.yaml    # DNS/健康检查配置示例
│
├── aws-secretsmanager-ops/        # Secrets Manager 操作技能
│   ├── SKILL.md                   # 精简版 - Secret/Rotation 操作
│   ├── references/
│   │   ├── aws-cli-usage.md       # Secrets Manager CLI 命令详解
│   │   ├── boto3-sdk-usage.md     # Secrets Manager SDK 代码示例
│   │   ├── core-concepts.md       # 密钥, 自动轮换
│   │   └── troubleshooting.md     # Secrets Manager 故障排查
│   └── assets/
│       └── example-config.yaml    # 密钥/轮换配置示例
│
├── aws-sqs-ops/                   # SQS 操作技能
│   ├── SKILL.md                   # 精简版 - Queue/Message 操作
│   ├── references/
│   │   ├── aws-cli-usage.md       # SQS CLI 命令详解
│   │   ├── boto3-sdk-usage.md     # SQS SDK 代码示例
│   │   ├── core-concepts.md       # 队列, 死信队列, FIFO
│   │   └── troubleshooting.md     # SQS 故障排查
│   └── assets/
│       └── example-config.yaml    # 队列/消息配置示例
│
├── aws-sns-ops/                   # SNS 操作技能
│   ├── SKILL.md                   # 精简版 - Topic/Subscription 操作
│   ├── references/
│   │   ├── aws-cli-usage.md       # SNS CLI 命令详解
│   │   ├── boto3-sdk-usage.md     # SNS SDK 代码示例
│   │   ├── core-concepts.md       # 主题, 订阅, 过滤
│   │   └── troubleshooting.md     # SNS 故障排查
│   └── assets/
│       └── example-config.yaml    # 主题/订阅配置示例
│
├── aws-cloudfront-ops/              # CloudFront 操作技能
│   ├── SKILL.md                     # 精简版 - CDN 操作
│   ├── references/
│   │   ├── aws-cli-usage.md         # CloudFront CLI 命令详解
│   │   ├── boto3-sdk-usage.md       # CloudFront SDK 代码示例
│   │   ├── core-concepts.md         # CDN, 缓存行为
│   │   └── troubleshooting.md       # CloudFront 故障排查
│   └── assets/
│       └── example-config.yaml      # 缓存/来源配置示例
│
├── aws-stepfunctions-ops/           # Step Functions 操作技能
│   ├── SKILL.md                     # 精简版 - 状态机操作
│   ├── references/
│   │   ├── aws-cli-usage.md         # Step Functions CLI 命令详解
│   │   ├── boto3-sdk-usage.md       # Step Functions SDK 代码示例
│   │   ├── core-concepts.md         # 状态机, 工作流
│   │   └── troubleshooting.md       # Step Functions 故障排查
│   └── assets/
│       └── example-config.yaml      # 工作流配置示例
│
└── aws-[service]-ops/               # 后续服务技能...
```

## 设计原则

### SKILL.md 精简
- 只关注 **What to do**: 触发条件、范围、执行流程概览
- ~70-120 行，Agent 可快速理解意图

### references 承载细节
- **How to do**: CLI 命令、SDK 代码、故障排查等
- 详细实现放在独立文件，按需加载

### 双路径执行
- **Primary**: AWS CLI (`aws [service] [command] --output json`)
- **Fallback**: boto3 SDK (CLI 失败后 3 次重试)

### 流程模式
```
Pre-flight → Execute → Validate → Recover
```

## 快速开始

### 使用 Meta Skill 生成新技能

当 Agent 加载 `aws-skill-generator` 后，提供以下信息：

```
Product: AWS [服务名]
Primary Resource: [资源类型]
Official Docs: https://docs.aws.amazon.com/[service]/
CLI Support: aws [service] help
SDK Module: boto3.client('[service]')
Operations: create, describe, list, modify, delete
```

Agent 将自动生成 `aws-[service]-ops` 目录结构。

### 使用现有技能

加载对应技能后，Agent 可执行：

```bash
# EC2 示例
aws ec2 run-instances --image-id ami-xxx --instance-type t3.micro --output json
aws ec2 describe-instances --instance-ids i-xxx --output json
aws ec2 stop-instances --instance-ids i-xxx --output json
```

## 环境设置

**前置要求**: Python >= 3.10

```bash
# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 创建环境 (需要 Python >= 3.10)
uv venv --python 3.10
source .venv/bin/activate
uv pip install awscli boto3

# 配置凭证
export AWS_ACCESS_KEY_ID="your_key"
export AWS_SECRET_ACCESS_KEY="your_secret"
export AWS_DEFAULT_REGION="us-east-1"

# 验证
aws sts get-caller-identity --output json
```

## 已有技能

| 技能 | 服务 | 状态 |
|------|------|------|
| aws-skill-generator | Meta Skill | ✅ 完成 |
| aws-ec2-ops | EC2 (虚拟机) | ✅ 完成 |
| aws-s3-ops | S3 (对象存储) | ✅ 完成 |
| aws-cloudwatch-ops | CloudWatch (监控) | ✅ 完成 |
| aws-iam-ops | IAM (身份管理) | ✅ 完成 |
| aws-elb-ops | ELB (负载均衡) | ✅ 完成 |
| aws-eks-ops | EKS (Kubernetes) | ✅ 完成 |
| aws-lambda-ops | Lambda (函数计算) | ✅ 完成 |
| aws-vpc-ops | VPC (网络) | ✅ 完成 |
| aws-rds-ops | RDS (数据库) | ✅ 完成 |
| aws-elasticache-ops | ElastiCache (Redis/Memcached) | ✅ 完成 |
| aws-dynamodb-ops | DynamoDB (NoSQL) | ✅ 完成 |
| aws-cloudtrail-ops | CloudTrail (审计) | ✅ 完成 |
| aws-kms-ops | KMS (加密) | ✅ 完成 |
| aws-route53-ops | Route53 (DNS) | ✅ 完成 |
| aws-secretsmanager-ops | Secrets Manager | ✅ 完成 |
| aws-sqs-ops | SQS (消息队列) | ✅ 完成 |
| aws-sns-ops | SNS (通知) | ✅ 完成 |
| aws-cloudfront-ops | CloudFront (CDN) | ✅ 完成 |
| aws-stepfunctions-ops | Step Functions | ✅ 完成 |

## 参考

- [AWS CLI Documentation](https://docs.aws.amazon.com/cli/)
- [boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [Agent Skills OpenSpec](https://agentskills.io/specification)

## License

MIT
