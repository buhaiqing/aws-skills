# Integration Setup — AWS Config

See: `aws-skill-generator/references/integration.md` for general setup.

## IAM Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "config:*",
        "iam:CreateServiceLinkedRole",
        "s3:GetBucketAcl",
        "s3:PutBucketPolicy",
        "sns:Publish",
        "lambda:InvokeFunction"
      ],
      "Resource": "*"
    }
  ]
}
```

## Service-linked Role

```bash
aws iam create-service-linked-role --aws-service-name config.amazonaws.com --output json
```

## S3 Bucket Policy (for delivery channel)

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "config.amazonaws.com" },
    "Action": "s3:PutObject",
    "Resource": "arn:aws:s3:::my-config-bucket/*"
  }]
}
```