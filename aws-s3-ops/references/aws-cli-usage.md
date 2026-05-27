# AWS CLI Usage — S3

## Common JSON Paths (Centralized)

```
# Create:  .Location  (bucket ARN)
# List:    .Buckets[].{Name,CreationDate}
# Head:    Empty (204 — check via HTTP response)
# Put/Get/Copy:  .ETag
# Delete:  Empty (success — verify via head-object or list)
# List Objects:  .Contents[].{Key,Size,LastModified} / .IsTruncated
```

## Command Map

| Goal | CLI Command |
|------|-------------|
| Create bucket | `aws s3api create-bucket` |
| Delete bucket | `aws s3api delete-bucket` |
| List buckets | `aws s3api list-buckets` |
| Head bucket (check exists) | `aws s3api head-bucket` |
| Put object | `aws s3api put-object` |
| Get object | `aws s3api get-object` |
| List objects | `aws s3api list-objects-v2` |
| Delete object | `aws s3api delete-object` |
| Copy object | `aws s3api copy-object` |
| Head object | `aws s3api head-object` |

## Key CLI Conventions

### Output Format
Always use `--output json` for agent parsing.

### Region Handling
S3 is global namespace but buckets are regional. Use `--region` for create/delete operations.

### Bucket Naming Rules
- 3-63 characters
- Lowercase letters, numbers, hyphens, periods
- No uppercase
- Must start with letter or number
- Cannot use IP address format

## Common Patterns

### Create Bucket (with region constraint)
```bash
# For us-east-1 (no LocationConstraint needed)
aws s3api create-bucket --bucket my-bucket --region us-east-1 --output json

# For other regions
aws s3api create-bucket \
  --bucket my-bucket \
  --region us-west-2 \
  --create-bucket-configuration LocationConstraint=us-west-2 \
  --output json
```

### List All Buckets
```bash
aws s3api list-buckets --output json
```

### Upload File
```bash
# Single object
aws s3api put-object --bucket my-bucket --key path/to/file.txt --body local-file.txt --output json

# High-level command (auto multipart for large files)
aws s3 cp local-file.txt s3://my-bucket/path/to/file.txt --region us-east-1
```

### Download File
```bash
aws s3api get-object --bucket my-bucket --key path/to/file.txt downloaded.txt --output json

# High-level command
aws s3 cp s3://my-bucket/path/to/file.txt downloaded.txt --region us-east-1
```

### List Objects in Bucket
```bash
aws s3api list-objects-v2 --bucket my-bucket --output json

# With prefix filter
aws s3api list-objects-v2 --bucket my-bucket --prefix logs/ --output json

# High-level command
aws s3 ls s3://my-bucket --recursive
```

### Delete Bucket (with contents)
```bash
# Empty bucket first
aws s3 rm s3://my-bucket --recursive --region us-east-1

# Delete empty bucket
aws s3api delete-bucket --bucket my-bucket --region us-east-1 --output json
```

### Set Bucket Policy
```bash
aws s3api put-bucket-policy --bucket my-bucket --policy file://policy.json --output json
```

### Enable Versioning
```bash
aws s3api put-bucket-versioning \
  --bucket my-bucket \
  --versioning-configuration Status=Enabled \
  --output json
```

## Multipart Upload (Large Files)

For files >100MB, use high-level `aws s3 cp` which handles multipart automatically:

```bash
aws s3 cp large-file.zip s3://my-bucket/large-file.zip --region us-east-1
```

Manual multipart (rare):
```bash
# Create multipart upload
aws s3api create-multipart-upload --bucket my-bucket --key large-file --output json

# Upload parts (capture UploadId from previous step)
aws s3api upload-part --bucket my-bucket --key large-file --part-number 1 --body chunk1.bin --upload-id UPLOAD_ID

# Complete multipart upload
aws s3api complete-multipart-upload --bucket my-bucket --key large-file --upload-id UPLOAD_ID --multipart-upload file://parts.json --output json
```

## Credential Handling

CLI reads credentials in priority order:
1. Environment: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
2. Config file: `~/.aws/credentials`
3. IAM role

Verify:
```bash
aws sts get-caller-identity --output json
```