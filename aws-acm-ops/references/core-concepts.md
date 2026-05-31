# Core Concepts — ACM

## What is AWS ACM

- **Purpose**: AWS Certificate Manager — provisions, manages, and deploys public and private SSL/TLS certificates
- **Category**: Security, Identity & Compliance
- **Console**: https://console.aws.amazon.com/acm/home
- **Docs**: https://docs.aws.amazon.com/acm/
- **Pricing**: https://aws.amazon.com/certificate-manager/pricing/ (public certs: free)

## Certificate Types

| Type | Source | Auto-Renewal | Use Case |
|------|--------|-------------|----------|
| **ACM-issued** | Requested via ACM | ✅ Yes (DNS validation) | Recommended for all AWS workloads |
| **ACM-issued** (email) | Requested via ACM | ⚠️ Manual click | Legacy; prefer DNS validation |
| **Imported** | Uploaded from third-party CA | ❌ No (manual re-import) | Existing certs, private CAs |
| **Private CA** | ACM Private CA | ✅ Managed by CA | Internal-only services |

## Validation Methods

| Method | How It Works | Auto-Renewal | Time to Issue |
|--------|-------------|-------------|---------------|
| **DNS validation** | Add CNAME record to DNS zone | ✅ Yes | Minutes |
| **Email validation** | Click link in email sent to domain admin | ❌ No | Hours-days |

> **Recommendation**: Always use DNS validation. It enables automatic renewal and is faster.

## Certificate States

| State | Description |
|-------|-------------|
| `PENDING_VALIDATION` | Awaiting DNS or email validation |
| `ISSUED` | Active and ready to use |
| `INACTIVE` | Admin disabled (uncommon) |
| `EXPIRED` | Past expiry date; cannot be used |
| `VALIDATION_TIMED_OUT` | Validation not completed within 72 hours |
| `REVOKED` | Explicitly revoked |
| `FAILED` | Certificate request or renewal failed |

## Key Attributes (from `describe-certificate`)

| Attribute | JSON Path | AIOps Use |
|-----------|-----------|-----------|
| DomainName | `.Certificate.DomainName` | Identity |
| SubjectAlternativeNames | `.Certificate.SubjectAlternativeNames` | SAN coverage |
| Status | `.Certificate.Status` | Health check |
| Type | `.Certificate.Type` | `AMAZON_ISSUED` or `IMPORTED` |
| IssuedAt | `.Certificate.IssuedAt` | Age tracking |
| NotAfter | `.Certificate.NotAfter` | **Expiry monitoring** |
| RenewalEligibility | `.Certificate.RenewalEligibility` | `ELIGIBLE` or `INELIGIBLE` |
| InUseBy | `.Certificate.InUseBy[]` | Usage tracking |
| DomainValidationOptions | `.Certificate.DomainValidationOptions` | Validation status per domain |

## Certificate Binding (Services That Use ACM)

| Service | Binding Point | Notes |
|---------|-------------|-------|
| **ALB** | HTTPS/HTTPS listener | Up to 25 certs per ALB via SNI |
| **NLB** | TLS listener | Single cert per listener |
| **CloudFront** | Distribution viewer protocol policy | **Must be in us-east-1** |
| **API Gateway** | Custom domain name | Regional or edge-optimized |
| **Elastic Beanstalk** | Environment configuration | Integrated via LB |

## Quotas

| Quota | Default | Adjustable |
|-------|---------|------------|
| Certificates per region | 2500 | Yes |
| Certificate transparency log | 5 entries per certificate | No |
| Domain names per certificate | 10 | No (use wildcard) |
| Certificate request rate | 10 per second | Yes |

## Best Practices

### Security
- Use DNS validation (enables auto-renewal)
- Use wildcard certificates (`*.example.com`) to cover multiple subdomains
- Monitor certificate expiry (see AIOps section)
- Use separate certificates for separate security domains

### Performance
- One wildcard cert vs many SAN certs: wildcard is simpler
- CloudFront requires certificates in `us-east-1`
- Certificate validation can take minutes (DNS) to hours (email)

### AIOps
- Set CloudWatch alarms for certificates expiring within 30 days (via custom metrics)
- Run weekly certificate expiry scans across all regions
- Automate DNS validation record creation via Route53
- Monitor `ClientTLSNegotiationErrorCount` on ALB — may indicate cert issues

## AIOps: Certificate Lifecycle Monitoring

```
Certificate Age Timeline:
   Created        Auto-Renewal (DNS)    Expiry Warning   Expired
      │                  │                   │              │
      ▼                  ▼                   ▼              ▼
  ─────┼──────────────────┼───────────────────┼──────────────┼────→
      T0              T0 + 11mo          T0 + 12mo - 30d  T0 + 13mo
                                          └── AIOps Alerts:
                                              - 30d: [MANUAL] inform
                                              - 14d: [AI_ASSIST] verify auto-renewal
                                              - 7d:  [AUTO_HEAL] force renew
```

## Services That Cannot Use ACM

- EC2 instances (directly): use ELB with ACM or install cert on OS
- On-premises servers: ACM certs cannot be exported (use third-party CA)
- IoT devices: use IoT certificate
