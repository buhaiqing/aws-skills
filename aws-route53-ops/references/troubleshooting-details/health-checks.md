# Route53 Health Check Failures — Detailed Recovery

## Diagnosis

```bash
aws route53 get-health-check --health-check-id {{check_id}}
curl -I http://{{endpoint}}/{{path}}
```

## Common Causes

- Endpoint down
- Security group blocking health check IPs
- SSL certificate expired
- Path returns non-200 status

## Resolution

1. Verify endpoint is accessible
2. Check security groups allow Route53 health checker IPs
3. Ensure HTTP response code is 200
4. Review CloudWatch logs for errors