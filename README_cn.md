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

└── aws-[service]-ops/             # 后续服务技能...
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
| aws-rds-ops | RDS (数据库) | 📋 待创建 |
| aws-vpc-ops | VPC (网络) | 📋 待创建 |
| aws-lambda-ops | Lambda (函数计算) | 📋 待创建 |
| aws-iam-ops | IAM (身份管理) | ✅ 完成 |

## 参考

- [AWS CLI Documentation](https://docs.aws.amazon.com/cli/)
- [boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [Agent Skills OpenSpec](https://agentskills.io/specification)

## License

MIT
