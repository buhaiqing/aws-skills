# boto3 SDK Usage — S3

## Client Initialization

```python
import boto3
import os

client = boto3.client(
    's3',
    region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
)
```

## Operation Patterns

### Create Bucket

```python
response = client.create_bucket(
    Bucket='my-bucket',
    # For regions other than us-east-1
    CreateBucketConfiguration={'LocationConstraint': 'us-west-2'}
)
print(f"Created: {response['Location']}")
```

### List Buckets

```python
response = client.list_buckets()
for bucket in response['Buckets']:
    print(f"{bucket['Name']} - {bucket['CreationDate']}")
```

### Put Object (Upload)

```python
# Simple upload
with open('local-file.txt', 'rb') as f:
    response = client.put_object(
        Bucket='my-bucket',
        Key='path/to/file.txt',
        Body=f
    )
    print(f"ETag: {response['ETag']}")

# Upload with metadata
response = client.put_object(
    Bucket='my-bucket',
    Key='uploads/data.json',
    Body=json_data_bytes,
    ContentType='application/json',
    Metadata={'project': 'myapp', 'version': '1.0'}
)
```

### Get Object (Download)

```python
response = client.get_object(
    Bucket='my-bucket',
    Key='path/to/file.txt'
)
content = response['Body'].read()
print(f"Size: {response['ContentLength']}")
print(f"ETag: {response['ETag']}")

# Save to file
with open('downloaded.txt', 'wb') as f:
    f.write(response['Body'].read())
```

### Head Object (Check exists/metadata)

```python
response = client.head_object(
    Bucket='my-bucket',
    Key='path/to/file.txt'
)
print(f"Size: {response['ContentLength']}")
print(f"LastModified: {response['LastModified']}")
```

### List Objects

```python
# List all objects
response = client.list_objects_v2(Bucket='my-bucket')
for obj in response.get('Contents', []):
    print(f"{obj['Key']} - {obj['Size']} bytes")

# With prefix
response = client.list_objects_v2(
    Bucket='my-bucket',
    Prefix='logs/'
)

# Pagination
paginator = client.get_paginator('list_objects_v2')
for page in paginator.paginate(Bucket='my-bucket', Prefix='logs/'):
    for obj in page.get('Contents', []):
        print(f"{obj['Key']}")
```

### Delete Object

```python
response = client.delete_object(
    Bucket='my-bucket',
    Key='path/to/file.txt'
)

# Delete multiple objects
response = client.delete_objects(
    Bucket='my-bucket',
    Delete={
        'Objects': [
            {'Key': 'file1.txt'},
            {'Key': 'file2.txt'}
        ]
    }
)
```

### Delete Bucket (Must be empty)

```python
# Empty bucket first
paginator = client.get_paginator('list_objects_v2')
for page in paginator.paginate(Bucket='my-bucket'):
    if 'Contents' in page:
        objects = [{'Key': obj['Key']} for obj in page['Contents']]
        client.delete_objects(Bucket='my-bucket', Delete={'Objects': objects})

# Delete bucket
client.delete_bucket(Bucket='my-bucket')
```

### Copy Object

```python
response = client.copy_object(
    Bucket='dest-bucket',
    Key='dest-key',
    CopySource={'Bucket': 'src-bucket', 'Key': 'src-key'}
)
print(f"Copied: {response['CopyObjectResult']['ETag']}")
```

### Multipart Upload (Large Files)

```python
import os

# Create multipart upload
mpu = client.create_multipart_upload(Bucket='my-bucket', Key='large-file')
upload_id = mpu['UploadId']

# Upload parts
parts = []
chunk_size = 10 * 1024 * 1024  # 10MB
with open('large-file.bin', 'rb') as f:
    part_number = 1
    while True:
        data = f.read(chunk_size)
        if not data:
            break
        up = client.upload_part(
            Bucket='my-bucket',
            Key='large-file',
            PartNumber=part_number,
            UploadId=upload_id,
            Body=data
        )
        parts.append({'PartNumber': part_number, 'ETag': up['ETag']})
        part_number += 1

# Complete multipart upload
client.complete_multipart_upload(
    Bucket='my-bucket',
    Key='large-file',
    UploadId=upload_id,
    MultipartUpload={'Parts': parts}
)
```

## Error Handling

```python
from botocore.exceptions import ClientError

try:
    response = client.create_bucket(Bucket='my-bucket')
except ClientError as e:
    code = e.response['Error']['Code']
    
    if code == 'BucketAlreadyExists':
        print("Bucket name taken (S3 is global namespace)")
    elif code == 'InvalidBucketName':
        print("Invalid bucket name format")
    elif code == 'AccessDenied':
        print("No permission to create bucket")
    else:
        raise
```

## Common Error Codes

| Error Code | HTTP | Action |
|------------|------|--------|
| BucketAlreadyExists | 409 | Use different name |
| InvalidBucketName | 400 | Fix naming rules |
| NoSuchBucket | 404 | Bucket doesn't exist |
| NoSuchKey | 404 | Object doesn't exist |
| AccessDenied | 403 | Check permissions |
| EntityTooLarge | 400 | Use multipart upload |
| ThrottlingException | 429 | Backoff and retry |

## Resource Pattern (High-level)

```python
# Resource interface (simpler for common operations)
s3 = boto3.resource('s3')

# Upload
s3.Object('my-bucket', 'key').put(Body=open('file.txt', 'rb'))

# Download
s3.Object('my-bucket', 'key').download_file('local.txt')

# List bucket objects
bucket = s3.Bucket('my-bucket')
for obj in bucket.objects.all():
    print(obj.key)
```

## Pre-signed URLs

```python
# Generate upload URL
url = client.generate_presigned_url(
    'put_object',
    Params={'Bucket': 'my-bucket', 'Key': 'upload-key'},
    ExpiresIn=3600
)

# Generate download URL
url = client.generate_presigned_url(
    'get_object',
    Params={'Bucket': 'my-bucket', 'Key': 'download-key'},
    ExpiresIn=3600
)
```