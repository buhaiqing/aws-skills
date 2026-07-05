# CloudTrail S3 Bucket Errors — Detailed Recovery

## S3BucketNotFound

Bucket doesn't exist or wrong name.

```bash
# Verify bucket exists
aws s3 ls s3://{{bucket_name}}/ --region {{region}}

# Create if needed
aws s3api create-bucket --bucket {{bucket_name}} --region {{region}}
# us-east-1: no LocationConstraint needed
```

## InsufficientS3BucketPolicy

Bucket policy doesn't allow CloudTrail write access.

```bash
account_id=$(aws sts get-caller-identity --query Account --output text)

aws s3api put-bucket-policy --bucket {{bucket_name}} --policy '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AWSCloudTrailAclCheck",
      "Effect": "Allow",
      "Principal": {"Service": "cloudtrail.amazonaws.com"},
      "Action": "s3:GetBucketAcl",
      "Resource": "arn:aws:s3:::{{bucket_name}}"
    },
    {
      "Sid": "AWSCloudTrailWrite",
      "Effect": "Allow",
      "Principal": {"Service": "cloudtrail.amazonaws.com"},
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::{{bucket_name}}/{{prefix}}/AWSLogs/'${account_id}'/*",
      "Condition": {"StringEquals": {"s3:x-amz-acl": "bucket-owner-full-control"}}
    }
  ]
}'
```

## S3BucketNotPublic

Bucket has overly permissive public access settings.

```bash
aws s3api get-public-access-block --bucket {{bucket_name}}

aws s3api put-public-access-block --bucket {{bucket_name}} \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=false,RestrictPublicBuckets=false"
```
