# Route53 Record Set Errors — Detailed Recovery

## InvalidChangeBatch

Record syntax error or invalid values.

- Check record name format
- Verify IP addresses are valid
- Ensure CNAME values are hostnames
- Check TTL values (positive integer)

## PriorRequestNotComplete

Previous change not yet synced.

```bash
aws route53 get-change --id {{change_id}}
```