# Route53 Hosted Zone Errors — Detailed Recovery

## NoSuchHostedZone

Zone deleted or incorrect ID.

```bash
aws route53 list-hosted-zones --output json
aws route53 get-hosted-zone --id {{zone_id}}
```

## HostedZoneAlreadyExists

Zone with this name already created. Use existing zone or different name.