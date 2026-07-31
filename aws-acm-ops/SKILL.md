---
name: aws-acm-ops
description: >-
  Use when the user needs to request, import, validate, or manage SSL/TLS certificates
  via AWS Certificate Manager (ACM); configure DNS or email validation; check certificate
  expiry and renewal status; bind certificates to ALB, NLB, CloudFront, or API Gateway
  listeners; diagnose certificate validation failures or renewal issues; perform automated
  certificate lifecycle management with expiry monitoring and renewal triggering.

  (AIOps) Use when monitoring certificate expiry (30/14/7 day warnings), automated
  renewal triggering, certificate health audits across services, or diagnosing
  TLS handshake failures in load balancers and CDN distributions.
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials. Requires Route53
  DNS zone for DNS validation (recommended) or email access for email validation.
metadata:
  author: aws
  version: "1.0.0"
  last_updated: "2026-07-31"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  aiops_level: full-chain
  destructive_ops_require_confirm: true
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
  cross_skill_deps:
    - aws-route53-ops       # DNS validation record creation
    - aws-elb-ops            # Certificate binding to HTTPS listeners
    - aws-cloudfront-ops     # Certificate binding to CloudFront distributions
    - aws-cloudwatch-ops     # Certificate expiry metrics and alarms
  orchestrator_aware: true
  orchestrator_compat: ">=0.10"
  delegate:
    accepts: ['health-check', 'self-heal']
    produces_facts: ['state', 'event']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---
# AWS ACM Operations Skill

Use for ACM certificates, DNS/email validation, renewal, import/export, bindings to ALB/CloudFront/API Gateway, expiry monitoring, and TLS diagnosis. Detailed commands remain in references.

## Common JSON Paths

Certificate: .Certificate.{CertificateArn,DomainName,Status,InUseBy,NotAfter,KeyAlgorithm,RenewalEligibility}
Certificates: .CertificateSummaryList[].{CertificateArn,DomainName,Status,Type,NotAfter}
Validation: .Certificate.DomainValidationOptions[].{DomainName,ValidationStatus,ResourceRecord}

## Trigger & Scope

### SHOULD Use When
ACM certificates, validation records, renewal, expiry, TLS, or certificate bindings.

### SHOULD NOT Use When
Route53 DNS records → `aws-route53-ops`; ALB → `aws-elb-ops`; CloudFront → `aws-cloudfront-ops`; API Gateway → `aws-apigateway-ops`.

## Variable Convention

| Placeholder | Source | Use |
|---|---|---|
| `{{env.AWS_*}}` | Runtime env | Never ask; fail closed if unset |
| `{{user.cert_arn}}`, `{{user.domain_name}}`, `{{user.validation_method}}` | User input | Certificate identity/validation |
| `{{user.service_arn}}`, `{{user.region}}` | User input | Binding and region |
| `{{output.*}}` | API response | Reuse certificate/status/validation records |

## Execution Flow

Every operation follows **Pre-flight → Execute → Validate → Recover**. Verify region (CloudFront requires us-east-1), domain ownership, validation records, key algorithm, service bindings, renewal status, and deployment impact. Use CLI `--output json`, then boto3 after 3 CLI failures. Poll certificate status and binding; recover with bounded retries and halt on validation, in-use, or region errors. See references for commands.

## Operations and Safety

| Operation | Pre-flight / validation | Confirmation |
|---|---|---|
| Request/import certificate | Validate domain/SAN, validation method, key algorithm | — |
| Create validation records | Verify exact DNS records and zone ownership | — |
| Renew/rebind certificate | Inspect service listener/distribution and expiry; validate deployment | Token for production binding |
| Delete certificate | `describe-certificate` and inspect `InUseBy`; warn HTTPS breakage | `confirm=DELETE_CERT <arn>` |
| Auto-bind/auto-renew | Correlate expiry and service health; bounded changes only | AUTO_HEAL within approved scope |

Never log private keys, certificate bodies, DNS validation secrets, or account credentials.

## Quality Gate (GCL)

Required GCL, `max_iter=2`, rubric `references/rubric.md`, prompts `references/prompt-templates.md`; persist traces under `./audit-results/`. Apply A7–A10; Safety=0 aborts.

## Token Efficiency

TE-1…TE-6 apply; query live certificate/binding state, keep SDK examples comment-only, centralize JSON paths above, use asset anchors, and keep flows single-sourced.

## Reference Files

[aws-cli-usage.md](references/aws-cli-usage.md) · [boto3-sdk-usage.md](references/boto3-sdk-usage.md) · [core-concepts.md](references/core-concepts.md) · [troubleshooting.md](references/troubleshooting.md) · [rubric.md](references/rubric.md) · [prompt-templates.md](references/prompt-templates.md)

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md): parse `aiops_delegate`; deduplicate writes by `idempotency_key` for 24h; require `confirmation_token` for certificate deletion/production rebinding; `MANUAL` never writes, `AI_ASSIST` writes only with token, `AUTO_HEAL` permits bounded renewal/rebinding; propagate `trace_id` as `User-Agent: aiops-orchestrator/<trace_id>` and always emit `aiops_context` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).

