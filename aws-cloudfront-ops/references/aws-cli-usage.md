# AWS CLI Usage - CloudFront

AWS CLI commands for CloudFront operations. Default region is us-east-1.

## Common JSON Paths (Centralized)

```
# Create Dist:       .Distribution.{Id,DomainName,Status}
# Get Dist:          .Distribution.{Id,DomainName,Status,DistributionConfig}
# List Dists:        .DistributionList.Items[].{Id,DomainName,Status,Enabled}
# Create Inval:      .Invalidation.{Id,Status}
# Get Inval:         .Invalidation.Status
# Get Dist Config:   .{ETag,DistributionConfig}
# Create OAI:        .CloudFrontOriginAccessIdentity.{Id,S3CanonicalUserId}
```

## Distribution Operations

### Create Distribution (S3 Origin)
```bash
aws cloudfront create-distribution \
  --distribution-config file://distribution-config.json
```

### Get Distribution
```bash
aws cloudfront get-distribution --id {{user.DistributionId}}
```

### List Distributions
```bash
aws cloudfront list-distributions --max-items 10
```

### Update Distribution
```bash
# Get current config + ETag first
aws cloudfront get-distribution-config --id {{user.DistributionId}}

# Apply update
aws cloudfront update-distribution \
  --id {{user.DistributionId}} \
  --if-match {{user.ETag}} \
  --distribution-config file://updated-config.json
```

### Disable/Enable Distribution
```bash
aws cloudfront get-distribution-config --id {{user.DistributionId}}
aws cloudfront update-distribution \
  --id {{user.DistributionId}} \
  --if-match {{user.ETag}} \
  --distribution-config '{"Enabled": false}'  # or true
```

### Delete Distribution (must be disabled first)
```bash
aws cloudfront delete-distribution \
  --id {{user.DistributionId}} \
  --if-match {{user.ETag}}
```

## Origin Access Identity

### Create Origin Access Identity
```bash
aws cloudfront create-cloud-front-origin-access-identity \
  --cloud-front-origin-access-identity-config '{"CallerReference":"{{user.CallerReference}}","Comment":"{{user.OAIComment}}"}'
```

## Cache Invalidation

### Create Invalidation
```bash
# Invalidate all
aws cloudfront create-invalidation \
  --distribution-id {{user.DistributionId}} \
  --invalidation-batch '{"Paths":{"Quantity":1,"Items":["/*"]},"CallerReference":"{{ref}}"}'

# Specific paths
aws cloudfront create-invalidation \
  --distribution-id {{user.DistributionId}} \
  --invalidation-batch '{"Paths":{"Quantity":2,"Items":["/index.html","/assets/*"]},"CallerReference":"{{ref}}"}'
```

### Get Invalidation Status
```bash
aws cloudfront get-invalidation \
  --distribution-id {{user.DistributionId}} --id {{user.InvalidationId}}
```

## Common Options

```
--distribution-id {{user.DistributionId}}  # Distribution ID
--if-match {{user.ETag}}                   # Required for updates (from get-distribution-config)
--paths "/*"                               # Invalidation paths
```