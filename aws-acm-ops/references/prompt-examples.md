# ACM Skill — AIOps Prompt Examples

_Lastest update: 2026-05-31_

---

## Scenario 1: Certificate expiring soon

### User Prompt
```
My SSL certificate for example.com expires in 20 days. Handle it.
```

### Agent Execution
| Step | Action | Decision |
|------|--------|----------|
| 1. Describe certificate | `aws acm describe-certificate --certificate-arn {{arn}}` | |
| 2. Check type | DNS-validated → auto-renewal enabled | `[AUTO_HEAL]` |
| 3. Verify renewal | Check Status and RenewalEligibility | |
| 4. Bind renewed cert to LB | `aws elbv2 modify-listener` | → aws-elb-ops |

```bash
aws acm describe-certificate --certificate-arn {{arn}} --query "Certificate.{Status:Status,Expiry:NotAfter,Type:Type,RenewalEligibility:RenewalEligibility}"
```

---

## Scenario 2: HTTPS listener creation with new cert

### User Prompt
```
I have a new cert for api.example.com. Bind it to my ALB's HTTPS listener.
```

### Agent Execution
```bash
aws elbv2 create-listener --load-balancer-arn {{lb_arn}} --protocol HTTPS --port 443 --certificates CertificateArn={{cert_arn}} --default-actions Type=forward,TargetGroupArn={{tg_arn}}
```

---

## Scenario 3: Cert health audit

### User Prompt
```
Check all certificates across all regions. Any expiring soon?
```

### Agent Execution
```bash
for region in $(aws ec2 describe-regions --query "Regions[].RegionName" --output text); do
  aws acm list-certificates --region $region --certificate-statuses ISSUED --output json | jq -r '.CertificateSummaryList[] | "\(.DomainName) \(.CertificateArn)"'
done
```

---

## Quick Reference

| User says | Scenario | Decision | Modules |
|-----------|----------|----------|---------|
| "Certificate expires in 20 days" | Expiry check + auto-renew | `[AUTO_HEAL]` | acm + elb |
| "Bind cert to ALB HTTPS listener" | Listener binding | `[AI_ASSIST]` | acm + elb |
| "Check all certs across regions" | Health audit | `[AI_ASSIST]` | acm |