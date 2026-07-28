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
  last_updated: "2026-06-27"
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
  destructive_ops_require_confirm: true
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_DEFAULT_REGION
  orchestrator_aware: true
  orchestrator_compat: ">=0.10"
  delegate:
    accepts: ['compliance-scan', 'change-impact', 'cost-forecast']
    produces_facts: ['config', 'state', 'cost']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---

# AWS S3 Operations Skill

Use for S3 buckets, objects, versions, policies, ACLs, lifecycle, replication, encryption, websites, CORS, multipart uploads, and storage operations. Detailed commands remain in references.

## Common JSON Paths

Buckets: .Buckets[].{Name,CreationDate}
Objects: .Contents[].{Key,Size,LastModified,StorageClass}
Versions: .Versions[].{Key,VersionId,IsLatest,Size,LastModified}
DeleteMarkers: .DeleteMarkers[].{Key,VersionId,IsLatest,LastModified}
Object: .{ETag,VersionId,ServerSideEncryption}

## Trigger & Scope

### SHOULD Use When
S3 buckets/objects, upload/download, versions, policies, lifecycle, replication, encryption, websites, CORS, ACLs, or multipart uploads.

### SHOULD NOT Use When
CloudFront → `aws-cloudfront-ops`; KMS key lifecycle → `aws-kms-ops`; IAM principal policy → `aws-iam-ops`; EFS → `aws-efs-ops`.

## Variable Convention

| Placeholder | Source | Use |
|---|---|---|
| `{{env.AWS_*}}` | Runtime env | Never ask; fail closed if unset |
| `{{user.bucket_name}}`, `{{user.key}}`, `{{user.region}}` | User input | Bucket/object identity |
| `{{user.file_path}}`, `{{user.prefix}}`, `{{user.version_id}}` | User input | Object operation parameters |
| `{{output.*}}` | API response | Reuse version, ETag, count, and size |

## Execution Flow Pattern

Every operation follows **Pre-flight → Execute → Validate → Recover**. First run `aws sts get-caller-identity --output json`, then verify bucket identity/region with `head-bucket` or `list-buckets`, versioning, object/version counts, policy/ACL, encryption, replication, and dependencies. Use CLI `--output json`, then boto3 after 3 CLI failures. Validate by read-back; recover with bounded retries and halt on region mismatch, access denial, or ambiguous scope. See [aws-cli-usage.md](references/aws-cli-usage.md), [boto3-sdk-usage.md](references/boto3-sdk-usage.md), and [troubleshooting.md](references/troubleshooting.md).

## Operations and Safety

| Operation | Pre-flight / validation | Confirmation |
|---|---|---|
| Put/get/list object | Verify bucket/key and encryption; mask sensitive content | Sensitive files (`.env`, credentials, `*.pem`, `*.key`) require explicit approval |
| Delete object/version | Echo exact key/version and verify lookup | Resource-bound token |
| Batch delete | `Objects` must be non-empty, explicit, bounded; wildcards abort | Count-bound confirmation |
| Recursive remove | Print object count and total bytes before execution | Scope/count/bytes confirmation |
| Delete bucket | Inspect versioning, objects, versions, delete markers, replication | Bucket-bound confirmation; versioned buckets require deleting versions first |
| Public policy/ACL | Diff policy; block `Principal:"*"`/public ACL unless explicitly approved | Public-access confirmation |
| Lifecycle expiration <30d | Show affected prefix/count and data-loss date | Explicit expiration confirmation |
| Remove website/CORS/policy/replication/encryption | Show production impact and current config | Human confirmation |
| Abort multipart upload | Show size/parts and resumability | Confirmation for large/non-resumable upload |

A2: versioned bucket deletion without prior object-version cleanup → Safety=0 abort. A6: empty/wildcard batch delete → abort. A7 region must match. A8 bucket must be echoed from lookup. A9 sensitive files/content never enter traces. A10 STS identity is first command. A15 public-access widening requires explicit public confirmation.

## Quality Gate (GCL)

Required GCL, `max_iter=2`, rubric `references/rubric.md`, prompts `references/prompt-templates.md`; persist traces under `./audit-results/`; Safety=0 aborts.

## Token Efficiency

TE-1…TE-6 apply; query live storage state/limits, keep SDK examples comment-only, centralize JSON paths above, use asset anchors, and keep flows single-sourced.

## Reference Files

[aws-cli-usage.md](references/aws-cli-usage.md) · [boto3-sdk-usage.md](references/boto3-sdk-usage.md) · [core-concepts.md](references/core-concepts.md) · [troubleshooting.md](references/troubleshooting.md) · [integration.md](../aws-skill-generator/references/integration.md) · [rubric.md](references/rubric.md) · [prompt-templates.md](references/prompt-templates.md)

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md): parse `aiops_delegate`; deduplicate writes by `idempotency_key` for 24h; require `confirmation_token` for destructive/public actions; `MANUAL` never writes, `AI_ASSIST` writes only with token, `AUTO_HEAL` permits non-destructive writes; propagate `trace_id` as `User-Agent: aiops-orchestrator/<trace_id>` and always emit `aiops_context` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).
