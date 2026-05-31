# Core Concepts — WAF

## What is AWS WAF

- **Purpose**: Web Application Firewall — protects web applications from common web exploits
- **Category**: Security, Identity & Compliance
- **Console**: https://console.aws.amazon.com/wafv2/
- **Docs**: https://docs.aws.amazon.com/waf/
- **Pricing**: Web ACL $5/mo + $0.60/million requests; Managed Rules $25/mo per rule group

## WAF v2 Components

| Component | Description |
|-----------|-------------|
| **Web ACL** | Container for rules, associated with ALB/CloudFront/API GW |
| **Rule** | Inspection criteria + action (Allow, Block, Count, Captcha) |
| **Rule Group** | Reusable collection of rules |
| **IP Set** | List of IP addresses/CIDRs |
| **Regex Pattern Set** | List of regex patterns |
| **Capacity (WCU)** | Rule complexity units (max 1,500 per Web ACL, adjustable) |

## Rule Actions

| Action | Description | AIOps Use |
|--------|-------------|-----------|
| `Allow` | Allow request to proceed | Normal operation |
| `Block` | Block request with 403 | DDoS mitigation |
| `Count` | Count without blocking | Test new rules before enabling |
| `Captcha` | Challenge with CAPTCHA | Suspicious but not malicious |

## AWS Managed Rule Groups

| Rule Group | WCU | Protection |
|-----------|-----|------------|
| AWSManagedRulesCommonRuleSet | 700 | SQLi, XSS, LFI, RFI, SSRF |
| AWSManagedRulesAdminProtection | 200 | Admin access attempts |
| AWSManagedRulesKnownBadInputs | 200 | Known bad patterns |
| AWSManagedRulesSQLiRuleSet | 400 | SQL injection |
| AWSManagedRulesLinuxRuleSet | 200 | Linux-specific exploits |
| AWSManagedRulesUnixRuleSet | 100 | Unix-specific exploits |
| AWSManagedRulesWindowsRuleSet | 150 | Windows-specific exploits |
| AWSManagedRulesPHPRuleSet | 100 | PHP-specific exploits |
| AWSManagedRulesWordpressRuleSet | 150 | WordPress-specific |
| AWSManagedRulesAmazonIpReputationList | 50 | Known malicious IPs |
| AWSManagedRulesAnonymousIpList | 50 | VPN/Proxy/Tor IPs |
| AWSManagedRulesBotControlRuleSet | 50 | Bot detection |

## Rate-Based Rules

Rate-based rules track request rate from a source and block when exceeds threshold:

| Key Type | Aggregation | Use Case |
|----------|-------------|----------|
| IP | Per source IP | Basic DDoS protection |
| Forwarded IP | Per X-Forwarded-For | Behind CDN/proxy |
| Cookie | Per cookie value | Application-layer DDoS |
| Header | Per header value | Targeted header attacks |
| Query Parameter | Per query param | Query-based DDoS |

## Scope

| Scope | Supports | Region Requirement |
|-------|----------|-------------------|
| REGIONAL | ALB, API Gateway, AppSync | Same region as resource |
| CLOUDFRONT | CloudFront distributions | us-east-1 only |

## AIOps: WAF Metrics

| Metric | Namespace | Description |
|--------|-----------|-------------|
| AllowedRequests | AWS/WAFV2 | Allowed request count |
| BlockedRequests | AWS/WAFV2 | Blocked request count |
| CountedRequests | AWS/WAFV2 | Counted request count |
| AllowedRequestsByRule | AWS/WAFV2 | Per-rule breakdown |
| BlockedRequestsByRule | AWS/WAFV2 | Per-rule block breakdown |

```bash
# Check WAF effectiveness
aws cloudwatch get-metric-statistics --namespace AWS/WAFV2 \
  --metric-name BlockedRequests \
  --dimensions Name=Rule,Value=All Name=WebACL,Value={{web_acl_name}} \
  --statistics Sum --period 3600
```

## Best Practices

- Start with Count mode for new rules (tune before enabling Block)
- Enable AWS Managed Rules CommonRuleSet + IP Reputation as baseline
- Use rate-based rules with baseline + 2x burst allowance
- Enable SampledRequests + CloudWatch metrics for visibility
- Log blocked requests for post-mortem analysis
- Regularly review BlockedRequests trend for anomalies