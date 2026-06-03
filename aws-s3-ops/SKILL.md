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
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to S3 endpoints.
metadata:
  author: aws
  version: "1.1.0"
  last_updated: "2026-06-04"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  gcl:
    enabled: true
    class: required
    max_iter: 2
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: true
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
## Quality Gate (GCL)

> This skill is the **Phase 1 GCL pilot** (2026-06-04, fourth rollout
> after `aws-ec2-ops`, `aws-iam-ops`, and `aws-kms-ops`). Every execution
> of `aws-s3-ops` MUST be wrapped by the Generator-Critic-Loop defined in
> `aws-skill-generator/references/gcl-spec.md`.

| Setting | Value | Source |
|---|---|---|
| Class | `required` | `gcl-spec.md` §10 (pilot) |
| `max_iterations` | `2` | `gcl-spec.md` §10 (Phase 1 default) |
| Rubric | `references/rubric.md` (v1) | this skill |
| Prompts | `references/prompt-templates.md` (v1) | this skill |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | `gcl-spec.md` §6 |

### Per-operation gating

The Orchestrator applies GCL on every execution. The following operations
are **destructive** and require `{{user.safety_confirm}}` in the trace
(exact format `confirm=<OPERATION> <bucket-or-arn>`):

- `delete-bucket` — must be empty first; if Versioning=Enabled, must also
  `delete-object-versions` (rule A2)
- `delete-objects` (batch) — `Objects` array MUST be non-empty and bounded
  (rule A6)
- `delete-object` (single) — confirmation required
- `aws s3 rm --recursive` — treated as destructive; pre-flight MUST print
  the object count and total size for user confirmation
- `put-bucket-lifecycle-configuration` with `Expiration.Days < 30` —
  treated as destructive (premature data expiry)
- `put-bucket-policy` that **widens public access** (adds
  `Principal: "*"` with `Effect: Allow` on `s3:GetObject` / `s3:*`) —
  treated as destructive, same family as IAM `Principal: *` trust policy
- `put-bucket-acl` / `put-object-acl` to `public-read` or `public-read-write` —
  treated as destructive
- `delete-bucket-website` / `delete-bucket-cors` /
  `delete-bucket-policy` / `delete-bucket-replication` /
  `delete-bucket-encryption` — configuration removal is destructive when
  the bucket serves production traffic
- `abort-multipart-upload` — only destructive for very large uploads with
  no resume; confirm

Non-destructive operations (`list-buckets`, `list-objects`,
`head-object`, `get-object`, `create-bucket`, `put-object` with
single-key idempotency) still flow through GCL with `Safety` scored
against routine guard rules only.

### AWS-specific rules in force

This skill's rubric instantiates the repo-wide AWS rules from
`gcl-spec.md` §8. The ones most relevant to S3:

- **A2** — `delete-bucket` on a `Versioning=Enabled` bucket without
  prior `delete-object-versions` → **Safety = 0 → ABORT**
- **A6** — `delete-objects` with empty `Objects` array or wildcard
  patterns → **Correctness = 0 → ABORT**
- **A7** — `--region` must match `{{user.region}}` or
  `{{env.AWS_DEFAULT_REGION}}`. S3 bucket names are globally unique but
  the API call is regional; mismatch is silently wrong.
- **A8** — `Bucket` name in the request MUST be echoed from a
  `head-bucket` or `list-buckets` lookup
- **A9** — S3 does not return secrets, but `aws s3 cp` of a
  `.env` / `credentials` / `*.pem` file would expose secrets in the
  trace. Rubric refuses `--exclude` patterns that don't cover these.
- **A10** — `aws sts get-caller-identity` MUST be the first command in
  trace to capture identity provenance

### See also

- `aws-skill-generator/references/gcl-spec.md` — full GCL specification
- `references/rubric.md` — this skill's 5-dimension rubric + S3 safety
  special cases (Versioned bucket guard, public-access widening
  detection, `--recursive` count confirmation, `delete-objects` empty
  array refusal)
- `references/prompt-templates.md` — Generator / Critic / Orchestrator
  skeletons
- Top-level `AGENTS.md` §11 — rollout index and Per-Skill Defaults
