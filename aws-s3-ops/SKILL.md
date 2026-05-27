---
name: aws-s3-ops
description: >-
  Use when the user needs to create, configure, or manage object storage buckets
  in AWS S3; upload, download, copy, or delete objects; configure bucket
  policies, access control lists (ACLs), or lifecycle policies; set up bucket
  versioning or encryption; configure CORS policies for cross-origin requests;
  configure static website hosting; manage multipart uploads for large files;
  or optimize storage costs with intelligent tiering, even if they don't say
  "S3" and instead say "store files in the cloud", "upload to object storage",
  "configure bucket access", "set up static website hosting", "manage file
  storage in AWS", or "configure cross-origin resource sharing for S3".
---
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to S3 endpoints.
metadata:
  author: aws
  version: "1.0.0"
  last_updated: "2026-05-10"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_DEFAULT_REGION
---

# AWS S3 Operations Skill

## Common JSON Paths (Centralized)

```
# Create:     .Location  (bucket ARN)
# List:       .Buckets[].{Name,CreationDate}
# Head:       Empty (204 — check via HTTP status)
# Put/Get:    .ETag
# List Objs:  .Contents[].{Key,Size,LastModified}
```

## Overview

Amazon S3 (Simple Storage Service) provides object storage with scalability, availability, and security. This skill is an **operational runbook** with explicit scope, credential rules, pre-flight checks, dual-path execution (AWS CLI + boto3 SDK), validation, and recovery.

## Trigger & Scope

### SHOULD Use When
- User mentions "S3", "Simple Storage Service", "bucket", "object storage"
- Task involves CRUD on **S3 buckets and objects** (create, list, delete, copy, upload, download)
- Keywords: bucket, object, key, prefix, upload, download, multipart

### SHOULD NOT Use When
- Billing only → delegate to: `aws-cost-ops`
- IAM only → delegate to: `aws-iam-ops`
- CloudFront CDN → delegate to: `aws-cloudfront-ops`
- Glacier lifecycle → delegate to: `aws-s3-ops` (same skill with lifecycle policies)

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use `us-east-1` if unset |
| `{{user.bucket_name}}` | User input | Ask once; reuse |
| `{{user.key}}` | User input | Ask once; reuse |
| `{{output.bucket_arn}}` | Last API response | Parse: `.Location` |

## Execution Flow Pattern

Every operation: **Pre-flight → Execute → Validate → Recover**

```
Pre-flight → Execute (CLI/SDK) → Validate → Recover (On Error)
```

### Operation: Create Bucket

#### Pre-flight

**Step 1: Check CLI**
```bash
aws --version
```
Log: `[OK] AWS CLI v2.x.x detected` or `[FAIL] AWS CLI not found. Install: uv pip install awscli`

**Step 2: Load & Verify Credentials**
```bash
aws sts get-caller-identity --output json
```

Log format:
```
[SKILL] Loading AWS credentials...
[OK]   AWS_DEFAULT_REGION={{env.AWS_DEFAULT_REGION}} (from .env)
[OK]   AWS_ACCESS_KEY_ID=**** (from .env, masked)
[OK]   Credential verification passed
[OK]   Identity: arn:aws:iam::{{env.AWS_ACCOUNT_ID}}:user/xxx
```

On failure:
```
[FAIL] AWS credential verification failed.
AWS Error: <exact error message>
Action: See references/integration.md → Error Messages for diagnosis.
```

| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `aws --version` | Install AWS CLI v2 |
| Credentials | `aws sts get-caller-identity` | HALT; log precise error; guide user to integration.md |
| Bucket name valid | Check naming rules (3-63 chars, no uppercase, DNS-compliant) | Suggest valid name |
| Region check | `aws s3 ls` | Confirm region |

#### Execute — CLI (Primary)
```bash
aws s3api create-bucket \
  --bucket "{{user.bucket_name}}" \
  --region "{{user.region}}" \
  --create-bucket-configuration LocationConstraint="{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
import boto3
client = boto3.client('s3', region_name='{{user.region}}')
response = client.create_bucket(
    Bucket='{{user.bucket_name}}',
    CreateBucketConfiguration={'LocationConstraint': '{{user.region}}'}
)
```

#### Validate
```bash
aws s3api head-bucket --bucket "{{user.bucket_name}}" --output json
```

#### Recover
| Error | Action |
|-------|--------|
| BucketAlreadyExists | HALT; suggest different name (global namespace) |
| InvalidBucketName | Fix name per naming rules |
| Throttling (429) | Backoff, retry 3x |

### Operation: Delete Bucket (Destructive)

**Safety Gate**: MUST obtain explicit confirmation.
> "Delete bucket {{user.bucket_name}} and all objects? This is IRREVERSIBLE."

#### Pre-flight
- Verify bucket exists and is empty OR enable `--force`
- List objects to show deletion scope

#### Execute — CLI
```bash
# Empty first (if objects exist)
aws s3 rm s3://"{{user.bucket_name}}" --recursive --region "{{user.region}}"

# Delete bucket
aws s3api delete-bucket --bucket "{{user.bucket_name}}" --region "{{user.region}}" --output json
```

### Operation: Upload Object (Put Object)

#### Execute — CLI
```bash
aws s3api put-object \
  --bucket "{{user.bucket_name}}" \
  --key "{{user.key}}" \
  --body "{{user.file_path}}" \
  --region "{{user.region}}" \
  --output json
```

#### Large Files (>100MB): Multipart Upload
```bash
aws s3 cp "{{user.file_path}}" s3://"{{user.bucket_name}}/{{user.key}}" --region "{{user.region}}"
```

### Operation: Download Object (Get Object)

#### Execute — CLI
```bash
aws s3api get-object \
  --bucket "{{user.bucket_name}}" \
  --key "{{user.key}}" \
  "{{user.output_path}}" \
  --region "{{user.region}}" \
  --output json
```

### Operation: List Objects

#### Execute — CLI
```bash
aws s3api list-objects-v2 \
  --bucket "{{user.bucket_name}}" \
  --prefix "{{user.prefix}}" \
  --region "{{user.region}}" \
  --output json
```

#### Present to User
| Field | JSON Path | Notes |
|-------|-----------|-------|
| Key | `.Contents[].Key` | Object path |
| Size | `.Contents[].Size` | Bytes |
| LastModified | `.Contents[].LastModified` | ISO 8601 |

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](../aws-skill-generator/references/integration.md)