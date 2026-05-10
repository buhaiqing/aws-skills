# Integration Setup (AWS Skills)

## Environment Setup

AWS CLI and boto3 SDK require a Python runtime. Use **`uv`** for local, isolated environment management.

### Install uv (One-time per machine)

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
# Or: brew install uv

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Bootstrap Python Environment (Idempotent)

```bash
uv venv --python 3.10

# Activate: macOS/Linux
source .venv/bin/activate
# Activate: Windows
# .venv\Scripts\activate

uv pip install awscli boto3
```

### Verify Installation

```bash
aws --version
python -c "import boto3; print('boto3 OK')"
```

## Credential Configuration

### Method A: Environment Variables (Recommended for SDK)

```bash
export AWS_ACCESS_KEY_ID="your_access_key"
export AWS_SECRET_ACCESS_KEY="your_secret_key"
export AWS_DEFAULT_REGION="us-east-1"
```

### Method B: AWS CLI Config Files

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

### Method C: IAM Role (EC2/Lambda)

No configuration needed - instance role used automatically.

## Credential Priority Order

| Priority | Source | Used By |
|----------|--------|---------|
| 1 | Environment vars | CLI + SDK |
| 2 | ~/.aws/credentials | CLI + SDK |
| 3 | ~/.aws/config | CLI (region) |
| 4 | IAM role | CLI + SDK |

## Verify Credentials

```bash
aws sts get-caller-identity --output json
```

Expected output:
```json
{
  "UserId": "AIDAI...",
  "Account": "123456789012",
  "Arn": "arn:aws:iam::123456789012:user/username"
}
```

## Project-based Setup (pyproject.toml)

```toml
[project]
name = "aws-ops"
version = "1.0.0"
requires-python = ">=3.10"
dependencies = [
    "awscli>=2.0.0",
    "boto3>=1.26.0",
]

[tool.uv]
python-version = "3.10"
```

Sync command:
```bash
uv sync
source .venv/bin/activate
```

## Multi-cloud Credential Separation

```ini
# AWS - use AWS_* prefix (standard)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1

# JD Cloud - use JDC_* prefix
JDC_ACCESS_KEY=...
JDC_SECRET_KEY=...
JDC_REGION=cn-north-1

# Aliyun - use ALIYUN_* prefix
ALIYUN_ACCESS_KEY_ID=...
ALIYUN_ACCESS_KEY_SECRET=...
ALIYUN_REGION=cn-hangzhou
```

## Safety Rules

- **NEVER** commit `.env` files (already in `.gitignore`)
- **NEVER** write credentials into Skill documents
- Generated Skills use `{{env.*}}` placeholders only