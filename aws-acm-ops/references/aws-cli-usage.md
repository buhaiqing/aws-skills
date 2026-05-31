# AWS CLI Usage — ACM

## Common JSON Paths

```
# Request Certificate:   .CertificateArn
# Describe Certificate:  .Certificate.{DomainName,Status,Type,IssuedAt,NotAfter,InUseBy,RenewalEligibility}
# List Certificates:     .CertificateSummaryList[].{DomainName,CertificateArn,Status}
# Delete Certificate:    Empty (success)
```

## Command Map

| Goal | CLI Command |
|------|-------------|
| Request certificate | `aws acm request-certificate` |
| Describe certificate | `aws acm describe-certificate` |
| List certificates | `aws acm list-certificates` |
| Delete certificate | `aws acm delete-certificate` |
| Renew certificate | `aws acm renew-certificate` |
| Import certificate | `aws acm import-certificate` |
| Add tags to certificate | `aws acm add-tags-to-certificate` |
| List tags | `aws acm list-tags-for-certificate` |
| Get certificate | `aws acm get-certificate` (download PEM) |
| Export certificate | `aws acm export-certificate` (with private key, IMPORTED only) |

## Common Patterns

### Request Certificate (DNS Validation)
```bash
aws acm request-certificate \
  --domain-name "example.com" \
  --validation-method DNS \
  --subject-alternative-names "www.example.com" \
  --tags Key=AIOps,Value=true \
  --output json
```

### Request Certificate (Email Validation)
```bash
aws acm request-certificate \
  --domain-name "example.com" \
  --validation-method EMAIL \
  --output json
```

### Describe Certificate
```bash
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:region:account:certificate/uuid \
  --output json
```

### Get Validation Records (for DNS setup)
```bash
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:region:account:certificate/uuid \
  --query "Certificate.DomainValidationOptions[].ResourceRecord"
```

### List All Issued Certificates
```bash
aws acm list-certificates --certificate-statuses ISSUED --output json
```

### List Certificates Expiring Soon
```bash
aws acm list-certificates --certificate-statuses ISSUED --output json \
  | jq -r '.CertificateSummaryList[] | .CertificateArn' \
  | while read arn; do
      desc=$(aws acm describe-certificate --certificate-arn "$arn")
      expiry=$(echo "$desc" | jq -r '.Certificate.NotAfter')
      days_left=$(( ( $(date -d "$expiry" +%s) - $(date +%s) ) / 86400 ))
      domain=$(echo "$desc" | jq -r '.Certificate.DomainName')
      echo "$domain: $days_left days remaining ($expiry)"
    done
```

### Delete Certificate
```bash
# Safety Gate: Confirm with user; check InUseBy first
aws acm describe-certificate --certificate-arn arn:aws:acm:region:account:certificate/uuid \
  --query "Certificate.InUseBy"
aws acm delete-certificate \
  --certificate-arn arn:aws:acm:region:account:certificate/uuid
```

### Import Certificate (Third-Party CA)
```bash
aws acm import-certificate \
  --certificate fileb://cert.pem \
  --private-key fileb://private-key.pem \
  --certificate-chain fileb://chain.pem \
  --tags Key=AIOps,Value=true \
  --output json
```

## Waiters

| Operation | Wait Condition | Max Wait |
|-----------|---------------|----------|
| Certificate issued | `.Certificate.Status == "ISSUED"` | 72 hours (validation timeout) |
| Certificate deleted | `describe-certificate` → ResourceNotFoundException | 1 min |

## AIOps Commands

### Certificate Expiry Monitoring
```bash
# List all certs with expiry in JSON for analysis
aws acm list-certificates --certificate-statuses ISSUED --output json \
  | jq -r '.CertificateSummaryList[] | "\(.DomainName) \(.CertificateArn)"' \
  | while IFS=' ' read domain arn; do
      aws acm describe-certificate --certificate-arn "$arn" \
        --query "Certificate.{Domain:DomainName,Type:Type,Status:Status,Expires:NotAfter,InUse:length(InUseBy[@})}" \
        --output json
    done \
  | jq -s '. | sort_by(.Expires)'
```

### Force Check and Trigger Renewal
```bash
# Check renewal eligibility
aws acm describe-certificate --certificate-arn {{cert_arn}} \
  --query "Certificate.{RenewalEligibility:RenewalEligibility,Status:Status,Type:Type}"

# If eligible and DNS-validated
aws acm renew-certificate --certificate-arn {{cert_arn}}
```

### Health Audit Across Regions
```bash
for region in us-east-1 us-west-2 eu-west-1 ap-southeast-1; do
  echo "=== $region ==="
  aws acm list-certificates --region $region --certificate-statuses ISSUED \
    --query "CertificateSummaryList[].DomainName" --output json
done
```
