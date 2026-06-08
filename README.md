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
|------|------|------|
| aws-skill-generator | Meta Skill | ✅ Complete |
| aws-ec2-ops | EC2 (Virtual Machine) | ✅ Complete |
| aws-autoscaling-ops | Auto Scaling (ASG) | ✅ Complete v1.0.0 |
| aws-config-ops | Config (Compliance) | ✅ Complete v1.0.0 |
| aws-eventbridge-ops | EventBridge (Event Bus) | ✅ Complete v1.0.0 |
| aws-s3-ops | S3 (Object Storage) | ✅ Complete · **GCL pilot v1.1.0** |
| aws-cloudwatch-ops | CloudWatch (Monitoring) | ✅ Complete |
| aws-iam-ops | IAM (Identity Management) | ✅ Complete · **GCL pilot v1.1.0** |
| aws-elb-ops | ELB (Load Balancing) | ✅ Complete |
| aws-eks-ops | EKS (Kubernetes) | ✅ Complete |
| aws-lambda-ops | Lambda (Function Compute) | ✅ Complete |
| aws-vpc-ops | VPC (Network) | ✅ Complete |
| aws-rds-ops | RDS (Database) | ✅ Complete |
| aws-elasticache-ops | ElastiCache (Redis/Memcached) | ✅ Complete |
| aws-dynamodb-ops | DynamoDB (NoSQL) | ✅ Complete |
| aws-cloudtrail-ops | CloudTrail (Audit) | ✅ Complete |
| aws-kms-ops | KMS (Encryption) | ✅ Complete · **GCL pilot v2.1.0** |
| aws-route53-ops | Route53 (DNS) | ✅ Complete |
| aws-secretsmanager-ops | Secrets Manager | ✅ Complete |
| aws-sqs-ops | SQS (Message Queue) | ✅ Complete |
| aws-sns-ops | SNS (Notification) | ✅ Complete |
| aws-cloudfront-ops | CloudFront (CDN) | ✅ Complete |
| aws-stepfunctions-ops | Step Functions | ✅ Complete |
| aws-waf-ops | WAF (Web Application Firewall) | ✅ Complete v1.0.0 |
| aws-acm-ops | ACM (Certificate Manager) | ✅ Complete v1.0.0 |
| aws-opensearch-ops | OpenSearch Service (managed Elasticsearch) | ✅ Complete v1.0.0 |
| aws-guardduty-ops | GuardDuty (threat detection) | ✅ Complete v1.0.0 |
| aws-securityhub-ops | Security Hub (security findings/compliance) | ✅ Complete v1.0.0 |

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

### AIOps Scenario Coverage (31 Scenarios)

| Domain | Scenarios | Key Modules |
|--------|-----------|-------------|
| **Fault Detection** (6) | Health flapping, latency spikes, error surges, connection exhaustion, cross-AZ imbalance, traffic anomalies | `aws-elb-ops` + `aws-cloudwatch-ops` |
| **Predictive Analysis** (5) | Capacity saturation, quota exhaustion, cert expiry, cost overrun, traffic peaks | `aws-cloudwatch-ops` + `aws-elb-ops` + `aws-acm-ops` |
| **Auto-Healing** (12) | Target re-registration, EC2 reboot/restart, DNS failover, cross-AZ rebalance, compliance fix, health check tuning | `aws-elb-ops` + `aws-ec2-ops` + `aws-route53-ops` + `aws-vpc-ops` |
| **Root Cause Analysis** (7) | 502 error, high latency, unhealthy target, connection timeout, TLS handshake, cost anomaly, cert expiry | All 6 AIOps modules |
| **Change Management** (4) | Pre-change impact, post-change validation, auto-rollback, compliance scanning | `aws-elb-ops` + `aws-vpc-ops` + `aws-cloudtrail-ops` |
| **Cost Optimization** (3) | Idle LB detection, overspec recommendation, cross-AZ cost analysis | `aws-elb-ops` + `aws-cloudwatch-ops` |

### Auto-Heal Boundary Conditions

| Condition | Degrade To | Reason |
|-----------|-----------|--------|
| Involves data deletion | `[MANUAL]` | Irreversible |
| Cross-account operation | `[MANUAL]` | Needs cross-account auth |
| Cost change > $100/month | `[AI_ASSIST]` | User must be aware |
| First-seen anomaly type | `[AI_ASSIST]` | No historical pattern |
| Auto-heal fails 2x | `[MANUAL]` | Prevent crash cascade |
| ALL targets unhealthy | `[AI_ASSIST]` | May indicate app outage |

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
| `aws-elb-ops` | v1.0.0 | **v2.2.0** | AIOps scenarios, self-healing, RCA, cost optimization, change management |
| `aws-cloudwatch-ops` | v2.1.0 | **v2.2.0** | ELB-specific alarms, metrics mapping, layered inspection |
| `aws-ec2-ops` | v1.1.0 | **v1.3.0** | LB-target diagnostics, auto-reboot, capacity prediction; **GCL pilot** (`references/rubric.md` + `references/prompt-templates.md`) |
| `aws-vpc-ops` | v1.1.0 | **v1.1.0+** | Flow Log analysis, SG drift detection, network RCA |
| `aws-route53-ops` | v1.0.0 | **v1.0.0+** | DNS failover automation, health check ELB integration |
| `aws-acm-ops` | — | **v1.0.0 (new)** | Certificate lifecycle, expiry monitoring, auto-renewal |
| `aws-autoscaling-ops` | — | **v1.0.0 (new)** | ASG management, scaling policies, instance refresh, lifecycle hooks, capacity governance; **GCL** (`references/rubric.md` + `references/prompt-templates.md`) |
| `aws-config-ops` | — | **v1.0.0 (new)** | Configuration recorder, delivery channel, managed/custom rules, conformance packs, aggregator, compliance evaluation; **GCL** (`references/rubric.md` + `references/prompt-templates.md`) |
| `aws-eventbridge-ops` | — | **v1.0.0 (new)** | Event buses, rules/targets, API destinations, connections, archives/replay, scheduler, pipes; **GCL** (`references/rubric.md` + `references/prompt-templates.md`) |

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
| 9 | ✅ GCL full rollout | Done | All 28 skills (4 pilots + 24 rollout) have complete GCL implementation — rubric.md, prompt-templates.md, GCL section, gcl frontmatter |
| 10 | 🔄 GCL runner script | Planned | `scripts/gcl_runner.py` reusable Orchestrator (Phase 2) |

## License

MIT
