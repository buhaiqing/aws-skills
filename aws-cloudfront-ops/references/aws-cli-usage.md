# AWS CLI Usage - CloudFront

AWS CLI commands for CloudFront operations. Default region is us-east-1.

## Distribution Operations

### Create Distribution (S3 Origin)
```bash
aws cloudfront create-distribution \
  --distribution-config '{
    "Comment": "{{user.Description}}",
    "PriceClass": "PriceClass_100",
    "Enabled": true,
    "DefaultCacheBehavior": {
      "TargetOriginId": "{{user.OriginId}}",
      "ViewerProtocolPolicy": "redirect-to-https",
      "AllowedMethods": {
        "Quantity": 2,
        "Items": ["GET", "HEAD"]
      },
      "ForwardedValues": {
        "QueryString": false,
        "Cookies": {"Forward": "none"},
        "Headers": {"Quantity": 0}
      },
      "MinTTL": 0,
      "DefaultTTL": 86400,
      "MaxTTL": 31536000
    },
    "Origins": {
      "Quantity": 1,
      "Items": [{
        "Id": "{{user.OriginId}}",
        "DomainName": "{{user.S3BucketDomain}}",
        "S3OriginConfig": {
          "OriginAccessIdentity": "{{user.OAI}}"
        }
      }]
    },
    "DefaultRootObject": "index.html",
    "Origins": {"Quantity": 1, "Items": [{"Id": "s3", "DomainName": "{{user.S3BucketDomain}}"}]}
  }' \
  --output json
```

### Get Distribution
```bash
aws cloudfront get-distribution \
  --id {{user.DistributionId}} \
  --output json
```

### List Distributions
```bash
aws cloudfront list-distributions \
  --max-items 10 \
  --output json
```

### Update Distribution
```bash
# Requires ETag from get-distribution
aws cloudfront get-distribution-config --id {{user.DistributionId}}

aws cloudfront update-distribution \
  --id {{user.DistributionId}} \
  --if-match {{user.ETag}} \
  --distribution-config file://updated-config.json \
  --output json
```

### Disable/Enable Distribution
```bash
# Get current config
aws cloudfront get-distribution-config --id {{user.DistributionId}}

# Update enabled to false/true
aws cloudfront update-distribution \
  --id {{user.DistributionId}} \
  --if-match {{user.ETag}} \
  --distribution-config '{
    ...
    "Enabled": false
  }' \
  --output json
```

### Delete Distribution
```bash
# Must be disabled first
aws cloudfront get-distribution-config --id {{user.DistributionId}}

aws cloudfront delete-distribution \
  --id {{user.DistributionId}} \
  --if-match {{user.ETag}} \
  --output json
```

## Origin Access Identity

### Create Origin Access Identity
```bash
aws cloudfront create-cloud-front-origin-access-identity \
  --cloud-front-origin-access-identity-config '{
    "CallerReference": "{{user.CallerReference}}",
    "Comment": "{{user.OAIComment}}"
  }' \
  --output json
```

## Cache Invalidation

### Create Invalidation
```bash
aws cloudfront create-invalidation \
  --distribution-id {{user.DistributionId}} \
  --invalidation-batch '{
    "Paths": {
      "Quantity": 1,
      "Items": ["/*"]
    },
    "CallerReference": "{{user.CallerReference}}"
  }' \
  --output json

# Specific paths
aws cloudfront create-invalidation \
  --distribution-id {{user.DistributionId}} \
  --invalidation-batch '{
    "Paths": {
      "Quantity": 2,
      "Items": ["/index.html", "/assets/*"]
    },
    "CallerReference": "{{uuid}}"
  }' \
  --output json
```

### Get Invalidation Status
```bash
aws cloudfront get-invalidation \
  --distribution-id {{user.DistributionId}} \
  --id {{user.InvalidationId}} \
  --output json
```

## Streaming Distribution

### Create RTMP Distribution (Legacy)
```bash
# Note: Use modern distributions instead
```

## Common Options

```bash
--distribution-id {{user.DistributionId}}  # Distribution ID
--if-match {{user.ETag}}                   # Required for updates
--paths "/*"                               # Invalidation paths
```