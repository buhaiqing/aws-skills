# AWS ECR — CLI Usage

## Common Flags
```bash
--region "{{user.region}}"
--output json
```

## Repository Operations

### Create Repository
```bash
aws ecr create-repository \
  --repository-name "{{user.repository_name}}" \
  --image-scanning-configuration scanOnPush=true \
  --encryption-type AES256 \
  --region "{{user.region}}" --output json
```

### List Repositories
```bash
aws ecr describe-repositories --region "{{user.region}}" --output json
```
JSON Path (file top): `.repositories[].{name: repositoryName, uri: repositoryUri}`

### Describe Repository
```bash
aws ecr describe-repositories \
  --repository-names "{{user.repository_name}}" \
  --region "{{user.region}}" --output json
```
JSON Path: `.repositories[0].repositoryUri`

### Delete Repository
> Destructive. Confirm with user first. Use `--force` to delete non-empty repos.
```bash
aws ecr delete-repository \
  --repository-name "{{user.repository_name}}" \
  --region "{{user.region}}" --output json
```
Force (images present):
```bash
aws ecr delete-repository \
  --repository-name "{{user.repository_name}}" \
  --force \
  --region "{{user.region}}" --output json
```

## Image Operations

### List Images
```bash
aws ecr list-images \
  --repository-name "{{user.repository_name}}" \
  --region "{{user.region}}" --output json
```
JSON Path: `.imageIds[].{digest: imageDigest, tag: imageTag}`

### Describe Images
```bash
aws ecr describe-images \
  --repository-name "{{user.repository_name}}" \
  --region "{{user.region}}" --output json
```
JSON Path: `.imageDetails[].{digest: imageDigest, size: imageSizeInBytes, pushedAt: imagePushedAt}`

### Batch Delete Images
> Destructive. Confirm with user.
```bash
aws ecr batch-delete-image \
  --repository-name "{{user.repository_name}}" \
  --image-ids imageTag=v1.0.0 imageTag=v0.9.0 \
  --region "{{user.region}}" --output json
```

### Batch Get Image
```bash
aws ecr batch-get-image \
  --repository-name "{{user.repository_name}}" \
  --image-ids imageDigest=sha256:... \
  --region "{{user.region}}" --output json
```

## Policy Operations

### Put Lifecycle Policy
```bash
aws ecr put-lifecycle-policy \
  --repository-name "{{user.repository_name}}" \
  --lifecycle-policy-text file://policy.json \
  --region "{{user.region}}" --output json
```

### Get Lifecycle Policy
```bash
aws ecr get-lifecycle-policy \
  --repository-name "{{user.repository_name}}" \
  --region "{{user.region}}" --output json
```

### Delete Lifecycle Policy
```bash
aws ecr delete-lifecycle-policy \
  --repository-name "{{user.repository_name}}" \
  --region "{{user.region}}" --output json
```

### Set Repository Policy
> Warn on cross-account or public access.
```bash
aws ecr set-repository-policy \
  --repository-name "{{user.repository_name}}" \
  --policy-text file://policy.json \
  --region "{{user.region}}" --output json
```

### Get Repository Policy
```bash
aws ecr get-repository-policy \
  --repository-name "{{user.repository_name}}" \
  --region "{{user.region}}" --output json
```

## Image Scanning

### Start Image Scan
```bash
aws ecr start-image-scan \
  --repository-name "{{user.repository_name}}" \
  --image-id imageTag=latest \
  --region "{{user.region}}" --output json
```

### Describe Image Scan Findings
```bash
aws ecr describe-image-scan-findings \
  --repository-name "{{user.repository_name}}" \
  --image-id imageTag=latest \
  --region "{{user.region}}" --output json
```

## Auth / Login

### Get Login Password (for Docker CLI)
```bash
aws ecr get-login-password --region "{{user.region}}" | \
  docker login --username AWS --password-stdin \
  {{output.registry_id}}.dkr.ecr.{{user.region}}.amazonaws.com
```
