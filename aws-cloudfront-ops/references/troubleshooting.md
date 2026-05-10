# CloudFront Troubleshooting

Common CloudFront error codes, recovery procedures.

## Error Code Reference

### Distribution Errors

#### NoSuchDistribution
```
Error: Distribution {{dist_id}} does not exist
```
**Resolution**: List distributions to verify ID.

#### DistributionNotDisabled
```
Error: Cannot delete enabled distribution
```
**Resolution**: Disable distribution first.

#### PreconditionFailed
```
Error: ETag mismatch
```
**Cause**: Config changed by another user.
**Resolution**: Get new config and ETag.

### Invalidation Errors

#### InvalidArgument
```
Error: Invalid path pattern
```
**Resolution**: Use valid patterns: `/path/*` or `/*`.

### Origin Errors

#### InvalidOrigin
```
Error: Invalid origin configuration
```
**Resolution**: Check origin exists and is accessible.

## Common Issues

### Cache Not Invalidating
**Causes:**
- Wrong distribution ID
- Invalid path
- Invalidation in progress

**Resolution:**
```bash
# Check invalidation status
aws cloudfront get-invalidation \
  --distribution-id {{dist_id}} \
  --id {{invalidation_id}}

# Check path format
# Valid: /*, /path/*, /path/file.ext
```

### Origin Errors (5xx)
**Causes:**
- Origin down
- SSL certificate issues
- Timeout

**Resolution:**
1. Check origin health
2. Verify SSL certificate
3. Check network connectivity
4. Review CloudFront logs

### 403 Forbidden
**Causes:**
- S3 bucket policy
- Missing OAI
- Signed URL required

**Resolution:**
```bash
# Check bucket policy
aws s3api get-bucket-policy --bucket {{bucket_name}}

# Update policy to allow CloudFront OAI
```

### Slow First Request
**Cause:** Cache miss, fetching from origin.
**Resolution:** Not an issue - expected behavior.

## Recovery Procedures

### Distribution Recovery
```
1. Check distribution status
2. Verify origin health
3. Update configuration
4. Wait for deployment (15-60 min)
```

### Invalidation Recovery
```
1. Check invalidation status
2. Verify path patterns
3. Create new invalidation if needed
4. Wait for Completion
```

### Origin Recovery
```
1. Check origin accessibility
2. Verify DNS resolution
3. Check SSL certificates
4. Update origin configuration
```