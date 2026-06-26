# Core Concepts — S3

## Overview

Amazon S3 is object storage with global namespace and regional data placement.
- **Docs**: https://docs.aws.amazon.com/s3/

## Resource Model

| Resource | Description |
|----------|-------------|
| Bucket | Storage container (global namespace, regional API) |
| Object | File stored in bucket (max 5TB, min 0B) |
| Prefix | Folder-like key prefix |
| Version | Object version (if versioning enabled) |

## Storage Classes (Summary)

- **STANDARD** — general purpose, immediate access
- **STANDARD_IA / ONEZONE_IA** — infrequent access, lower cost
- **GLACIER / DEEP_ARCHIVE** — archive, minutes-to-hours restore
- **INTELLIGENT_TIERING** — auto-optimizes between tiers

## Bucket Naming Rules

3–63 chars, lowercase + numbers + hyphens + periods, start with letter/number, no IP format, global uniqueness.

## Key Quotas

| Quota | Default |
|-------|---------|
| Buckets per account | 100 (up to 1000 via support) |
| Object size max | 5TB |
| Multipart upload parts max | 10,000 |
| Min multipart part size | 5MB (recommended) |

## Region Handling

- `us-east-1`: no `LocationConstraint` needed
- Other regions: `LocationConstraint=<region>` required

## Dependencies

| Dependency | Required | Skill |
|------------|----------|-------|
| IAM Policy | Yes | `aws-iam-ops` |
| KMS Key (encryption) | Optional | `aws-kms-ops` |
| VPC Endpoint | No | `aws-vpc-ops` |
| SNS Topic (notifications) | Optional | `aws-sns-ops` |