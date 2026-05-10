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
└── aws-[service]-ops/             # More service skills...
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

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create environment (requires Python >= 3.10)
uv venv --python 3.10
source .venv/bin/activate
uv pip install awscli boto3

# Configure credentials
export AWS_ACCESS_KEY_ID="your_key"
export AWS_SECRET_ACCESS_KEY="your_secret"
export AWS_DEFAULT_REGION="us-east-1"

# Verify
aws sts get-caller-identity --output json
```

## Existing Skills

| Skill | Service | Status |
|------|------|------|
| aws-skill-generator | Meta Skill | ✅ Complete |
| aws-ec2-ops | EC2 (Virtual Machine) | ✅ Complete |
| aws-s3-ops | S3 (Object Storage) | ✅ Complete |
| aws-cloudwatch-ops | CloudWatch (Monitoring) | ✅ Complete |
| aws-iam-ops | IAM (Identity Management) | ✅ Complete |
| aws-elb-ops | ELB (Load Balancing) | ✅ Complete |
| aws-eks-ops | EKS (Kubernetes) | ✅ Complete |
| aws-lambda-ops | Lambda (Function Compute) | ✅ Complete |
| aws-vpc-ops | VPC (Network) | ✅ Complete |
| aws-rds-ops | RDS (Database) | ✅ Complete |
| aws-elasticache-ops | ElastiCache (Redis/Memcached) | ✅ Complete |

## References

- [AWS CLI Documentation](https://docs.aws.amazon.com/cli/)
- [boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [Agent Skills OpenSpec](https://agentskills.io/specification)

## License

MIT
