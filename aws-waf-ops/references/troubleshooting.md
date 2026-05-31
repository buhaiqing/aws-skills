# Troubleshooting — WAF

## Common Error Codes

| Error | Agent Action |
|-------|-------------|
| WAFDuplicateItemException (400) | HALT; use different name |
| WAFInvalidParameterException (400) | Fix parameter; retry once |
| WAFLimitsExceededException (400) | HALT; reduce WCU or request increase |
| WAFNonexistentItemException (404) | HALT; verify ARN/ID |
| WAFInternalErrorException (500) | Retry 3x; HALT |
| WAFAssociatedItemException (409) | HALT; disassociate first |
| WAFUnavailableEntityException (400) | HALT; resource not found |
| WAFSubscriptionNotFoundException (400) | Subscribe to WAF first |
| ThrottlingException (429) | Backoff; retry 3x |

## Diagnostic Order

1. **Verify Web ACL exists**: `aws wafv2 get-web-acl --name {{name}} --scope {{scope}} --id {{id}}`
2. **Check association**: `aws wafv2 get-web-acl-for-resource --resource-arn {{arn}}`
3. **Check rule capacity**: `aws wafv2 check-capacity`
4. **Check CloudWatch metrics**: `get-metric-statistics BlockedRequests`
5. **Check sampled requests**: `aws wafv2 get-sampled-requests`

## Common Issues

### Web ACL Not Blocking Expected Traffic

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Malicious traffic reaching ALB | Web ACL not associated | `aws wafv2 associate-web-acl` |
| Rules not matching | Rule in Count mode (not Block) | Change action to Block |
| Rate limit too high | Legitimate traffic blends in | Lower rate limit threshold |
| Wrong scope | REGIONAL vs CLOUDFRONT | Check scope matches resource |

### Cannot Delete Web ACL

| Symptom | Cause | Resolution |
|---------|-------|------------|
| "Associated with resource" | Still linked to ALB/CF | Disassociate first |
| Lock token mismatch | Stale lock token | Re-read Web ACL to get new token |

### Web ACL Performance Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| ALB latency increases | Too many rules | Reduce WCU; use managed rules |
| False positives blocking good traffic | Rules too aggressive | Switch to Count mode; tune |
| Rate limit false triggers | Legitimate traffic spikes | Increase limit or use forwarded IP |

## AIOps: DDoS/Rate Limit RCA

```
Trigger: ALB RequestCount spike + WAF blocked requests spike
┌──────────────────────────────────────────────────────────────────┐
│ Step 1 — Check WAF BlockedRequests trend                         │
│ aws cloudwatch get-metric-statistics --namespace AWS/WAFV2      │
│   --metric-name BlockedRequests                                 │
│   --dimensions Name=WebACL,Value={{name}} Name=Rule,Value=All   │
│                                                                  │
│ Step 2 — Check sampled requests for attack pattern               │
│ aws wafv2 get-sampled-requests ...                             │
│                                                                  │
│ Step 3 — Check source IP diversity                              │
│ # Many unique IPs → possible DDoS                               │
│ # Few IPs repeated → possible scraping or brute force           │
│                                                                  │
│ Step 4 — Action                                                  │
│ → DDoS pattern: [AUTO_HEAL] lower rate limit                    │
│ → Brute force: [AI_ASSIST] add IP set block rule                │
│ → False positive: [AI_ASSIST] adjust rule in Count mode         │
└──────────────────────────────────────────────────────────────────┘
```

## Permissions Required

| Action | Minimum IAM Permissions |
|--------|-------------------------|
| Create/Update Web ACL | `wafv2:CreateWebACL`, `wafv2:UpdateWebACL` |
| Delete Web ACL | `wafv2:DeleteWebACL` |
| Associate/Disassociate | `wafv2:AssociateWebACL`, `wafv2:DisassociateWebACL` |
| List/Describe | `wafv2:ListWebACLs`, `wafv2:GetWebACL` |
| Logging | `wafv2:PutLoggingConfiguration` |
| Get Sampled Requests | `wafv2:GetSampledRequests` |
| Associate ALB | `elasticloadbalancing:SetWebACL` |

## Recovery Actions

| Error | Max Retries | Action |
|-------|-------------|--------|
| WAFInternalErrorException | 3 | Backoff 2s, 4s, 8s; HALT |
| ThrottlingException | 3 | Exponential backoff |
| WAFInvalidParameterException | 1 | Fix; retry once |
| WAFDuplicateItemException | 0 | HALT; use different name |
| WAFAssociatedItemException | 0 | HALT; disassociate first |

## Diagnostic Commands

```bash
# Full Web ACL details
aws wafv2 get-web-acl --name {{name}} --scope REGIONAL --id {{id}}

# Check association
aws wafv2 get-web-acl-for-resource --resource-arn {{lb_arn}}

# Check sampled blocked requests
aws wafv2 get-sampled-requests --web-acl-arn {{arn}} \
  --rule-metric-name All \
  --scope REGIONAL \
  --time-window StartTime={{t0-1h}},EndTime={{t0}}

# Check capacity
aws wafv2 check-capacity --scope REGIONAL --rules '[]'
```
