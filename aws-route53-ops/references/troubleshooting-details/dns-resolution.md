# Route53 DNS Resolution — Detailed Recovery

## Diagnosis

```bash
# Check name servers
dig NS {{zone_name}} +short

# Query specific nameserver
dig @{{name_server}} {{record_name}} +short

# Check TTL
dig {{record_name}} +noall +answer
```

## Resolution

1. Verify record exists: `list-resource-record-sets`
2. Check name servers match domain registrar
3. Wait for DNS propagation (TTL period)
4. Check for typos in record name