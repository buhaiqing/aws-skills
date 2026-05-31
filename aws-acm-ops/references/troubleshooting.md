# Troubleshooting — ACM

## Common Error Codes

| Error | Agent Action |
|-------|-------------|
| LimitExceededException (400) | HALT; request quota increase (2500 certs per region) |
| InvalidDomainValidationOptionsException (400) | Fix domain name; retry |
| TooManyTagsException (400) | Reduce tags to max 50 |
| ValidationException (400) | Check parameter values; retry |
| ResourceNotFoundException (404) | HALT; verify certificate ARN |
| RequestInProgressException (400) | Wait for existing request to complete; retry |
| ThrottlingException (429) | Backoff; retry 3x |
| InternalFailure (500) | Retry 3x; HALT |

## Diagnostic Order

1. **Verify certificate exists**: `aws acm describe-certificate --certificate-arn {{arn}}`
2. **Check status**: `.Certificate.Status` should be `ISSUED`
3. **Check expiry**: `.Certificate.NotAfter` — is certificate still valid?
4. **Check in use**: `.Certificate.InUseBy` — is cert bound to any service?
5. **Check validation**: `.Certificate.DomainValidationOptions` — validation status per domain

## Common Issues

### Certificate Validation Fails

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Validation pending > 30 min | DNS record not created or incorrect | `aws acm describe-certificate` → check `ResourceRecord` → create in Route53 |
| DNS validation times out (72h) | CNAME record missing or wrong target | Verify CNAME exists and points to correct ACM validation value |
| Email not received | WHOIS email not accessible | Check domain WHOIS for admin/tech/hostmaster emails |
| Validation shows FAILED | Domain validation rejected | Check domain is registered and resolving |

### Certificate Not Issued

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Status = `PENDING_VALIDATION` > 30m | DNS not propagating | Wait (TTL up to 24h); verify CNAME record |
| Status = `VALIDATION_TIMED_OUT` | 72h passed without validation | Re-request certificate; create DNS records immediately |
| Status = `FAILED` | Invalid domain or CA rejection | Verify domain is valid and not on blocklist |

### Certificate Binding Fails

| Symptom | Cause | Resolution |
|---------|-------|------------|
| "Certificate not found" in ELB | Wrong region | Cert must be in same region as LB |
| "Certificate not found" in CloudFront | Wrong region | CloudFront requires cert in **us-east-1** |
| "Certificate not valid" | Cert expired or not yet issued | Check `NotAfter` and `Status` |

### Renewal Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Auto-renewal not working | Email validation (not DNS) | Re-issue with DNS validation |
| Renewal shows INELIGIBLE | Imported certificate | Must re-import before expiry |
| Renewal shows PENDING_VALIDATION | Validation records missing | Re-create DNS CNAME records |
| Certificate expired | No action taken | IMMEDIATELY re-issue and re-bind to services |

## AIOps: Self-Healing & RCA

### Expiry RCA Flow

```
Trigger: Certificate within 30 days of expiry
┌───────────────────────────────────────────────────────────────────┐
│ Step 1 — Describe Certificate                                     │
│ aws acm describe-certificate --certificate-arn {{arn}}            │
│                                                                   │
│ Step 2 — Check Type & Validation Method                          │
│ AMAZON_ISSUED + DNS → Should auto-renew → check status            │
│ AMAZON_ISSUED + EMAIL → Check validation email                    │
│ IMPORTED → Manual re-import needed                                │
│                                                                   │
│ Step 3 — Check InUseBy                                            │
│ If bound to CloudFront: cert MUST be in us-east-1                 │
│ If bound to ALB: cert in same region as LB                        │
│                                                                   │
│ Step 4 — Action                                                   │
│ → DNS-validated + 14d: [AUTO_HEAL] renew-certificate              │
│ → Email-validated: [AI_ASSIST] Notify user to check email         │
│ → Imported: [AI_ASSIST] Remind user to re-import                  │
│ → Already expired: [MANUAL] Emergency re-issue + re-bind          │
└───────────────────────────────────────────────────────────────────┘
```

### TLS Handshake Failure RCA

```
Trigger: ClientTLSNegotiationErrorCount > 0 on ALB
┌───────────────────────────────────────────────────────────────────┐
│ Step 1 — Check Certificate Status                                 │
│ aws acm describe-certificate --certificate-arn {{listener_cert}}  │
│                                                                   │
│ Step 2 — Check Expiry                                             │
│ If expired → [AUTO_HEAL] not possible; [MANUAL] re-issue          │
│                                                                   │
│ Step 3 — Check SSL Policy (aws-elb-ops help)                     │
│ Old SSL policies (2016-08) may cause negotiation failures         │
│                                                                   │
│ Step 4 — Check Supported Cipher Suites                           │
│ Newer clients may not support outdated ciphers                    │
│                                                                   │
│ Step 5 — Action                                                   │
│ → Expired cert: [MANUAL] Replace certificate on listener          │
│ → Old SSL policy: [AI_ASSIST] Upgrade to ELBSecurityPolicy-FS    │
│ → Client mismatch: [MANUAL] Check client TLS version support      │
└───────────────────────────────────────────────────────────────────┘
```

## Permissions Required

| Action | Minimum IAM Permissions |
|--------|-------------------------|
| Request certificate | `acm:RequestCertificate` |
| Describe certificate | `acm:DescribeCertificate` |
| List certificates | `acm:ListCertificates` |
| Delete certificate | `acm:DeleteCertificate` |
| Renew certificate | `acm:RenewCertificate` |
| Import certificate | `acm:ImportCertificate` |
| Add tags | `acm:AddTagsToCertificate` |
| Route53 create record | `route53:ChangeResourceRecordSets` (for DNS validation) |

## Cleanup Sequence

```
1. Verify certificate not in use: describe-certificate → check InUseBy
   If InUseBy not empty → unbind from services first
2. Safely delete: delete-certificate --certificate-arn {{arn}}
3. Validate: describe → ResourceNotFoundException
```

## Recovery Actions

| Error | Max Retries | Action |
|-------|-------------|--------|
| 5xx InternalFailure | 3 | Backoff 2s, 4s, 8s; HALT after 3 |
| 429 ThrottlingException | 3 | Exponential backoff |
| 400 ValidationException | 1 | Fix; retry once |
| 400 LimitExceededException | 0 | HALT; request quota increase |
| 404 ResourceNotFoundException | 0 | HALT; verify ARN |
| 400 RequestInProgressException | 0 | Wait for completion; retry |

## Diagnostic Commands

```bash
# Full certificate details
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:region:account:certificate/uuid \
  --output json | jq '.Certificate'

# Quick health (status + expiry)
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:region:account:certificate/uuid \
  --query "Certificate.{Status:Status,Type:Type,Expires:NotAfter,InUse:length(InUseBy[@])}"

# List certs expiring within 30 days
aws acm list-certificates --certificate-statuses ISSUED --output json \
  | jq -r '.CertificateSummaryList[] | .CertificateArn' \
  | while read arn; do
      expiry=$(aws acm describe-certificate --certificate-arn "$arn" \
        --query "Certificate.NotAfter" --output text)
      days=$(( ( $(date -d "$expiry" +%s) - $(date +%s) ) / 86400 ))
      if [ "$days" -lt 30 ] && [ "$days" -ge 0 ]; then
        domain=$(aws acm describe-certificate --certificate-arn "$arn" \
          --query "Certificate.DomainName" --output text)
        echo "⚠️  $domain: $days days remaining ($expiry)"
      fi
    done
```

## Access Logs

ACM does not generate access logs. Use CloudTrail for API activity:
```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceType,AttributeValue=AWS::ACM::Certificate \
  --start-time "$(date -d '-7 days' -u +%Y-%m-%dT00:00:00Z)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --query "Events[].{Time:EventTime,Name:EventName,User:Username}"
```
