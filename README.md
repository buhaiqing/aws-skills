# AWS Skills Repository

A collection of AWS cloud resource/service operation skills for AI Agent automated operation scenarios.

🌐 [中文版本](./README_cn.md)

## Project Structure

```
aws-skills/
├── aws-skill-generator/           # Meta Skill (Skill Generator)
│   ├── SKILL.md                   # Concise - What to do
│   ├── references/                # Detailed - How to do
│   │   ├── aws-skill-template.md  # Skill skeleton template
│   │   ├── aws-cli-conventions.md # CLI behavior conventions
│   │   ├── boto3-sdk-usage.md     # SDK usage patterns
│   │   ├── integration.md         # Environment setup
│   │   ├── core-concepts-template.md
│   │   ├── troubleshooting-template.md
│   │   └── governance-review.md   # Checklist
│   └── assets/
│       └── example-config.yaml

├── aws-ec2-ops/                   # EC2 Operations Skill
│   ├── SKILL.md                   # Concise - Trigger/Scope/Flow
│   ├── references/
│   │   ├── aws-cli-usage.md       # EC2 CLI commands
│   │   ├── boto3-sdk-usage.md     # EC2 SDK code examples
│   │   ├── core-concepts.md       # EC2 architecture/quota
│   │   └── troubleshooting.md    # EC2 troubleshooting
│   └── assets/

├── aws-autoscaling-ops/           # Auto Scaling Operations Skill
│   ├── SKILL.md                   # Concise - ASG/Policy/Refresh ops
│   ├── references/
│   │   ├── aws-cli-usage.md       # Auto Scaling CLI commands
│   │   ├── boto3-sdk-usage.md     # Auto Scaling SDK code examples
│   │   ├── core-concepts.md       # ASG architecture/quota
│   │   ├── troubleshooting.md     # Auto Scaling troubleshooting
│   │   ├── rubric.md              # GCL scoring rubric
│   │   └── prompt-templates.md    # GCL prompt templates
│   └── assets/
│       └── example-config.yaml    # ASG/Policy/Schedule config
│
├── aws-config-ops/               # Config Operations Skill
│   ├── SKILL.md                   # Concise - Recorder/Rule/Compliance ops
│   ├── references/
│   │   ├── aws-cli-usage.md       # Config CLI commands
│   │   ├── boto3-sdk-usage.md     # Config SDK code examples
│   │   ├── core-concepts.md       # Config architecture/quota
│   │   ├── troubleshooting.md     # Config troubleshooting
│   │   ├── rubric.md              # GCL scoring rubric
│   │   └── prompt-templates.md    # GCL prompt templates
│   └── assets/
│       └── example-config.yaml    # Recorder/Rule config
│
├── aws-eventbridge-ops/          # EventBridge Operations Skill
│   ├── SKILL.md                   # Concise - EventBus/Rule/Schedule ops
│   ├── references/
│   │   ├── aws-cli-usage.md       # EventBridge CLI commands
│   │   ├── boto3-sdk-usage.md     # EventBridge SDK code examples
│   │   ├── core-concepts.md       # EventBridge architecture/quota
│   │   ├── troubleshooting.md     # EventBridge troubleshooting
│   │   ├── rubric.md              # GCL scoring rubric
│   │   └── prompt-templates.md    # GCL prompt templates
│   └── assets/
│       └── example-config.yaml    # Rule/Schedule/Pipe config
│
├── aws-s3-ops/                    # S3 Operations Skill
│   ├── SKILL.md                   # Concise - Bucket/Object operations
│   ├── references/
│   │   ├── aws-cli-usage.md       # S3 CLI commands
│   │   ├── boto3-sdk-usage.md     # S3 SDK code examples
│   │   ├── core-concepts.md       # S3 storage class/quota
│   │   └── troubleshooting.md    # S3 troubleshooting
│   └── assets/
│       └── example-config.yaml    # Policy/Lifecycle examples

├── aws-cloudwatch-ops/            # CloudWatch Operations Skill
│   ├── SKILL.md                   # Concise - Metrics/Alarms operations
│   ├── references/
│   │   ├── aws-cli-usage.md       # CloudWatch CLI commands
│   │   ├── boto3-sdk-usage.md     # CloudWatch SDK code examples
│   │   ├── core-concepts.md       # Namespace/Metric structure
│   │   └── troubleshooting.md    # CloudWatch troubleshooting
│   └── assets/
│       └── example-config.yaml    # Alarm/Dashboard examples

├── aws-iam-ops/             # IAM Operations Skill
│   ├── SKILL.md             # Concise - User/Group/Role/Policy operations
│   ├── references/
│   │   ├── aws-cli-usage.md # IAM CLI commands
│   │   ├── boto3-sdk-usage.md # IAM SDK code examples
│   │   ├── core-concepts.md # IAM components/quota
│   │   └── troubleshooting.md # IAM troubleshooting
│   └── assets/
│       └── example-config.yaml # Trust/Permission Policy examples

├── aws-elb-ops/             # ELB Operations Skill
│   ├── SKILL.md             # Concise - ALB/NLB/CLB operations
│   ├── references/
│   │   ├── aws-cli-usage.md # ELB CLI commands
│   │   ├── boto3-sdk-usage.md # ELB SDK code examples
│   │   ├── core-concepts.md # Load balancer types, components
│   │   └── troubleshooting.md # ELB troubleshooting
│   └── assets/
│       └── example-config.yaml # Listener/Target Group examples
│
├── aws-eks-ops/              # EKS Operations Skill
│   ├── SKILL.md              # Concise - Cluster/NodeGroup/Fargate operations
│   ├── references/
│   │   ├── aws-cli-usage.md  # EKS CLI commands
│   │   ├── boto3-sdk-usage.md # EKS SDK code examples
│   │   ├── core-concepts.md  # Kubernetes versions, add-ons
│   │   └── troubleshooting.md # EKS troubleshooting
│   └── assets/
│       └── example-config.yaml # NodeGroup/Fargate/Addon examples
│
├── aws-lambda-ops/           # Lambda Operations Skill
│   ├── SKILL.md              # Concise - Function/Layer operations
│   ├── references/
│   │   ├── aws-cli-usage.md  # Lambda CLI commands
│   │   ├── boto3-sdk-usage.md # Lambda SDK code examples
│   │   ├── core-concepts.md  # Serverless compute, runtimes
│   │   └── troubleshooting.md # Lambda troubleshooting
│   └── assets/
│       └── example-config.yaml # Function/Layer/EventSource examples
│
├── aws-vpc-ops/              # VPC Operations Skill
│   ├── SKILL.md              # Concise - VPC/Subnet/SecurityGroup operations
│   ├── references/
│   │   ├── aws-cli-usage.md  # VPC CLI commands
│   │   ├── boto3-sdk-usage.md # VPC SDK code examples
│   │   ├── core-concepts.md  # Network architecture, CIDR
│   │   └── troubleshooting.md # VPC troubleshooting
│   └── assets/
│       └── example-config.yaml # VPC/Subnet/SG examples
│
├── aws-rds-ops/              # RDS Operations Skill
│   ├── SKILL.md              # Concise - DB Instance/Snapshot operations
│   ├── references/
│   │   ├── aws-cli-usage.md  # RDS CLI commands
│   │   ├── boto3-sdk-usage.md # RDS SDK code examples
│   │   ├── core-concepts.md  # Database engines, HA
│   │   └── troubleshooting.md # RDS troubleshooting
│   └── assets/
│       └── example-config.yaml # DB/Snapshot/ParamGroup examples
│
├── aws-aurora-ops/           # Aurora Cluster Operations Skill
│   ├── SKILL.md              # Aurora cluster, failover, Global DB, Serverless v2, AIOps
│   ├── references/
│   │   ├── aws-cli-usage.md  # Aurora/RDS cluster CLI + AIOps metrics
│   │   ├── boto3-sdk-usage.md # Aurora cluster SDK patterns
│   │   ├── core-concepts.md  # Cluster architecture, AIOps Metrics Map
│   │   ├── prompt-examples.md # 8 AIOps user prompts
│   │   ├── layered-inspection-template.md # Health check + RCA template
│   │   ├── rubric.md         # GCL rubric (required)
│   │   ├── prompt-templates.md # GCL G/C/O prompts
│   │   └── troubleshooting.md # Aurora cluster troubleshooting
│   └── assets/
│       └── example-config.yaml # Cluster/Serverless/Global DB examples
│
├── aws-elasticache-ops/      # ElastiCache Operations Skill
│   ├── SKILL.md              # Concise - Redis/Memcached operations
│   ├── references/
│   │   ├── aws-cli-usage.md  # ElastiCache CLI commands
│   │   ├── boto3-sdk-usage.md # ElastiCache SDK code examples
│   │   ├── core-concepts.md  # Redis vs Memcached, node types
│   │   └── troubleshooting.md # ElastiCache troubleshooting
│   └── assets/
│       └── example-config.yaml # Redis/Memcached config examples
│
├── aws-dynamodb-ops/              # DynamoDB Operations Skill
│   ├── SKILL.md                   # Concise - Table/Item/GSI operations
│   ├── references/
│   │   ├── aws-cli-usage.md       # DynamoDB CLI commands
│   │   ├── boto3-sdk-usage.md     # DynamoDB SDK code examples
│   │   ├── core-concepts.md       # NoSQL, capacity modes, indexing
│   │   └── troubleshooting.md     # DynamoDB troubleshooting
│   └── assets/
│       └── example-config.yaml    # Table/GSI/Item examples
│
├── aws-cloudtrail-ops/            # CloudTrail Operations Skill
│   ├── SKILL.md                   # Concise - Trail/Event operations
│   ├── references/
│   │   ├── aws-cli-usage.md       # CloudTrail CLI commands
│   │   ├── boto3-sdk-usage.md     # CloudTrail SDK code examples
│   │   ├── core-concepts.md       # Audit trails, event types
│   │   └── troubleshooting.md     # CloudTrail troubleshooting
│   └── assets/
│       └── example-config.yaml    # Trail/Event configuration examples
│
├── aws-kms-ops/                   # KMS Operations Skill
│   ├── SKILL.md                   # Concise - Key/Encryption operations
│   ├── references/
│   │   ├── aws-cli-usage.md       # KMS CLI commands
│   │   ├── boto3-sdk-usage.md     # KMS SDK code examples
│   │   ├── core-concepts.md       # Encryption keys, key lifecycle
│   │   └── troubleshooting.md     # KMS troubleshooting
│   └── assets/
│       └── example-config.yaml    # Key policy/configuration examples
│
├── aws-route53-ops/               # Route53 Operations Skill
│   ├── SKILL.md                   # Concise - DNS/Hosted Zone operations
│   ├── references/
│   │   ├── aws-cli-usage.md       # Route53 CLI commands
│   │   ├── boto3-sdk-usage.md     # Route53 SDK code examples
│   │   ├── core-concepts.md       # DNS, routing policies
│   │   └── troubleshooting.md     # Route53 troubleshooting
│   └── assets/
│       └── example-config.yaml    # DNS/Health Check examples
│
├── aws-secretsmanager-ops/        # Secrets Manager Operations Skill
│   ├── SKILL.md                   # Concise - Secret/Rotation operations
│   ├── references/
│   │   ├── aws-cli-usage.md       # Secrets Manager CLI commands
│   │   ├── boto3-sdk-usage.md     # Secrets Manager SDK code examples
│   │   ├── core-concepts.md       # Secrets, rotation
│   │   └── troubleshooting.md     # Secrets Manager troubleshooting
│   └── assets/
│       └── example-config.yaml    # Secret/Rotation examples
│
├── aws-sqs-ops/                   # SQS Operations Skill
│   ├── SKILL.md                   # Concise - Queue/Message operations
│   ├── references/
│   │   ├── aws-cli-usage.md       # SQS CLI commands
│   │   ├── boto3-sdk-usage.md     # SQS SDK code examples
│   │   ├── core-concepts.md       # Queues, DLQ, FIFO
│   │   └── troubleshooting.md     # SQS troubleshooting
│   └── assets/
│       └── example-config.yaml    # Queue/Message examples
│
├── aws-sns-ops/                   # SNS Operations Skill
│   ├── SKILL.md                   # Concise - Topic/Subscription operations
│   ├── references/
│   │   ├── aws-cli-usage.md       # SNS CLI commands
│   │   ├── boto3-sdk-usage.md     # SNS SDK code examples
│   │   ├── core-concepts.md       # Topics, subscriptions, filtering
│   │   └── troubleshooting.md     # SNS troubleshooting
│   └── assets/
│       └── example-config.yaml    # Topic/Subscription examples
│
├── aws-cloudfront-ops/              # CloudFront Operations Skill
│   ├── SKILL.md                     # Concise - CDN operations
│   ├── references/
│   │   ├── aws-cli-usage.md         # CloudFront CLI commands
│   │   ├── boto3-sdk-usage.md       # CloudFront SDK code examples
│   │   ├── core-concepts.md         # CDN, cache behaviors
│   │   └── troubleshooting.md       # CloudFront troubleshooting
│   └── assets/
│       └── example-config.yaml      # Cache/Origin examples
│
├── aws-stepfunctions-ops/           # Step Functions Operations Skill
│   ├── SKILL.md                     # Concise - State machine operations
│   ├── references/
│   │   ├── aws-cli-usage.md         # Step Functions CLI commands
│   │   ├── boto3-sdk-usage.md       # Step Functions SDK code examples
│   │   ├── core-concepts.md         # State machines, workflows
│   │   └── troubleshooting.md       # Step Functions troubleshooting
│   └── assets/
│       └── example-config.yaml      # Workflow examples
│
├── aws-securityhub-ops/           # Security Hub Operations Skill
│   ├── SKILL.md                   # Concise - Security Hub/Findings/Standards operations
│   ├── references/
│   │   ├── aws-cli-usage.md       # Security Hub CLI commands
│   │   ├── boto3-sdk-usage.md     # Security Hub SDK code examples
│   │   ├── core-concepts.md       # Security Hub architecture, standards, controls
│   │   ├── troubleshooting.md     # Security Hub troubleshooting
│   │   ├── rubric.md              # GCL scoring rubric
│   │   └── prompt-templates.md    # GCL prompt templates
│   └── assets/
│       └── example-config.yaml    # Insight/ActionTarget/AutomationRule examples
│
├── aws-acm-ops/                   # ACM Operations Skill
│   ├── SKILL.md                   # Concise - Certificate operations
│   ├── references/
│   │   ├── aws-cli-usage.md       # ACM CLI commands
│   │   ├── boto3-sdk-usage.md     # ACM SDK code examples
│   │   ├── core-concepts.md       # Certificate lifecycle, validation
│   │   ├── troubleshooting.md     # ACM troubleshooting
│   │   ├── rubric.md              # GCL scoring rubric
│   │   └── prompt-templates.md    # GCL prompt templates
│   └── assets/
│       └── example-config.yaml    # Certificate config examples
│
├── aws-guardduty-ops/             # GuardDuty Operations Skill
│   ├── SKILL.md                   # Concise - Threat detection operations
│   ├── references/
│   │   ├── aws-cli-usage.md       # GuardDuty CLI commands
│   │   ├── boto3-sdk-usage.md     # GuardDuty SDK code examples
│   │   ├── core-concepts.md       # Threat detection, findings, detectors
│   │   ├── troubleshooting.md     # GuardDuty troubleshooting
│   │   ├── rubric.md              # GCL scoring rubric
│   │   └── prompt-templates.md    # GCL prompt templates
│   └── assets/
│       └── example-config.yaml    # Detector/Filter config examples
│
├── aws-opensearch-ops/            # OpenSearch Operations Skill
│   ├── SKILL.md                   # Concise - OpenSearch domain operations
│   ├── references/
│   │   ├── aws-cli-usage.md       # OpenSearch CLI commands
│   │   ├── boto3-sdk-usage.md     # OpenSearch SDK code examples
│   │   ├── core-concepts.md       # OpenSearch architecture, versions
│   │   ├── troubleshooting.md     # OpenSearch troubleshooting
│   │   ├── rubric.md              # GCL scoring rubric
│   │   └── prompt-templates.md    # GCL prompt templates
│   └── assets/
│       └── example-config.yaml    # Domain/Policy config examples
│
├── aws-ssm-ops/                   # SSM Operations Skill
│   ├── SKILL.md                   # Concise - Systems Manager operations
│   ├── references/
│   │   ├── aws-cli-usage.md       # SSM CLI commands
│   │   ├── boto3-sdk-usage.md     # SSM SDK code examples
│   │   ├── core-concepts.md       # SSM architecture, documents, parameters
│   │   ├── troubleshooting.md     # SSM troubleshooting
│   │   ├── rubric.md              # GCL scoring rubric
│   │   └── prompt-templates.md    # GCL prompt templates
│   └── assets/
│       └── example-config.yaml    # SSM config examples
│
├── aws-waf-ops/                   # WAF Operations Skill
│   ├── SKILL.md                   # Concise - WAF rule/WebACL operations
│   ├── references/
│   │   ├── aws-cli-usage.md       # WAF CLI commands
│   │   ├── boto3-sdk-usage.md     # WAF SDK code examples
│   │   ├── core-concepts.md       # WAF rules, WebACL, rate limiting
│   │   ├── troubleshooting.md     # WAF troubleshooting
│   │   ├── rubric.md              # GCL scoring rubric
│   │   └── prompt-templates.md    # GCL prompt templates
│   └── assets/
│       └── example-config.yaml    # WAF rule config examples
│
├── aws-athena-ops/              # Athena Operations Skill
│   ├── SKILL.md                  # Concise - Query/WorkGroup/Catalog operations
│   ├── references/
│   │   ├── aws-cli-usage.md      # Athena CLI commands
│   │   ├── boto3-sdk-usage.md    # Athena SDK code examples
│   │   ├── core-concepts.md      # Query engine, data catalog
│   │   ├── troubleshooting.md    # Athena troubleshooting
│   │   ├── rubric.md             # GCL scoring rubric
│   │   └── prompt-templates.md   # GCL prompt templates
│   └── assets/
│       └── example-config.yaml   # WorkGroup/Query/Catalog examples
│
├── aws-ram-ops/                 # RAM Operations Skill
│   ├── SKILL.md                  # Concise - Resource Share/Permission operations
│   ├── references/
│   │   ├── aws-cli-usage.md      # RAM CLI commands
│   │   ├── boto3-sdk-usage.md    # RAM SDK code examples
│   │   ├── core-concepts.md      # Cross-account sharing, permissions
│   │   ├── troubleshooting.md    # RAM troubleshooting
│   │   ├── rubric.md             # GCL scoring rubric
│   │   └── prompt-templates.md   # GCL prompt templates
│   └── assets/
│       └── example-config.yaml   # ResourceShare/Permission examples
│
└── aws-[service]-ops/               # More service skills...
```

## Design Principles

### SKILL.md Concise
- Focus only on **What to do**: trigger conditions, scope, execution flow overview
- ~70-120 lines for quick Agent comprehension

### References for Details
- **How to do**: CLI commands, SDK code, troubleshooting, etc.
- Detailed implementation in separate files, loaded on demand

### Dual-Path Execution
- **Primary**: AWS CLI (`aws [service] [command] --output json`)
- **Fallback**: boto3 SDK (3 retries after CLI failure)

### Workflow Pattern
```
Pre-flight → Execute → Validate → Recover
```

## Quick Start

### Generate New Skills with Meta Skill

When Agent loads `aws-skill-generator`, provide the following:

```
Product: AWS [Service Name]
Primary Resource: [Resource Type]
Official Docs: https://docs.aws.amazon.com/[service]/
CLI Support: aws [service] help
SDK Module: boto3.client('[service]')
Operations: create, describe, list, modify, delete
```

Agent will automatically generate `aws-[service]-ops` directory structure.

### Use Existing Skills

After loading the corresponding skill, Agent can execute:

```bash
# EC2 Examples
aws ec2 run-instances --image-id ami-xxx --instance-type t3.micro --output json
aws ec2 describe-instances --instance-ids i-xxx --output json
aws ec2 stop-instances --instance-ids i-xxx --output json
```

## Environment Setup

**Prerequisites**: Python >= 3.10

### Option 1: .env File (Recommended)

```bash
# Copy template and fill in credentials
cp .env.example .env

# Edit .env with your AWS credentials
# AWS_ACCESS_KEY_ID=your_key
# AWS_SECRET_ACCESS_KEY=your_secret
# AWS_DEFAULT_REGION=us-east-1

# Install uv and dependencies
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv --python 3.10
source .venv/bin/activate
uv pip install awscli boto3

# Verify (credentials loaded from .env)
aws sts get-caller-identity --output json
```

### Option 2: Shell Environment Variables

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create environment (requires Python >= 3.10)
uv venv --python 3.10
source .venv/bin/activate
uv pip install awscli boto3

# Configure credentials via shell
export AWS_ACCESS_KEY_ID="your_key"
export AWS_SECRET_ACCESS_KEY="your_secret"
export AWS_DEFAULT_REGION="us-east-1"

# Verify
aws sts get-caller-identity --output json
```

### Option 3: AWS CLI Config Files

Use AWS CLI's native configuration files. Suitable when you already use `aws configure`.

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
# Install uv and dependencies
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv --python 3.10
source .venv/bin/activate
uv pip install awscli boto3

# Verify (credentials loaded from ~/.aws/credentials)
aws sts get-caller-identity --output json
```

**Note**: `.env` file is blocked by `.gitignore` — never commit real credentials.

## Existing Skills

| Skill | Service | Status |
|-------|---------|--------|
| aws-aiops-orchestrator | **Cross-service AIOps Orchestrator** | ✅ **Complete v0.1.0 (NEW)** — see [§AIOps Architecture](#aiops-architecture) |
| aws-skill-generator | Meta Skill | ✅ Complete v1.0.0 |
| aws-ec2-ops | EC2 (Virtual Machine) | ✅ Complete v1.3.0 |
| aws-autoscaling-ops | Auto Scaling (ASG) | ✅ Complete v1.0.0 |
| aws-config-ops | Config (Compliance) | ✅ Complete v1.0.0 |
| aws-eventbridge-ops | EventBridge (Event Bus) | ✅ Complete v1.0.0 |
| aws-s3-ops | S3 (Object Storage) | ✅ Complete v1.1.0 |
| aws-cloudwatch-ops | CloudWatch (Monitoring) | ✅ Complete v2.4.0 |
| aws-iam-ops | IAM (Identity Management) | ✅ Complete v1.1.0 |
| aws-elb-ops | ELB (Load Balancing) | ✅ Complete v2.2.0 |
| aws-eks-ops | EKS (Kubernetes) | ✅ Complete v1.0.0 |
| aws-lambda-ops | Lambda (Function Compute) | ✅ Complete v1.1.0 |
| aws-vpc-ops | VPC (Network) | ✅ Complete v1.3.0 |
| aws-rds-ops | RDS (Database) | ✅ Complete v1.1.0 |
| aws-aurora-ops | Aurora (MySQL/PostgreSQL clusters) | ✅ Complete v1.2.0 |
| aws-elasticache-ops | ElastiCache (Redis/Memcached) | ✅ Complete v1.0.0 |
| aws-dynamodb-ops | DynamoDB (NoSQL) | ✅ Complete v1.1.0 |
| aws-cloudtrail-ops | CloudTrail (Audit) | ✅ Complete v1.0.0 |
| aws-kms-ops | KMS (Encryption) | ✅ Complete v2.1.0 |
| aws-route53-ops | Route53 (DNS) | ✅ Complete v1.2.0 |
| aws-secretsmanager-ops | Secrets Manager | ✅ Complete v1.0.0 |
| aws-sqs-ops | SQS (Message Queue) | ✅ Complete v1.1.0 |
| aws-sns-ops | SNS (Notification) | ✅ Complete v1.1.0 |
| aws-cloudfront-ops | CloudFront (CDN) | ✅ Complete v1.1.0 |
| aws-ssm-ops | SSM (Systems Manager) | ✅ Complete v1.0.0 |
| aws-stepfunctions-ops | Step Functions | ✅ Complete v1.1.0 |
| aws-waf-ops | WAF (Web Application Firewall) | ✅ Complete v1.0.0 |
| aws-acm-ops | ACM (Certificate Manager) | ✅ Complete v1.0.0 |
| aws-opensearch-ops | OpenSearch Service (managed Elasticsearch) | ✅ Complete v1.0.0 |
| aws-guardduty-ops | GuardDuty (threat detection) | ✅ Complete v1.0.0 |
| aws-securityhub-ops | Security Hub (security findings/compliance) | ✅ Complete v1.0.0 |
| aws-athena-ops | Athena (serverless SQL queries) | ✅ Complete v1.0.0 |
| aws-ram-ops | RAM (cross-account resource sharing) | ✅ Complete v1.1.0 |
| aws-topo-discovery | Cross-product Topology Discovery | ✅ Complete v1.1.0 |
| aws-aiops-cruise | **Full-chain AIOps patrol (read-only)** | ✅ **Complete v2.0.0** — see [§AIOps Cruise](#aiops-cruise) |

## AIOps Cruise

**`aws-aiops-cruise`** is the **read-only end-to-end patrol skill** (EIP → ALB → EC2 → RDS/ElastiCache → NAT → Security Groups). It complements:

| Skill | Role |
|-------|------|
| `aws-topo-discovery` | Static topology + HCL/baseline |
| `aws-aiops-cruise` | Scheduled health cruise + 7 Perceive Agents + runbooks 01–09 |
| `aws-aiops-orchestrator` | Cross-service RCA, self-heal, cost forecast orchestration |

Quick start:

```bash
python3 aws-aiops-cruise/runbooks/scripts/daily-health-check.py \
  --resource-group prod-web-rg --region us-east-1 \
  --render-topology --non-interactive
```

## AIOps Orchestrator

**`aws-aiops-orchestrator`** is the **cross-service brain** that sits on top
of all 30 `aws-*-ops` skills. It does not execute AWS operations directly;
instead it:

1. **Routes** user intents (health-check, RCA, self-heal, cost/capacity
   forecast, change-impact) to the appropriate `aws-*-ops` skill via a
   standardized `aiops_delegate` envelope.
2. **Correlates** signals (metrics, logs, events, config, cost) across
   services — a single symptom often spans 3+ services.
3. **Drives multi-skill remediation workflows** through 22 standard
   runbooks (RB-001 … RB-022).
4. **Provides global capacity & cost forecasting** via CloudWatch FORECAST,
   Cost Explorer, and Compute Optimizer.
5. **Implements the unified AIOps closed-loop** (Data Collection →
   Detection → RCA → Decision → Action → Feedback) reusing the blueprint
   in [`aws-elb-ops/references/aiops-automation-engine.md`](aws-elb-ops/references/aiops-automation-engine.md).

### When to load the orchestrator

| Use the orchestrator when… | Delegate to a specific skill when… |
|---------------------------|------------------------------------|
| Cross-service health ("is prod OK?", "site is slow") | Single-service create / modify / delete |
| Cross-service RCA ("why 502", "why latency") | Specific CloudWatch / IAM / S3 setup |
| Cost forecast across services | Single-resource lookup |
| Coordinated self-heal across multiple skills | Single-skill self-healing (e.g., ELB target re-register) |
| Change-impact / blast-radius analysis | Direct console-like interaction |

### Orchestrator skill files

```
aws-aiops-orchestrator/
├── SKILL.md                          # main entry — 440 lines
├── references/
│   ├── delegate-routing.md           # delegate contract + routing matrix
│   ├── delegate-adapter-patch.md     # canonical patch for downstream skills
│   ├── correlation-graph.md          # resource dependency graph model
│   ├── detection-rules.md            # 53 detection rules (FD/PD/CO/SD/CD)
│   └── runbook-recipes.md            # 22 runbooks (RB-001…RB-022)
└── assets/
    ├── example-scope-graph.yaml      # sample dependency graph
    └── cost-forecast-template.json   # cost forecast output schema
```

### Detection Rule Coverage (53 rules)

| Domain | Count | Sample Rules | Primary Skills |
|--------|-------|--------------|----------------|
| **FD — Fault Detection** | 14 | FD-01 target flapping, FD-03 5xx surge, FD-06 status check fail, FD-10 ALL targets unhealthy, FD-11 Lambda throttle | `aws-elb-ops`, `aws-ec2-ops`, `aws-rds-ops`, `aws-lambda-ops` |
| **PD — Predictive** | 7 | PD-01 cert expiry, PD-03 RDS storage, PD-05 LCU forecast, PD-07 cost overrun | `aws-acm-ops`, `aws-rds-ops`, `aws-cloudwatch-ops`, Cost Explorer |
| **CO — Cost Optimization** | 9 | CO-01 idle ALB, CO-03 idle NAT GW, CO-09 cost anomaly, CO-08 Compute Optimizer | `aws-elb-ops`, `aws-vpc-ops`, `aws-ec2-ops`, Compute Optimizer |
| **SD — Security Detection** | 7 | SD-01 GuardDuty CRITICAL, SD-02 S3 public, SD-03 SG 0.0.0.0/0, SD-04 IAM cred leak | `aws-guardduty-ops`, `aws-s3-ops`, `aws-iam-ops` |
| **CD — Change Detection** | 5 | CD-01 SG drift, CD-02 IAM attach, CD-04 RDS delete, CD-05 pre-change baseline | `aws-cloudtrail-ops`, `aws-config-ops`, `aws-iam-ops` |

### Runbook Library (22 runbooks)

| ID Range | Coverage |
|----------|----------|
| RB-001…RB-010 | Core LB/EC2/RDS/Cert/Cost incidents (target flapping, 5xx surge, cert expiry, idle LB, RDS connections) |
| RB-011…RB-014 | Lambda + VPC + SG (throttling, iterator age, flow log anomaly, SG drift) |
| RB-015…RB-017 | Storage + Security (EBS saturation, KMS compliance, IAM credential leak) |
| RB-018…RB-022 | Cache + Search + Cost + DNS (ElastiCache, OpenSearch, S3 lifecycle, multi-region failover, cost spike) |

### Delegate Adapter Patch (v0.1)

To make a downstream skill orchestrator-aware, apply the canonical patch
in [`aws-aiops-orchestrator/references/delegate-adapter-patch.md`](aws-aiops-orchestrator/references/delegate-adapter-patch.md).
The patch:

1. Adds `metadata.orchestrator_aware`, `orchestrator_compat`, and
   `delegate:` keys to the skill's YAML frontmatter.
2. Appends a `## AIOps Delegate Contract` section to `SKILL.md`.

**Adoption status** (see `delegate-adapter-patch.md` §5 for migration order):

| Priority | Skills | Status |
|----------|--------|--------|
| **P0** (core) | `aws-cloudwatch-ops`, `aws-elb-ops`, `aws-ec2-ops`, `aws-rds-ops`, `aws-vpc-ops`, `aws-acm-ops`, `aws-route53-ops`, `aws-waf-ops` | ✅ Patched |
| **P1** (data + executor) | `aws-cloudtrail-ops`, `aws-config-ops`, `aws-autoscaling-ops`, `aws-kms-ops`, `aws-iam-ops`, `aws-guardduty-ops`, `aws-securityhub-ops`, `aws-s3-ops` | ✅ Patched |
| **P2** (optional) | `aws-lambda-ops`, `aws-stepfunctions-ops`, `aws-eventbridge-ops`, `aws-sns-ops`, `aws-sqs-ops`, `aws-ssm-ops`, `aws-secretsmanager-ops`, `aws-elasticache-ops`, `aws-opensearch-ops`, `aws-dynamodb-ops`, `aws-cloudfront-ops`, `aws-eks-ops`, `aws-athena-ops`, `aws-ram-ops` | ⏳ Pending (on demand) |

Apply the patch in priority order; the canonical text is in
`aws-aiops-orchestrator/references/delegate-adapter-patch.md`. Use
`scripts/apply_aiops_adapter_patch.py` to batch-apply across multiple
skills at once (idempotent).

## AIOps Architecture

This project includes a **full-chain AIOps closed-loop** architecture across 6 modules, AI-led and data-driven. The architecture is built on the original "Pre-flight → Execute → Validate → Recover" pattern, extended with 6 AIOps layers:

```
Layer 1: 数据采集层 (Data Collection)
          CloudWatch Metrics | Access Logs | CloudTrail Events
          VPC Flow Logs | AWS Config | AWS Health

Layer 2: 检测分析层 (Detection & Analysis)
          ML Anomaly Detection | FORECAST | Logs Insights
          Contributor Insights | Time-Series Alignment

Layer 3: 根因诊断层 (Root Cause Analysis)
          Cross-Module Correlation | Time-Line Tracing
          CloudTrail Change Association | Dependency Graph

Layer 4: 决策规划层 (Decision & Planning)
          [AUTO_HEAL] — automatic execution (< 15 min)
          [AI_ASSIST] — recommend, user confirms (1-4 h)
          [MANUAL] — human judgment required (> 4 h)

Layer 5: 自动执行层 (Automated Execution)
          Target Re-registration | EC2 Reboot
          DNS Failover | Compliance Fix | Capacity Scaling

Layer 6: 反馈学习层 (Feedback & Learning)
          Success Tracking | Model Calibration
          Knowledge Base Update | Progressive Tuning
```

### AIOps Decision Types

| Label | Meaning | Response SLA | When Used |
|-------|---------|-------------|----------|
| `[AUTO_HEAL]` | AI executes fix autonomously | < 15 min | Target re-registration, EC2 reboot, DNS failover, cross-zone enable, compliance fix |
| `[AI_ASSIST]` | AI recommends, user confirms | 1-4 h | Health check tuning, EC2 resize, capacity scaling, SSM diagnostics |
| `[MANUAL]` | AI identifies, human decides | > 4 h | SG changes, resource deletion, cost > $100/month changes |

### AIOps Scenario Coverage

The legacy 31-scenario model in `aws-elb-ops/references/aiops-automation-engine.md`
remains the canonical blueprint. As of v0.1.0, the AIOps Orchestrator
generalizes this across the entire `aws-*-ops` fleet with the following
expanded coverage:

#### Detection Rules (53 total — see `aws-aiops-orchestrator/references/detection-rules.md`)

| Domain | Count | Examples | Key Modules |
|--------|-------|----------|-------------|
| **FD — Fault Detection** | 20 | FD-01 target flapping, FD-03 5xx surge, FD-06 status check, FD-07a memory pressure, FD-07b IOPS saturation, FD-07e network bandwidth, FD-10 ALL unhealthy, FD-11 Lambda throttle | `aws-elb-ops`, `aws-cloudwatch-ops`, `aws-ec2-ops`, `aws-rds-ops`, `aws-lambda-ops`, `aws-vpc-ops`, `aws-opensearch-ops` |
| **PD — Predictive** | 7 | PD-01 cert expiry, PD-03 RDS storage, PD-05 LCU forecast, PD-07 cost overrun | `aws-cloudwatch-ops` (FORECAST), `aws-acm-ops`, `aws-rds-ops`, Cost Explorer |
| **CO — Cost Optimization** | 9 | CO-01 idle ALB, CO-03 idle NAT GW, CO-04 unattached EBS, CO-07 RDS over-prov, CO-09 cost anomaly | `aws-elb-ops`, `aws-vpc-ops`, `aws-ec2-ops`, Compute Optimizer |
| **SD — Security Detection** | 7 | SD-01 GuardDuty CRITICAL, SD-02 S3 public, SD-03 SG 0.0.0.0/0, SD-04 IAM leak | `aws-guardduty-ops`, `aws-securityhub-ops`, `aws-s3-ops`, `aws-iam-ops`, `aws-kms-ops` |
| **CD — Change Detection** | 5 | CD-01 SG drift, CD-02 IAM attach, CD-04 RDS delete, CD-05 pre-change baseline | `aws-cloudtrail-ops`, `aws-config-ops`, `aws-iam-ops` |

#### Runbooks (22 total — see `aws-aiops-orchestrator/references/runbook-recipes.md`)

| Tier | Count | Example Runbooks |
|------|-------|------------------|
| **`[AUTO_HEAL]`** (execute without prompt) | 4 | RB-001 target flapping, RB-002 target unhealthy, RB-004 cert expiry, RB-005 WAF DDoS, RB-007 prod 5xx surge |
| **`[AI_ASSIST]`** (recommend + confirm) | 12 | RB-003 latency spike, RB-008 S3 BPA, RB-010 RDS conn, RB-011 Lambda throttle, RB-013 VPC flow anomaly, RB-015 EBS sat, RB-019 OpenSearch yellow/red, RB-021 multi-region failover |
| **`[MANUAL]`** (identify only) | 6 | RB-006 cost investigation, RB-009 idle LB, RB-014 SG open ingress, RB-017 IAM leak, RB-020 S3 lifecycle, RB-022 cost spike containment |

### Auto-Heal Boundary Conditions

| Condition | Degrade To | Reason |
|-----------|-----------|--------|
| Involves data deletion | `[MANUAL]` | Irreversible |
| Cross-account operation | `[MANUAL]` | Needs cross-account auth |
| Cost change > $100/month | `[AI_ASSIST]` | User must be aware |
| First-seen anomaly type | `[AI_ASSIST]` | No historical pattern |
| Auto-heal fails 2x | `[MANUAL]` | Prevent crash cascade |
| ALL targets unhealthy | `[AI_ASSIST]` | May indicate app outage |
| Orchestrator-level: blast radius > 5 prod resources | `[MANUAL]` | Mass change requires human review |
| Orchestrator-level: missing `confirmation_token` on destructive op | `[AI_ASSIST]` | Per delegate contract §6 |
| Orchestrator-level: orchestrator_aware flag false on target skill | `[AI_ASSIST]` | Fall back to recommendation until patched |

### Cross-Module RCA Chains

| Scenario | Diagnostic Chain |
|----------|-----------------|
| 502 Error | `aws-elb-ops` → `aws-ec2-ops` → `aws-vpc-ops` → `aws-cloudtrail-ops` |
| High Latency | `aws-elb-ops` → `aws-ec2-ops` → `aws-rds-ops`/`aws-eks-ops` → `aws-cloudwatch-ops` |
| Connection Timeout | `aws-elb-ops` → `aws-vpc-ops` → `aws-ec2-ops` |
| TLS Handshake Failure | `aws-elb-ops` → `aws-acm-ops` → `aws-cloudwatch-ops` |

### Enhanced Modules

| Module | Original Version | Current Version | Enhancement |
|--------|-----------------|----------------|-------------|
| `aws-aiops-orchestrator` | — | **v0.1.0 (new)** | **Cross-service orchestrator**: 53 detection rules, 22 runbooks, 16 downstream skills patched with delegate contract; bridges single-service AIOps into end-to-end RCA + coordinated remediation |
| `aws-elb-ops` | v1.0.0 | **v2.2.0** | AIOps scenarios, self-healing, RCA, cost optimization, change management; **orchestrator-aware (P0 patched)** |
| `aws-cloudwatch-ops` | v2.3.0 | **v2.4.0** | SKILL极致瘦身 (610→~145 lines); Operation Index → references/operation-index.md |
| `aws-ec2-ops` | v1.1.0 | **v1.3.0** | LB-target diagnostics, auto-reboot, capacity prediction; **GCL pilot** + **orchestrator-aware (P0 patched)** |
| `aws-vpc-ops` | v1.1.0 | **v1.1.0+** | Flow Log analysis, SG drift detection, network RCA; **orchestrator-aware (P0 patched)** |
| `aws-rds-ops` | v1.1.0 | **v1.1.0+** | DB diagnostics, RDS connections; **orchestrator-aware (P0 patched)** |
| `aws-acm-ops` | — | **v1.0.0 (new)** | Certificate lifecycle, expiry monitoring, auto-renewal; **orchestrator-aware (P0 patched)** |
| `aws-route53-ops` | v1.0.0 | **v1.0.0+** | DNS failover automation, health check ELB integration; **orchestrator-aware (P0 patched)** |
| `aws-waf-ops` | — | **v1.0.0 (new)** | WAF AIOps: traffic anomaly, rate limiting, Managed Rules, rule audit; **orchestrator-aware (P0 patched)** |
| `aws-autoscaling-ops` | — | **v1.0.0 (new)** | ASG management, scaling policies, instance refresh, lifecycle hooks, capacity governance; **GCL** + **orchestrator-aware (P1 patched)** |
| `aws-config-ops` | — | **v1.0.0 (new)** | Configuration recorder, delivery channel, managed/custom rules, conformance packs, aggregator, compliance evaluation; **GCL** + **orchestrator-aware (P1 patched)** |
| `aws-eventbridge-ops` | — | **v1.0.0 (new)** | Event buses, rules/targets, API destinations, connections, archives/replay, scheduler, pipes; **GCL** + **orchestrator-aware (P2 pending)** |
| `aws-cloudtrail-ops` | v1.0.0 | **v1.0.0+** | API event correlation, change timeline; **orchestrator-aware (P1 patched)** |
| `aws-s3-ops` | v1.0.0 | **v1.1.0** | Lifecycle gap detection, public-access audit, cost optimization; **GCL pilot** + **orchestrator-aware (P1 patched)** |
| `aws-iam-ops` | v1.0.0 | **v1.1.0** | Credential leak response, IAM attach tracking; **GCL pilot** + **orchestrator-aware (P1 patched)** |
| `aws-kms-ops` | v1.0.0 | **v2.1.0** | Key compliance, rotation, deletion guard; **GCL pilot** + **orchestrator-aware (P1 patched)** |
| `aws-guardduty-ops` | — | **v1.0.0 (new)** | Threat detection, finding correlation; **orchestrator-aware (P1 patched)** |
| `aws-securityhub-ops` | — | **v1.0.0 (new)** | Security score, compliance standards aggregation; **orchestrator-aware (P1 patched)** |

## References

- [AWS CLI Documentation](https://docs.aws.amazon.com/cli/)
- [boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [Agent Skills OpenSpec](https://agentskills.io/specification)

## Data Source Dependencies

| Level | Scenarios Covered | Requires | Cost |
|-------|------------------|----------|------|
| **Level 1** — ELB API + CloudWatch | 18 scenarios | Nothing (default ON) | Free |
| **Level 2** — + CloudTrail Management Events | 5 scenarios | CloudTrail (default ON) | Free |
| **Level 3** — + Access Logs / Flow Logs | 5 scenarios (optional depth) | S3 / Logs | Minimal |
| **Orchestrator** — All of the above + Cost Explorer + Compute Optimizer | 53 detection rules + 22 runbooks across 16 patched skills | All P0/P1 downstream skills | Free – Minimal |

See `aws-elb-ops/references/integration.md` for detailed CloudTrail and AWS Config integration.

## Quality Gate (GCL)

The repository adopts a **Generator-Critic-Loop (GCL)** adversarial quality
gate on every high-side-effect skill execution. Full specification lives in
[`aws-skill-generator/references/gcl-spec.md`](aws-skill-generator/references/gcl-spec.md);
top-level index in `AGENTS.md` §11.

All **28 skills** now have complete GCL implementation:

| Phase | Skills | Class | Date |
|---|---|---|---|
| **Pilot** | `aws-ec2-ops`, `aws-iam-ops`, `aws-kms-ops`, `aws-s3-ops` | required | 2026-06-04 |
| **Group 1** | `aws-rds-ops`, `aws-lambda-ops`, `aws-dynamodb-ops` | required | 2026-06-04 |
| **Group 2** | `aws-vpc-ops`, `aws-route53-ops`, `aws-cloudfront-ops`, `aws-elb-ops` | required/recommended | 2026-06-04 |
| **Group 3** | `aws-elasticache-ops`, `aws-waf-ops`, `aws-secretsmanager-ops`, `aws-ssm-ops`, `aws-acm-ops`, `aws-eks-ops`, `aws-sqs-ops`, `aws-sns-ops`, `aws-stepfunctions-ops`, `aws-cloudwatch-ops`, `aws-cloudtrail-ops` | required/recommended/optional | 2026-06-04 |
| **Group 4** | `aws-autoscaling-ops` | required | 2026-06-07 |
| **Group 5** | `aws-config-ops`, `aws-eventbridge-ops` | recommended | 2026-06-07 |
| **Group 6** | `aws-guardduty-ops`, `aws-opensearch-ops`, `aws-securityhub-ops` | required | 2026-06-08 |
| **Group 7** | `aws-athena-ops`, `aws-ram-ops` | required | 2026-06-10 |

- **5-dimension rubric** (0 / 0.5 / 1): Correctness, Safety, Idempotency,
  Traceability, Spec Compliance. **Safety = 0 → ABORT.**
- **Trace path:** `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` (git-ignored).
- **Rollout complete:** Every `required`, `recommended`, and `optional` skill
  listed in `AGENTS.md` §11.5 Per-Skill Defaults table now ships rubric.md,
  prompt-templates.md, and a `## Quality Gate (GCL)` section in its SKILL.md.
- **Next:** Phase 2 — `scripts/gcl_runner.py` reusable Orchestrator (planned).

## Still Needs Enhancement

| # | Area | Priority | Detail |
|---|------|----------|--------|
| 1 | ✅ `aws-waf-ops` module | Done | Created v1.0.0 with AH-08 DDoS auto-mitigation |
| 2 | ✅ CloudWatch dashboard | Done | 8-component dashboard JSON in aws-cloudwatch-ops/assets/ |
| 3 | ✅ EventBridge automation | Done | 3 event patterns in aws-waf-ops/references/ |
| 4 | ✅ Cost Explorer integration | Done | Per-LB cost via tags in aws-elb-ops/references/ |
| 5 | ✅ ACM auto-bind to ELB | Done | AH-ACM-01 in aws-acm-ops/SKILL.md |
| 6 | ✅ Multi-region AIOps | Done | Cross-region health/latency/failover in aws-route53-ops/references/ |
| 7 | ✅ Feedback loop persistence | Done | CloudWatch Logs feedback storage in aws-cloudwatch-ops/references/ |
| 8 | ✅ SLA breach escalation | Done | PagerDuty/Jira integration in aws-elb-ops/references/ |
| 9 | ✅ GCL full rollout | Done | All 30 skills (4 pilots + 26 rollout) have complete GCL implementation — rubric.md, prompt-templates.md, GCL section, gcl frontmatter |
| 10 | 🔄 GCL runner script | Planned | `scripts/gcl_runner.py` reusable Orchestrator (Phase 2) |

## License

MIT
