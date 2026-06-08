---
name: aws-cloudfront-ops
description: Use when managing CloudFront distributions, CDN, cache invalidations,
  origins, or SSL/TLS certificates. Invoke when user mentions "CDN", "CloudFront",
  "distribution", or needs content delivery optimization.
license: MIT
compatibility: AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network
  access to CloudFront endpoints.
metadata:
  author: aws
  version: "1.1.0"
  last_updated: '2026-06-04'
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
  - AWS_ACCESS_KEY_ID
  - AWS_SECRET_ACCESS_KEY
  - AWS_DEFAULT_REGION
  gcl:
    enabled: true
    class: required
    max_iter: 2
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: false
---
# AWS CloudFront Ops Skill

## Common JSON Paths (Centralized)

```
# Create Dist:       .Distribution.{Id,DomainName,Status}
# Get Dist:          .Distribution.{Id,DomainName,Status}
# List Dists:        .DistributionList.Items[].{Id,DomainName,Status}
# Create Inval:      .Invalidation.{Id,Status}
# Get Inval:         .Invalidation.Status
# Create OAI:        .CloudFrontOriginAccessIdentity.{Id,S3CanonicalUserId}
```

## Trigger & Scope

### SHOULD Use When
- User requests distribution creation or deletion
- User needs to manage cache behaviors
- User asks about CloudFront
- User mentions "CDN", "distribution", "origin", "cache"
- User needs to invalidate cached content
- User asks about SSL/TLS certificates for CloudFront
- User needs to configure custom domains

### SHOULD NOT Use When
- S3 bucket operations only → delegate to: `aws-s3-ops`
- ELB operations → delegate to: `aws-elb-ops`
- Route53 operations → delegate to: `aws-route53-ops`

### Delegation
- S3 → `aws-s3-ops` (origin bucket)
- Route53 → `aws-route53-ops` (DNS/alias records)
- ACM → `aws-acm-ops` (SSL/TLS certificates)
- Lambda → `aws-lambda-ops` (Lambda@Edge)

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | CloudFront uses us-east-1 |
| `{{user.DistributionId}}` | User input | Ask once; reuse |
| `{{user.Domain}}` | User input | example.com |
| `{{user.OriginDomain}}` | User input | mybucket.s3.amazonaws.com |
| `{{user.AcmCertArn}}` | User input | ACM cert ARN (us-east-1) |
| `{{user.ETag}}` | Last API response | Required for updates (from get-distribution-config) |

## Execution Flow

**Pre-flight**: `aws --version` + `aws sts get-caller-identity`. Verify origin exists (S3/ELB). Check SSL cert in us-east-1.

**CLI (primary)**: `aws cloudfront [command] --output json` — see [references/aws-cli-usage.md](references/aws-cli-usage.md).

**boto3 (fallback)**: After 3 CLI failures, switch to SDK — see [references/boto3-sdk-usage.md](references/boto3-sdk-usage.md).

**Validate**: Use `get-distribution --id {{u.id}}` to poll. Status: `InProgress` → `Deployed`. Max wait 15 min for create, 5 min for invalidation.

**Common Recovery**:
| Error | Action |
|-------|--------|
| InvalidArgument (400) | Fix distribution config; retry once |
| DistributionAlreadyExists | HALT — choose different name |
| PreconditionFailed | HALT — ETag mismatch; re-fetch with `get-distribution-config` |
| TooManyDistributions | HALT — account limit reached |
| Throttling (429) | Backoff, retry 3x |
| InternalError (5xx) | Retry 3x; HALT |

## Safety Gates

### Distribution Deletion
```
⚠️ Distribution must be DISABLED before deletion.
1. `update-distribution` with Enabled=false
2. Wait for Deployed status
3. Confirm: Type DELETE {{user.DistributionId}} to proceed.
```

## Related Skills

- `aws-s3-ops` — S3 origin bucket
- `aws-route53-ops` — DNS alias
- `aws-acm-ops` — SSL/TLS certificates

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](../aws-skill-generator/references/integration.md)
## Quality Gate (GCL)

> Phase 1 GCL rollout (2026-06-04, required). Every execution of
> `aws-cloudfront-ops` MUST be wrapped by the Generator-Critic-Loop
> defined in `aws-skill-generator/references/gcl-spec.md`.

| Setting | Value |
|---|---|
| Class | `required` |
| `max_iterations` | `2` |
| Rubric | `references/rubric.md` (v1) |
| Prompts | `references/prompt-templates.md` (v1) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |

Destructive ops requiring `{{user.safety_confirm}}` in trace:

- `delete-distribution` — **MUST disable first** (`update-distribution
  --enabled false`, poll `Status=Deployed`); `confirm=DELETE_DISTRIBUTION <id>`
- `delete-distribution` on prod-tagged —
  `confirm=DELETE_PROD_DISTRIBUTION <id>`
- `delete-streaming-distribution`
- `delete-key-group` — pre-flight: list distributions referencing it
- `delete-origin-access-control` — pre-flight: list distributions using it
- `delete-realtime-log-config`
- `delete-function` (CloudFront Functions / Lambda@Edge) — pre-flight:
  list associations

Relevant AWS rules from `gcl-spec.md` §8: A7 (region; canonical
`us-east-1` since CloudFront is global), A8 (resource echo-back),
A9 (no env-var / secret values in `Comment` field; rule A10 (sts
first command).

See `references/rubric.md` for the 5-dimension rubric and `references/prompt-templates.md` for G/C/O skeletons.
