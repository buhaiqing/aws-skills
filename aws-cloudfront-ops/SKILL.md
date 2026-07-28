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
  destructive_ops_require_confirm: true
  environment: [AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION]
  gcl: {enabled: true, class: required, max_iter: 2, rubric_version: v1, rubric_ref: references/rubric.md, prompts_ref: references/prompt-templates.md, pilot: false}
  orchestrator_aware: true
  orchestrator_compat: ">=0.10"
  delegate:
    accepts: ['health-check', 'self-heal', 'change-impact']
    produces_facts: ['metric', 'config', 'state']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---
# AWS CloudFront Ops Skill

## Common JSON Paths (Centralized)

```
CreateDistribution: .Distribution.{Id,DomainName,Status}
GetDistribution: .Distribution.{Id,DomainName,Status}
ListDistributions: .DistributionList.Items[].{Id,DomainName,Status}
CreateInvalidation: .Invalidation.{Id,Status}
GetInvalidation: .Invalidation.Status
CreateOAI: .CloudFrontOriginAccessIdentity.{Id,S3CanonicalUserId}
```

## Trigger & Scope

### SHOULD Use When
Use for CloudFront distributions, CDN origins/cache, invalidations, custom domains, or TLS.

### SHOULD NOT Use When
S3-only → `aws-s3-ops`; ELB → `aws-elb-ops`; DNS → `aws-route53-ops`.

### Delegation
S3 → `aws-s3-ops`; Route53 → `aws-route53-ops`; ACM → `aws-acm-ops`; Lambda@Edge → `aws-lambda-ops`.

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

## Token Efficiency

TE-1…TE-6 apply; query live distribution data, keep SDK examples comment-only, centralize JSON paths above, use asset anchors, and keep flows single-sourced.

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](../aws-skill-generator/references/integration.md)
## Quality Gate (GCL)
Required GCL, `max_iter=2`, rubric `references/rubric.md`, prompts `references/prompt-templates.md`; persist traces under `./audit-results/`. For deletion: disable first, poll `Status=Deployed`, then confirm `DELETE_DISTRIBUTION <id>` (prod uses `DELETE_PROD_DISTRIBUTION <id>`); apply A7–A10 from `gcl-spec.md` §8.

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md): parse `aiops_delegate`; deduplicate writes by `idempotency_key` for 24h; require `confirmation_token` for destructive ops; `MANUAL` never writes, `AI_ASSIST` writes only with token, `AUTO_HEAL` permits non-destructive writes; propagate `trace_id` as `User-Agent: aiops-orchestrator/<trace_id>` and always emit `aiops_context` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).
