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

├── aws-autoscaling-ops/           # Auto Scaling 操作技能
│   ├── SKILL.md                   # 精简版 - ASG/策略/实例刷新操作
│   ├── references/
│   │   ├── aws-cli-usage.md       # Auto Scaling CLI 命令详解
│   │   ├── boto3-sdk-usage.md     # Auto Scaling SDK 代码示例
│   │   ├── core-concepts.md       # ASG 架构/配额/流程
│   │   ├── troubleshooting.md     # Auto Scaling 故障排查
│   │   ├── rubric.md              # GCL 评分标准
│   │   └── prompt-templates.md    # GCL 提示模板
│   └── assets/
│       └── example-config.yaml    # ASG/策略/调度配置示例
│
├── aws-config-ops/                 # Config 操作技能
│   ├── SKILL.md                   # 精简版 - 配置记录器/规则/合规操作
│   ├── references/
│   │   ├── aws-cli-usage.md       # Config CLI 命令详解
│   │   ├── boto3-sdk-usage.md     # Config SDK 代码示例
│   │   ├── core-concepts.md       # Config 架构/配额/规则
│   │   ├── troubleshooting.md     # Config 故障排查
│   │   ├── rubric.md              # GCL 评分标准
│   │   └── prompt-templates.md    # GCL 提示模板
│   └── assets/
│       └── example-config.yaml    # 记录器/规则配置示例
│
├── aws-eventbridge-ops/            # EventBridge 操作技能
│   ├── SKILL.md                   # 精简版 - 事件总线/规则/调度器操作
│   ├── references/
│   │   ├── aws-cli-usage.md       # EventBridge CLI 命令详解
│   │   ├── boto3-sdk-usage.md     # EventBridge SDK 代码示例
│   │   ├── core-concepts.md       # 事件总线/规则/管道架构
│   │   ├── troubleshooting.md     # EventBridge 故障排查
│   │   ├── rubric.md              # GCL 评分标准
│   │   └── prompt-templates.md    # GCL 提示模板
│   └── assets/
│       └── example-config.yaml    # 规则/调度器/管道配置示例
│
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
├── aws-aurora-ops/           # Aurora 集群操作技能
│   ├── SKILL.md              # Aurora 集群、故障转移、Global DB、Serverless v2、AIOps
│   ├── references/
│   │   ├── aws-cli-usage.md  # Aurora/RDS 集群 CLI + AIOps 指标采集
│   │   ├── boto3-sdk-usage.md # Aurora 集群 SDK 模式
│   │   ├── core-concepts.md  # 集群架构、AIOps Metrics Map
│   │   ├── prompt-examples.md # 8 个 AIOps 用户 Prompt
│   │   ├── layered-inspection-template.md # 健康巡检 + RCA 模板
│   │   ├── rubric.md         # GCL 评分标准（required）
│   │   ├── prompt-templates.md # GCL G/C/O 提示模板
│   │   └── troubleshooting.md # Aurora 集群故障排查
│   └── assets/
│       └── example-config.yaml # 集群/Serverless/Global DB 示例
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
├── aws-securityhub-ops/           # Security Hub 操作技能
│   ├── SKILL.md                   # 精简版 - Security Hub/安全发现/合规标准操作
│   ├── references/
│   │   ├── aws-cli-usage.md       # Security Hub CLI 命令详解
│   │   ├── boto3-sdk-usage.md     # Security Hub SDK 代码示例
│   │   ├── core-concepts.md       # Security Hub 架构/标准/控制项
│   │   ├── troubleshooting.md     # Security Hub 故障排查
│   │   ├── rubric.md              # GCL 评分标准
│   │   └── prompt-templates.md    # GCL 提示模板
│   └── assets/
│       └── example-config.yaml    # 洞察/操作目标/自动化规则配置示例
│
├── aws-acm-ops/                   # ACM 操作技能
│   ├── SKILL.md                   # 精简版 - 证书操作
│   ├── references/
│   │   ├── aws-cli-usage.md       # ACM CLI 命令详解
│   │   ├── boto3-sdk-usage.md     # ACM SDK 代码示例
│   │   ├── core-concepts.md       # 证书生命周期/验证
│   │   ├── troubleshooting.md     # ACM 故障排查
│   │   ├── rubric.md              # GCL 评分标准
│   │   └── prompt-templates.md    # GCL 提示模板
│   └── assets/
│       └── example-config.yaml    # 证书配置示例
│
├── aws-guardduty-ops/             # GuardDuty 操作技能
│   ├── SKILL.md                   # 精简版 - 威胁检测操作
│   ├── references/
│   │   ├── aws-cli-usage.md       # GuardDuty CLI 命令详解
│   │   ├── boto3-sdk-usage.md     # GuardDuty SDK 代码示例
│   │   ├── core-concepts.md       # 威胁检测/发现/探测器
│   │   ├── troubleshooting.md     # GuardDuty 故障排查
│   │   ├── rubric.md              # GCL 评分标准
│   │   └── prompt-templates.md    # GCL 提示模板
│   └── assets/
│       └── example-config.yaml    # 探测器/过滤器配置示例
│
├── aws-opensearch-ops/            # OpenSearch 操作技能
│   ├── SKILL.md                   # 精简版 - OpenSearch 域操作
│   ├── references/
│   │   ├── aws-cli-usage.md       # OpenSearch CLI 命令详解
│   │   ├── boto3-sdk-usage.md     # OpenSearch SDK 代码示例
│   │   ├── core-concepts.md       # OpenSearch 架构/版本
│   │   ├── troubleshooting.md     # OpenSearch 故障排查
│   │   ├── rubric.md              # GCL 评分标准
│   │   └── prompt-templates.md    # GCL 提示模板
│   └── assets/
│       └── example-config.yaml    # 域/策略配置示例
│
├── aws-ssm-ops/                   # SSM 操作技能
│   ├── SKILL.md                   # 精简版 - Systems Manager 操作
│   ├── references/
│   │   ├── aws-cli-usage.md       # SSM CLI 命令详解
│   │   ├── boto3-sdk-usage.md     # SSM SDK 代码示例
│   │   ├── core-concepts.md       # SSM 架构/文档/参数
│   │   ├── troubleshooting.md     # SSM 故障排查
│   │   ├── rubric.md              # GCL 评分标准
│   │   └── prompt-templates.md    # GCL 提示模板
│   └── assets/
│       └── example-config.yaml    # SSM 配置示例
│
├── aws-waf-ops/                   # WAF 操作技能
│   ├── SKILL.md                   # 精简版 - WAF 规则/WebACL 操作
│   ├── references/
│   │   ├── aws-cli-usage.md       # WAF CLI 命令详解
│   │   ├── boto3-sdk-usage.md     # WAF SDK 代码示例
│   │   ├── core-concepts.md       # WAF 规则/WebACL/速率限制
│   │   ├── troubleshooting.md     # WAF 故障排查
│   │   ├── rubric.md              # GCL 评分标准
│   │   └── prompt-templates.md    # GCL 提示模板
│   └── assets/
│       └── example-config.yaml    # WAF 规则配置示例
│
├── aws-athena-ops/              # Athena 操作技能
│   ├── SKILL.md                  # 精简版 - 查询/工作组/数据目录操作
│   ├── references/
│   │   ├── aws-cli-usage.md      # Athena CLI 命令详解
│   │   ├── boto3-sdk-usage.md    # Athena SDK 代码示例
│   │   ├── core-concepts.md      # 查询引擎/数据目录架构
│   │   ├── troubleshooting.md    # Athena 故障排查
│   │   ├── rubric.md             # GCL 评分标准
│   │   └── prompt-templates.md   # GCL 提示模板
│   └── assets/
│       └── example-config.yaml   # 工作组/查询/目录配置示例
│
├── aws-ram-ops/                 # RAM 操作技能
│   ├── SKILL.md                  # 精简版 - 资源共享/权限操作
│   ├── references/
│   │   ├── aws-cli-usage.md      # RAM CLI 命令详解
│   │   ├── boto3-sdk-usage.md    # RAM SDK 代码示例
│   │   ├── core-concepts.md      # 跨账户共享/权限架构
│   │   ├── troubleshooting.md    # RAM 故障排查
│   │   ├── rubric.md             # GCL 评分标准
│   │   └── prompt-templates.md   # GCL 提示模板
│   └── assets/
│       └── example-config.yaml   # 资源共享/权限配置示例
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

### 方式一: .env 文件 (推荐)

```bash
# 复制模板并填写凭证
cp .env.example .env

# 编辑 .env 文件,填入 AWS 凭证
# AWS_ACCESS_KEY_ID=your_key
# AWS_SECRET_ACCESS_KEY=your_secret
# AWS_DEFAULT_REGION=us-east-1

# 安装 uv 和依赖
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv --python 3.10
source .venv/bin/activate
uv pip install awscli boto3

# 验证 (凭证从 .env 文件加载)
aws sts get-caller-identity --output json
```

### 方式二: Shell 环境变量

```bash
# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 创建环境 (需要 Python >= 3.10)
uv venv --python 3.10
source .venv/bin/activate
uv pip install awscli boto3

# 通过 shell 配置凭证
export AWS_ACCESS_KEY_ID="your_key"
export AWS_SECRET_ACCESS_KEY="your_secret"
export AWS_DEFAULT_REGION="us-east-1"

# 验证
aws sts get-caller-identity --output json
```

### 方式三: AWS CLI 配置文件

使用 AWS CLI 原生配置文件。适合已经习惯 `aws configure` 的用户。

**~/.aws/credentials**
```ini
[default]
aws_access_key_id = your_access_key
aws_secret_access_key = your_secret_key
```

**~/.aws/config**
```ini
[default]
region = us-east-1
output = json
```

```bash
# 安装 uv 和依赖
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv --python 3.10
source .venv/bin/activate
uv pip install awscli boto3

# 验证 (凭证从 ~/.aws/credentials 加载)
aws sts get-caller-identity --output json
```

**注意**: `.env` 文件已被 `.gitignore` 阻止 — 永勿提交真实凭证。

## 已有技能

| 技能 | 服务 | 状态 |
|------|------|------|
| aws-aiops-orchestrator | **跨服务 AIOps 编排器** | ✅ **完成 v0.1.0 (新增)** — 见下方 [§AIOps 编排器](#aiops-编排器) |
| aws-security-copilot | **跨服务 SecOps 编排器** (GuardDuty, SecurityHub, Config, IAM, Secrets, KMS, CloudTrail) | ✅ **完成 v0.1.0 (新增)** |
| aws-apigateway-ops | API Gateway (REST/HTTP API) | ✅ 完成 v1.0.0 |
| aws-skill-generator | Meta Skill | ✅ 完成 v1.1.0 |
| aws-ec2-ops | EC2 (虚拟机) | ✅ 完成 v1.4.0 |
| aws-ecs-ops | ECS (容器编排) | ✅ **完成 v1.2.0** — AIOps+FinOps 信号（Container Insights、Fargate Spot、Tag 治理、部署健康）；委托给 aws-finops-core 和 aws-application-autoscaling-ops |
| aws-application-autoscaling-ops | Application Auto Scaling（跨服务 scaler） | ✅ **完成 v1.1.0** — ECS / Lambda / DynamoDB / Spot Fleet（按 namespace 专属指标的 target tracking / step scaling）；4 条 cruise inference rule（`PD/CO/FD-AUTOSCALING-01`） + RB-AUTOSCALING-01；委托给 aws-finops-core 并接入 AIOps 自愈 |
| aws-autoscaling-ops | Auto Scaling (ASG) | ✅ 完成 v1.1.0 |
| aws-config-ops | Config (合规) | ✅ 完成 v1.0.0 |
| aws-eventbridge-ops | EventBridge (事件总线) | ✅ 完成 v1.1.0 |
| aws-s3-ops | S3 (对象存储) | ✅ 完成 v1.1.0 |
| aws-cloudwatch-ops | CloudWatch (监控) | ✅ 完成 v2.5.0 |
| aws-iam-ops | IAM (身份管理) | ✅ 完成 v1.1.0 |
| aws-elb-ops | ELB (负载均衡) | ✅ 完成 v2.4.0 |
| aws-eks-ops | EKS (Kubernetes) | ✅ 完成 v1.0.0 |
| aws-lambda-ops | Lambda (函数计算) | ✅ 完成 v1.2.0 |
| aws-vpc-ops | VPC (网络) | ✅ 完成 v1.3.0 |
| aws-rds-ops | RDS (数据库) | ✅ 完成 v1.2.0 |
| aws-aurora-ops | Aurora (MySQL/PostgreSQL 集群) | ✅ 完成 v1.2.0 |
| aws-elasticache-ops | ElastiCache (Redis/Memcached) | ✅ 完成 v1.1.0 |
| aws-dynamodb-ops | DynamoDB (NoSQL) | ✅ 完成 v1.3.0 |
| aws-ecr-ops | ECR (容器镜像仓库) | ✅ 完成 v1.0.0 |
| aws-ebs-ops | EBS (块存储) | ✅ 完成 v1.0.0 |
| aws-efs-ops | EFS (弹性文件系统) | ✅ 完成 v1.0.0 |
| aws-cloudtrail-ops | CloudTrail (审计) | ✅ 完成 v1.1.0 |
| aws-kms-ops | KMS (加密) | ✅ 完成 v2.1.0 |
| aws-route53-ops | Route53 (DNS) | ✅ 完成 v1.2.0 |
| aws-secretsmanager-ops | Secrets Manager | ✅ 完成 v1.0.0 |
| aws-sqs-ops | SQS (消息队列) | ✅ 完成 v1.1.0 |
| aws-sns-ops | SNS (通知) | ✅ 完成 v1.1.0 |
| aws-cloudfront-ops | CloudFront (CDN) | ✅ 完成 v1.1.0 |
| aws-ssm-ops | SSM (Systems Manager) | ✅ 完成 v1.0.0 |
| aws-stepfunctions-ops | Step Functions | ✅ 完成 v1.1.0 |
| aws-waf-ops | WAF (Web Application Firewall) | ✅ 完成 v1.0.0 |
| aws-acm-ops | ACM (Certificate Manager) | ✅ 完成 v1.0.0 |
| aws-opensearch-ops | OpenSearch Service (托管 Elasticsearch) | ✅ 完成 v1.0.0 |
| aws-guardduty-ops | GuardDuty (威胁检测) | ✅ 完成 v1.0.0 |
| aws-securityhub-ops | Security Hub (安全发现/合规) | ✅ 完成 v1.0.0 |
| aws-athena-ops | Athena (无服务器 SQL 查询) | ✅ 完成 v1.1.0 |
| aws-ram-ops | RAM (跨账户资源共享) | ✅ 完成 v1.3.0 |
| aws-topo-discovery | 跨产品拓扑发现 | ✅ 完成 v1.1.0 |
| aws-aiops-cruise | **全链路 AIOps 巡检（只读）** | ✅ **完成 v2.2.0** — 见 [§AIOps 巡检](#aiops-巡检) |

## AIOps 巡检

**`aws-aiops-cruise`** 是 **只读全链路巡航技能**（EIP → ALB → EC2 → RDS/ElastiCache → NAT → 安全组），与下列技能分工：

| 技能 | 职责 |
|------|------|
| `aws-topo-discovery` | 静态拓扑 + HCL/基线 |
| `aws-aiops-cruise` | 定时健康巡检 + 7 个感知 Agent + runbook 01–09 |
| `aws-aiops-orchestrator` | 跨服务 RCA、自愈编排、成本预测 |

快速开始：

```bash
python3 aws-aiops-cruise/runbooks/scripts/daily-health-check.py \
  --resource-group prod-web-rg --region us-east-1 \
  --render-topology --non-interactive
```

## SecOps 编排器（新增 — v0.1.0）

**`aws-security-copilot`** 是统一 SecOps 入口，与 AIOps、FinOps 并列为第三大运维支柱：

| 技能 | 职责 |
|------|------|
| `aws-aiops-cruise` | 只读健康巡检 |
| `aws-aiops-orchestrator` | 跨服务 RCA 和编排 |
| `aws-finops-core` | 成本异常和闲置资源 |
| `aws-security-copilot` | 安全态势、告警发现、事件响应 |

见 [`aws-security-copilot/SKILL.md`](aws-security-copilot/SKILL.md)。

## AIOps 编排器

**`aws-aiops-orchestrator`** 是构建在所有 `aws-*-ops` 技能之上的**跨服务大脑**。它不直接执行 AWS 操作，而是：

1. **路由**：通过标准化的 `aiops_delegate` 信封，将用户意图（健康检查、RCA、自愈、成本/容量预测、变更影响）分发到合适的 `aws-*-ops` 技能。
2. **关联**：跨服务关联指标、日志、事件、配置、成本信号 —— 一个症状往往横跨 3+ 个服务。
3. **驱动多技能修复**：通过 22 个标准 runbook（RB-001 … RB-022）。
4. **全局预测**：借助 CloudWatch FORECAST、Cost Explorer、Compute Optimizer 提供全局容量与成本预测。
5. **复用 6 层闭环蓝图**：直接复用 [`aws-elb-ops/references/aiops-automation-engine.md`](aws-elb-ops/references/aiops-automation-engine.md) 的设计模式（Data Collection → Detection → RCA → Decision → Action → Feedback）。

### 何时使用编排器

| 用编排器 | 用具体技能 |
|---------|----------|
| 跨服务健康（"线上还好吗？""网站很慢"） | 单服务创建/修改/删除 |
| 跨服务 RCA（"为什么 502""为什么延迟"） | 具体的 CloudWatch / IAM / S3 设置 |
| 跨服务成本预测 | 单资源查询 |
| 多技能协同自愈 | 单技能自愈（如 ELB target re-register） |
| 变更影响 / 爆炸半径分析 | 直接 console 式交互 |

### 文件结构

```
aws-aiops-orchestrator/
├── SKILL.md                          # 主入口（440 行）
├── references/
│   ├── delegate-routing.md           # 委派契约 + 路由矩阵
│   ├── delegate-adapter-patch.md     # 下游技能适配补丁规范
│   ├── correlation-graph.md          # 资源依赖图模型
│   ├── detection-rules.md            # 53 条检测规则（FD/PD/CO/SD/CD）
│   └── runbook-recipes.md            # 22 个 runbook（RB-001…RB-022）
└── assets/
    ├── example-scope-graph.yaml      # 依赖图示例
    └── cost-forecast-template.json   # 成本预测输出 schema
```

### 检测规则覆盖（53 条）

| 领域 | 数量 | 示例规则 | 涉及技能 |
|------|------|----------|----------|
| **FD — 故障检测** | 20 | FD-01 target 抖动、FD-03 5xx 飙升、FD-06 status check、FD-07a 内存压力、FD-07b IOPS 饱和、FD-07e 网络带宽、FD-10 ALL unhealthy、FD-11 Lambda throttle | elb、cloudwatch、ec2、rds、lambda、vpc、opensearch |
| **PD — 预测** | 7 | PD-01 证书到期、PD-03 RDS 存储、PD-05 LCU 预测、PD-07 成本超支 | cloudwatch (FORECAST)、acm、rds、Cost Explorer |
| **CO — 成本优化** | 9 | CO-01 空闲 ALB、CO-03 空闲 NAT GW、CO-04 未挂载 EBS、CO-07 RDS 过大、CO-09 成本异常 | elb、vpc、ec2、Compute Optimizer |
| **SD — 安全检测** | 7 | SD-01 GuardDuty CRITICAL、SD-02 S3 公开、SD-03 SG 0.0.0.0/0、SD-04 IAM 凭据泄露 | guardduty、securityhub、s3、iam、kms |
| **CD — 变更检测** | 5 | CD-01 SG 漂移、CD-02 IAM 附加、CD-04 RDS 删除、CD-05 变更前基线 | cloudtrail、config、iam |

### Runbook 库（22 个）

| ID 范围 | 覆盖场景 |
|---------|----------|
| RB-001…RB-010 | 核心 LB/EC2/RDS/Cert/Cost 事件 |
| RB-011…RB-014 | Lambda + VPC + SG（限流、迭代器龄、流量日志异常、SG 漂移） |
| RB-015…RB-017 | 存储 + 安全（EBS 满、KMS 合规、IAM 凭据泄露） |
| RB-018…RB-022 | 缓存 + 搜索 + 成本 + DNS（ElastiCache、OpenSearch、S3 生命周期、多区域故障切换、成本尖峰） |

### 委派适配补丁（v0.1）

要让下游技能变成 "orchestrator-aware"，应用
[`aws-aiops-orchestrator/references/delegate-adapter-patch.md`](aws-aiops-orchestrator/references/delegate-adapter-patch.md) 中的标准补丁。补丁会：

1. 在 skill 的 YAML frontmatter 增加 `metadata.orchestrator_aware`、`orchestrator_compat`、`delegate:` 键。
2. 在 `SKILL.md` 末尾追加 `## AIOps Delegate Contract` 章节。

**当前适配状态**（迁移顺序见补丁文档 §5）：

| 优先级 | 技能 | 状态 |
|--------|------|------|
| **P0**（核心）| cloudwatch、elb、ec2、rds、vpc、acm、route53、waf | ✅ 已打补丁 |
| **P1**（数据 + 执行器）| cloudtrail、config、autoscaling、kms、iam、guardduty、securityhub、s3 | ✅ 已打补丁 |
| **P2**（可选）| lambda、stepfunctions、eventbridge、sns、sqs、ssm、secretsmanager、elasticache、opensearch、dynamodb、cloudfront、eks、athena、ram | ⏳ 待办（按需） |

批量应用：使用 `scripts/apply_aiops_adapter_patch.py`（幂等）。

### 版本历史

| 技能 | 旧版 | 新版 | 变更说明 |
|------|------|------|----------|
| `aws-aiops-orchestrator` | — | **v0.1.0（新增）** | **跨服务编排器**：53 条检测规则、22 个 runbook、16 个已打补丁的下游技能；桥接单服务 AIOps 为端到端 RCA + 协同修复 |
| `aws-elb-ops` | v1.0.0 | **v2.2.0** | AIOps 场景、自愈、RCA、成本优化、变更管理；**已适配编排器（P0）** |
| `aws-cloudwatch-ops` | v2.3.0 | **v2.5.0** | 模板对齐重构: 20 个 Operation 块、Config File Placeholders、拆分 Pre-flight、ASCII 图、TE 章节、保留 AIOps 内容 |
| `aws-ec2-ops` | v1.1.0 | **v1.4.0** | 模板对齐重构；**GCL 试点** + **已适配编排器** |
| `aws-vpc-ops` | v1.1.0 | **v1.1.0+** | Flow Log 分析、SG 漂移检测、网络 RCA；**已适配编排器（P0）** |
| `aws-rds-ops` | v1.2.0 | **v1.2.0+** | DB 诊断、RDS 连接；**已适配编排器（P0）** |
| `aws-acm-ops` | — | **v1.0.0（新增）** | 证书生命周期、到期监控、自动续期；**已适配编排器（P0）** |
| `aws-route53-ops` | v1.0.0 | **v1.0.0+** | DNS 故障转移自动化、健康检查 ELB 集成；**已适配编排器（P0）** |
| `aws-waf-ops` | — | **v1.0.0（新增）** | WAF AIOps：流量异常、速率限制、托管规则、规则审计；**已适配编排器（P0）** |
| `aws-autoscaling-ops` | — | **v1.0.0（新增）** | ASG 管理、扩缩策略、实例刷新、生命周期钩子、容量治理；**GCL** + **已适配编排器（P1）** |
| `aws-config-ops` | — | **v1.0.0（新增）** | 配置记录器、投递通道、托管/自定义规则、合规包、聚合器、合规评估；**GCL** + **已适配编排器（P1）** |
| `aws-eventbridge-ops` | — | **v1.0.0（新增）** | 事件总线、规则/目标、API 目标、连接、归档/重放、调度器、管道；**GCL** + **已适配编排器（P2 待办）** |
| `aws-cloudtrail-ops` | v1.0.0 | **v1.1.0+** | API 事件关联、变更时间线；**已适配编排器（P1）** |
| `aws-s3-ops` | v1.0.0 | **v1.1.0** | 生命周期缺口检测、公开访问审计、成本优化；**GCL 试点** + **已适配编排器（P1）** |
| `aws-iam-ops` | v1.0.0 | **v1.1.0** | 凭据泄露响应、IAM 附加追踪；**GCL 试点** + **已适配编排器（P1）** |
| `aws-kms-ops` | v1.0.0 | **v2.1.0** | 密钥合规性、轮换、删除保护；**GCL 试点** + **已适配编排器（P1）** |
| `aws-guardduty-ops` | — | **v1.0.0（新增）** | 威胁检测、发现关联；**已适配编排器（P1）** |
| `aws-securityhub-ops` | — | **v1.0.0（新增）** | 安全评分、合规标准聚合；**已适配编排器（P1）** |

### 完整覆盖统计

- **30** 个 ops 技能（含 1 个 meta-skill）
- **16** 个技能已应用 orchestrator 适配补丁（P0 + P1）
- **47** 条检测规则（FD/PD/CO/SD/CD）
- **22** 个标准 runbook（RB-001 … RB-022）
- **6** 层 AIOps 闭环（Data Collection → Detection → RCA → Decision → Action → Feedback）

## 质量门 (GCL)

本仓库在所有高副作用技能执行中采用 **Generator-Critic-Loop (GCL)** 对抗式质量门。完整规范位于
[`aws-skill-generator/references/gcl-spec.md`](aws-skill-generator/references/gcl-spec.md)；
顶层索引位于 `AGENTS.md` §11。

全部 **30 个技能** 现已完成 GCL 实现：

| 阶段 | 技能 | 类别 | 日期 |
|---|---|---|---|
| **试点** | `aws-ec2-ops`、`aws-iam-ops`、`aws-kms-ops`、`aws-s3-ops` | required | 2026-06-04 |
| **Group 1** | `aws-rds-ops`、`aws-lambda-ops`、`aws-dynamodb-ops` | required | 2026-06-04 |
| **Group 2** | `aws-vpc-ops`、`aws-route53-ops`、`aws-cloudfront-ops`、`aws-elb-ops` | required/recommended | 2026-06-04 |
| **Group 3** | `aws-elasticache-ops`、`aws-waf-ops`、`aws-secretsmanager-ops`、`aws-ssm-ops`、`aws-acm-ops`、`aws-eks-ops`、`aws-sqs-ops`、`aws-sns-ops`、`aws-stepfunctions-ops`、`aws-cloudwatch-ops`、`aws-cloudtrail-ops` | required/recommended/optional | 2026-06-04 |
| **Group 4** | `aws-autoscaling-ops` | required | 2026-06-07 |
| **Group 5** | `aws-config-ops`、`aws-eventbridge-ops` | recommended | 2026-06-07 |
| **Group 6** | `aws-guardduty-ops`、`aws-opensearch-ops`、`aws-securityhub-ops` | required | 2026-06-08 |
| **Group 7** | `aws-athena-ops`、`aws-ram-ops` | required | 2026-06-10 |

- **5 维度评分** (0 / 0.5 / 1): 正确性、安全性、幂等性、可追溯性、规范合规性。**Safety = 0 → 立即 ABORT。**
- **跟踪路径:** `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` (git-ignored)。
- **推广完成:** 所有 `required`、`recommended`、`optional` 类别技能（见 `AGENTS.md` §11.5 Per-Skill Defaults 表）均已配备 rubric.md、prompt-templates.md 及 SKILL.md 中的 `## Quality Gate (GCL)` 章节。
- **下步计划:** Phase 2 — 可复用 `scripts/gcl_runner.py` Orchestrator（计划中）。

## 参考

- [AWS CLI Documentation](https://docs.aws.amazon.com/cli/)
- [boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [Agent Skills OpenSpec](https://agentskills.io/specification)

## License

MIT
