# AWS CLI Usage — S3

## Command Map

| Goal | CLI Command | JSON Output Path |
|------|-------------|------------------|
| Create bucket | `aws s3api create-bucket` | `.Location` |
| Delete bucket | `aws s3api delete-bucket` | Empty response |
| List buckets | `aws s3api list-buckets` | `.Buckets[]` |
| Head bucket (check exists) | `aws s3api head-bucket` | Empty (204) |
| Put object | `aws s3api put-object` | `.ETag` |
| Get object | `aws s3api get-object` | `.ETag` (file written to local) |
| List objects | `aws s3api list-objects-v2` | `.Contents[]` |
| Delete object | `aws s3api delete-object` | Empty response |
| Copy object | `aws s3api copy-object` | `.CopyObjectResult.ETag` |
| Head object | `aws s3api head-object` | `.ContentLength, .ETag, .LastModified` |

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

## CLI vs API Coverage Gap

| Operation (API) | CLI Available | Notes |
|-----------------|---------------|-------|
| CreateBucket | ✅ | `s3api create-bucket` |
| DeleteBucket | ✅ | `s3api delete-bucket` |
| ListBuckets | ✅ | `s3api list-buckets` |
| PutObject | ✅ | `s3api put-object`, `s3 cp` |
| GetObject | ✅ | `s3api get-object`, `s3 cp` |
| ListObjects | ✅ | `s3api list-objects-v2` |
| DeleteObject | ✅ | `s3api delete-object`, `s3 rm` |
| HeadObject | ✅ | `s3api head-object` |
| PutBucketPolicy | ✅ | `s3api put-bucket-policy` |
| GetBucketPolicy | ✅ | `s3api get-bucket-policy` |
| PutBucketVersioning | ✅ | `s3api put-bucket-versioning` |
| PutBucketEncryption | ✅ | `s3api put-bucket-encryption` |
| PutBucketLifecycleConfiguration | ✅ | `s3api put-bucket-lifecycle-configuration` |

## Credential Handling

CLI reads credentials in priority order:
1. Environment: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
2. Config file: `~/.aws/credentials`
3. IAM role

Verify:
```bash
aws sts get-caller-identity --output json
```