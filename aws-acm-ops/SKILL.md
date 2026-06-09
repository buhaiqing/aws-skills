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
  last_updated: "2026-05-31"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  aiops_level: full-chain
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
  orchestrator_compat: ">=0.1.0"
  delegate:
    accepts: ['health-check', 'self-heal']
    produces_facts: ['state', 'event']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---

# AWS ACM Operations Skill

## Overview

AWS Certificate Manager (ACM) handles the lifecycle of SSL/TLS certificates used with AWS services. This skill covers **certificate request, import, validation, renewal, expiry monitoring, and binding** to ALB/NLB/CloudFront/API Gateway, with full AIOps support for **expiry prediction, automated renewal, certificate health audits, and TLS diagnostics**.

## Trigger & Scope

### SHOULD Use When
- User mentions "SSL certificate", "TLS", "HTTPS", "ACM"
- User needs to secure an ALB/NLB/CloudFront listener with HTTPS
- Task involves requesting or importing a certificate
- Task involves DNS or email validation
- User asks "check certificate expiry", "when does my cert expire"
- **(AIOps)** Certificate renewal issues or validation failures
- **(AIOps)** TLS handshake error diagnosis
- **(AIOps)** SSL compliance audit across services
- Keywords: certificate, cert, SSL, TLS, HTTPS, ACM, validation, renewal

### SHOULD NOT Use When
- Load balancer CRUD → delegate to: `aws-elb-ops`
- Route53 DNS record management → delegate to: `aws-route53-ops`
- CloudFront distribution config → delegate to: `aws-cloudfront-ops`
- IAM server certificate → use IAM (legacy, not ACM)
- KMS key management → delegate to: `aws-kms-ops`

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default; allow override |
| `{{env.AWS_ACCOUNT_ID}}` | Runtime env | Required for ARN construction |
| `{{user.domain_name}}` | User input | e.g., "example.com" |
| `{{user.cert_arn}}` | User input or last output | Certificate ARN from `describe-certificate` |
| `{{output.cert_arn}}` | Last API response | Parse: `.Certificate.CertificateArn` |
| `{{output.cert_status}}` | Last API response | Parse: `.Certificate.Status` |

## Execution Flow Pattern

**Pre-flight → Execute → Validate → Recover**
**AIOps: Monitor → Predict → Diagnose → Remediate → Verify**

```
Certificate Lifecycle:
  ┌──────────┐    ┌────────────┐    ┌──────────┐    ┌────────────┐
  │  Request  │ → │  Validate   │ → │   Issue   │ → │    Bind    │
  │  Cert     │    │  DNS/Email  │    │   Cert    │    │  to Service │
  └──────────┘    └────────────┘    └──────────┘    └────────────┘
                                                        │
                                                        ▼
                          ┌────────────┐    ┌──────────────────────┐
                          │  Auto-Renew │ ← │  Expiry Monitoring   │
                          │  (ACM-managed) │    │  (AIOps: 30/14/7d)   │
                          └────────────┘    └──────────────────────┘
```

---

## Operations

### Operation: Request Certificate

#### Pre-flight
```bash
aws --version && aws sts get-caller-identity --output json
```

| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `aws --version` | Install AWS CLI v2 |
| Credentials | `aws sts get-caller-identity` | HALT; log error |
| Domain validation method | Ask user: DNS or Email? | DNS recommended (faster, auto-renew) |
| **(AIOps) Check existing certs** | `aws acm list-certificates` | WARN if similar domain exists |
| **(AIOps) Route53 zone exists** | Delegate `aws-route53-ops` | HALT for DNS validation |

#### Execute — CLI (Primary)
```bash
# Basic DNS-validation certificate
aws acm request-certificate \
  --domain-name "{{user.domain_name}}" \
  --validation-method DNS \
  --subject-alternative-names "www.{{user.domain_name}}" \
  --tags Key=AIOps,Value=true \
  --output json
```
Save `{{output.cert_arn}}` from `.CertificateArn`.

#### Execute — boto3 (Fallback)
```python
import boto3
client = boto3.client('acm', region_name='us-east-1')
response = client.request_certificate(
    DomainName='example.com',
    ValidationMethod='DNS',
    SubjectAlternativeNames=['www.example.com'],
    Tags=[{'Key': 'AIOps', 'Value': 'true'}]
)
print(response['CertificateArn'])
```

#### Validate
```bash
aws acm describe-certificate --certificate-arn {{output.cert_arn}} --output json
```
Check `.Certificate.{Status,DomainValidationOptions}`.

### Operation: Create DNS Validation Records

Required for DNS validation. Delegate to `aws-route53-ops`.

#### Read validation records
```bash
aws acm describe-certificate --certificate-arn {{output.cert_arn}} \
  --query "Certificate.DomainValidationOptions[].{Domain:DomainName,Record:ResourceRecord}"
```

Output:
```
Validation Records:
  - example.com: _xxx.example.com. CNAME → _yyy.acm-validations.aws.
  - www.example.com: _zzz.www.example.com. CNAME → _www.acm-validations.aws.
```

#### Create Route53 records (delegation)
Delegate DNS record creation to `aws-route53-ops`:
```
Task: Create/upsert CNAME record
  Zone: example.com (Route53)
  Name: _xxx.example.com
  Type: CNAME
  Value: _yyy.acm-validations.aws.
  TTL: 60
```

### Operation: Describe Certificate

#### Execute — CLI
```bash
aws acm describe-certificate --certificate-arn {{user.cert_arn}} --output json
# Key paths: .Certificate.{DomainName,Status,Type,IssuedAt,NotAfter,InUseBy,RenewalEligibility}
```

### Operation: List Certificates

#### Execute — CLI
```bash
aws acm list-certificates --output json
# Filter by status
aws acm list-certificates --certificate-statuses ISSUED --output json
```

### Operation: Delete Certificate

**Safety Gate**: MUST obtain explicit user confirmation. Verify certificate not in use by any service.

```bash
# Pre-delete: Check which services use this certificate
aws acm describe-certificate --certificate-arn {{user.cert_arn}} \
  --query "Certificate.InUseBy"
```

```
[WARN] Certificate is in use by: N services
  {{service1_arn}}
  {{service2_arn}}
Deleting will break HTTPS for these services.
Type 'DELETE {{user.cert_arn}}' to confirm.
```

```bash
aws acm delete-certificate --certificate-arn {{user.cert_arn}}
```

### Operation: Renew Certificate

ACM automatically renews certificates requested via DNS validation. Manual action only needed for:
- Email-validated certificates (must click validation email)
- Imported certificates (must re-import before expiry)

```bash
# Check renewal eligibility
aws acm describe-certificate --certificate-arn {{user.cert_arn}} \
  --query "Certificate.{Type:Type,RenewalEligibility:RenewalEligibility,Status:Status}"
```

```
DNS-validated ACM cert: auto-renewal enabled. No action needed.
Email-validated ACM cert: check email for validation link if renewal pending.
Imported cert: manually re-import before expiry.
```

---

## AIOps: Certificate Expiry Monitoring & Prediction

### Expiry Monitoring Commands

```bash
# List all certificates with expiry dates, sorted by remaining days
aws acm list-certificates --certificate-statuses ISSUED --output json \
  | jq -r '.CertificateSummaryList[] | {Domain: .DomainName, ARN: .CertificateArn, Status: .Status}' \
  | while read cert; do
      arn=$(echo $cert | jq -r '.ARN')
      aws acm describe-certificate --certificate-arn "$arn" \
        --query "Certificate.{Domain:DomainName,Expiry:NotAfter,Status:Status}" \
        --output json
    done
```

### AIOps Expiry Prediction

```
Certificate Expiry Check:
  ┌─────────────────────────────────────────────────────────┐
  │ Cert: example.com (arn:aws:acm:region:acct:cert/xxx)    │
  │   Issued: 2025-06-01  Expires: 2026-06-01               │
  │   Days remaining: 32                                    │
  │   Type: DNS-validated | Auto-renewal: Enabled           │
  │                                                         │
  │   ⚠️ < 30 days → [AUTO_HEAL] no action needed           │
  │     (DNS validation enables auto-renewal)                │
  │                                                         │
  │   ❌ < 7 days → [AI_ASSIST] Force renewal check:        │
  │     aws acm renew-certificate ...                        │
  │                                                         │
  │   🔴 EXPIRED → [MANUAL] Re-issue cert immediately       │
  └─────────────────────────────────────────────────────────┘
```

### Expiry Decision Matrix

| Days Remaining | Certificate Type | Decision | Action |
|----------------|-----------------|----------|--------|
| > 45 | Any | `[MANUAL]` | No action; periodic monitoring |
| 30-45 | DNS-validated | `[MANUAL]` | Verify auto-renewal is in progress |
| 30-45 | Email-validated | `[AI_ASSIST]` | Notify user to check validation email |
| 30-45 | Imported | `[AI_ASSIST]` | Remind user to re-import before expiry |
| 7-30 | DNS-validated | `[AUTO_HEAL]` | Trigger `renew-certificate` if renewal not started |
| 7-30 | Email/Imported | `[AI_ASSIST]` | Alert: manual renewal needed |
| < 7 | Any | `[MANUAL]` | Critical: risk of HTTPS failure |

### AIOps: Certificate Health Audit

```bash
# Full certificate audit across all regions
for region in $(aws ec2 describe-regions --query "Regions[].RegionName" --output text); do
  echo "=== Region: $region ==="
  aws acm list-certificates --region $region --certificate-statuses ISSUED --output json \
    | jq -r '.CertificateSummaryList[] | "\(.DomainName) \(.CertificateArn)"'
done
```

```
[AUDIT_REPORT] Certificate Health — {{date}}
  Total certificates: N across M regions
  Expiring in 30 days: X certs
  Expiring in 7 days: Y certs (CRITICAL)
  Already expired: Z certs (IMMEDIATE ACTION REQUIRED)
  In use certificates: P of N (Q are unused → [AI_ASSIST] cleanup)
```

---

## AIOps: Auto-Bind Certificate to ELB Listener

### AH-ACM-01: Renew and Re-Bind to ALB [AUTO_HEAL]

When a certificate is renewed (or re-imported), automatically bind it to the ALB
HTTPS listener that was using the previous certificate:

```
Trigger: Certificate renewal completed for {{domain}}
┌──────────────────────────────────────────────────────────────────┐
│ Step 1 — Find listener using the OLD certificate                 │
│ aws elbv2 describe-listeners --load-balancer-arn {{lb_arn}}     │
│   --query "Listeners[?Protocol=='HTTPS']"                        │
│                                                                  │
│ Step 2 — Extract old cert ARN from listener config               │
│ Listeners[0].Certificates[0].CertificateArn                      │
│                                                                  │
│ Step 3 — Replace with NEW cert ARN                              │
│ aws elbv2 modify-listener --listener-arn {{listener_arn}}        │
│   --certificates CertificateArn={{new_cert_arn}}                │
│                                                                  │
│ Step 4 — Verify                                                  │
│ aws elbv2 describe-listeners --listener-arns {{listener_arn}}   │
│   --query "Listeners[0].Certificates"                           │
│                                                                  │
│ Step 5 — Rollback if verification fails                         │
│ aws elbv2 modify-listener ... --certificates OldArn             │
└──────────────────────────────────────────────────────────────────┘
```

**Decision**: `[AUTO_HEAL]` — reversible, no traffic interruption.
**Boundary**: Only if the LB and listener still exist at renewal time.

```bash
# Auto-bind command sequence
NEW_CERT_ARN="{{output.new_cert_arn}}"
LB_ARN="{{user.lb_arn}}"

# Find HTTPS listener
LISTENER_ARN=$(aws elbv2 describe-listeners --load-balancer-arn "$LB_ARN" \
  --query "Listeners[?Protocol=='HTTPS'].[ListenerArn]" --output text)

if [ -n "$LISTENER_ARN" ]; then
  # Replace certificate
  aws elbv2 modify-listener \
    --listener-arn "$LISTENER_ARN" \
    --certificates CertificateArn="$NEW_CERT_ARN"
  
  # Verify
  NEW_CERT=$(aws elbv2 describe-listeners --listener-arns "$LISTENER_ARN" \
    --query "Listeners[0].Certificates[0].CertificateArn" --output text)
  
  if [ "$NEW_CERT" = "$NEW_CERT_ARN" ]; then
    echo "[AUTO_HEAL] Certificate bound to $LISTENER_ARN"
  fi
fi
```

---

## Cross-Skill Orchestration

### Certificate Binding to Services

| Service | Delegation | Binding Command |
|---------|-----------|----------------|
| ALB/HTTPS Listener | `aws-elb-ops` | `create-listener --certificates CertificateArn={{cert_arn}}` |
| ALB Modify Listener (renew) | `aws-elb-ops` | `modify-listener --certificates CertificateArn={{new_cert_arn}}` |
| NLB/TLS Listener | `aws-elb-ops` | `create-listener --certificates CertificateArn={{cert_arn}}` |
| CloudFront Distribution | `aws-cloudfront-ops` | `update-distribution --viewer-certificate` |
| API Gateway Custom Domain | (future) | `create-domain-name --certificate-arn` |

### TLS Issue Diagnosis Chain

When ELB listener reports HTTPS/SSL errors:
```
TLS issue → aws-elb-ops → aws-acm-ops (cert check) → aws-route53-ops (DNS check)

Steps:
1. [aws-elb-ops] Check listener config → verify cert ARN
2. [aws-acm-ops] Describe certificate → check Status (ISSUED?), Expiry (not expired?)
3. [aws-acm-ops] Check InUseBy → is cert bound to correct LB?
4. [aws-route53-ops] Check DNS validation → CNAME still exists?
5. [aws-cloudwatch-ops] Check ClientTLSNegotiationErrorCount
```

---

## Cost Awareness

- **ACM Certificates**: Free (no additional charge for public certificates)
- **Cost**: Only the services using the certificate (ALB/CloudFront) incur cost
- **Imported certificates**: Free to store; renewal must be manual
- **Savings**: Using ACM (free) vs purchasing from third-party CA ($50-400/year)

---

## Quality Gate (GCL)

> Phase 1 GCL rollout (2026-06-04, required). Every execution of
> `aws-acm-ops` MUST be wrapped by the Generator-Critic-Loop defined in
> `aws-skill-generator/references/gcl-spec.md`.

| Setting | Value |
|---|---|
| Class | `required` |
| `max_iterations` | `2` |
| Rubric | `references/rubric.md` (v1) |
| Prompts | `references/prompt-templates.md` (v1) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |

Destructive ops requiring `{{user.safety_confirm}}` in trace:

- `delete-certificate` — IRREVERSIBLE; MUST pre-flight `describe-certificate` to check `InUseBy` array; warn user about HTTPS breakage; confirm `DELETE_CERT <arn>`

Relevant AWS rules from `gcl-spec.md` §8: A7 (region), A8 (CertificateArn echoed from `describe-certificate` / `list-certificates`), A9 (no secrets in domain names or cert data), A10 (sts first command).

### See also

- `aws-skill-generator/references/gcl-spec.md` — full GCL specification
- `references/rubric.md` — this skill's 5-dimension rubric
- `references/prompt-templates.md` — G/C/O skeletons
- Top-level `AGENTS.md` §11 — rollout index and Per-Skill Defaults

## Reference Files

- [Core Concepts & Certificate Types](references/core-concepts.md)
- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Troubleshooting & Expiry Monitoring](references/troubleshooting.md)
- [Cross-Skill: Layered Inspection](../aws-cloudwatch-ops/references/layered-inspection-template.md)

## AIOps Delegate Contract

This skill is orchestrator-aware. When invoked by
`aws-aiops-orchestrator`, it MUST honor the delegate contract.

### Recognition

If the incoming prompt contains an `aiops_delegate:` block (see
[aws-aiops-orchestrator/references/delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md)),
parse and validate:

- `request_id` — non-empty string
- `parent_intent` — one of: health-check | rca | self-heal
  | cost-forecast | capacity-forecast | change-impact
  | compliance-scan | forensic
- `action_mode` — observe | recommend | auto-heal | manual
- `decision_tier` — AUTO_HEAL | AI_ASSIST | MANUAL
- `scope.resource_ids` — array (may be empty for discovery)

### Behavior rules

1. **Idempotency**: every write operation MUST accept an
   `idempotency_key` parameter. If the same key was executed within
   the last 24h, return the cached result with
   `aiops_context.status: "ok"` and
   `aiops_context.facts[*].deduplicated: true`.
2. **Confirmation gate**: any destructive operation (delete, terminate,
   deregister, detach, disable, rotate) MUST require a
   `confirmation_token`. If absent, refuse and return
   `aiops_context.status: "failed"` with summary
   `"confirmation_token required for destructive op"`.
3. **Decision tier respect**:
   - `decision_tier: MANUAL` — never execute writes; recommendations only.
   - `decision_tier: AI_ASSIST` — recommendations; execute only if
     `confirmation_token` is present.
   - `decision_tier: AUTO_HEAL` — execute non-destructive writes
     directly; destructive ones still require `confirmation_token`.
4. **Trace propagation**: every AWS CLI / boto3 call MUST include the
   `trace_id` from the delegate block in the User-Agent header
   (`User-Agent: aiops-orchestrator/<trace_id>`).
5. **Output format**: always include a final `aiops_context:` JSON
   block in the response, even on failure.

### Cross-reference

This skill participates in the orchestrator's runbook library. See
[aws-aiops-orchestrator/references/runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md)
for which runbooks invoke this skill.

