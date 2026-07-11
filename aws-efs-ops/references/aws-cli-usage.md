# AWS EFS — CLI Usage

## Common Flags
```bash
--region "{{user.region}}"
--output json
```

## File System Operations

### Create File System
```bash
aws efs create-file-system \
  --creation-token "{{user.file_system_token}}" \
  --performance-mode generalPurpose \
  --throughput-mode bursting \
  --encrypted \
  --region "{{user.region}}" --output json
```
Custom KMS key:
```bash
aws efs create-file-system \
  --creation-token "{{user.file_system_token}}" \
  --encrypted \
  --kms-key-id "arn:aws:kms:{{user.region}}:{{user.account_id}}:key/xxx" \
  --region "{{user.region}}" --output json
```

### List File Systems
```bash
aws efs describe-file-systems --region "{{user.region}}" --output json
```
JSON Path: `.FileSystems[].{id: FileSystemId, state: LifeCycleState, size: SizeInBytes.Value}`

### Describe File System
```bash
aws efs describe-file-systems \
  --file-system-id "{{user.file_system_id}}" \
  --region "{{user.region}}" --output json
```

### Delete File System
> Destructive. Confirm with user first. Must delete mount targets & access points first.
```bash
aws efs delete-file-system \
  --file-system-id "{{user.file_system_id}}" \
  --region "{{user.region}}" --output json
```

## Mount Target Operations

### Create Mount Target
```bash
aws efs create-mount-target \
  --file-system-id "{{user.file_system_id}}" \
  --subnet-id "{{user.subnet_id}}" \
  --security-groups "{{user.security_group_id}}" \
  --region "{{user.region}}" --output json
```
JSON Path: `.MountTargetId`

### List Mount Targets
```bash
aws efs describe-mount-targets \
  --file-system-id "{{user.file_system_id}}" \
  --region "{{user.region}}" --output json
```

### Describe Mount Target
```bash
aws efs describe-mount-target-security-groups \
  --mount-target-id "{{user.mount_target_id}}" \
  --region "{{user.region}}" --output json
```

### Delete Mount Target
> Destructive. Confirm with user.
```bash
aws efs delete-mount-target \
  --mount-target-id "{{user.mount_target_id}}" \
  --region "{{user.region}}" --output json
```

## Access Point Operations

### Create Access Point
```bash
aws efs create-access-point \
  --file-system-id "{{user.file_system_id}}" \
  --posix-user Uid=1000,Gid=1000 \
  --root-directory Path="/data",CreationInfo='{OwnerUid=1000,OwnerGid=1000,Permissions=0755}' \
  --region "{{user.region}}" --output json
```
JSON Path: `.AccessPointId`

### List Access Points
```bash
aws efs describe-access-points \
  --file-system-id "{{user.file_system_id}}" \
  --region "{{user.region}}" --output json
```

### Delete Access Point
> Destructive. Confirm with user.
```bash
aws efs delete-access-point \
  --access-point-id "{{user.access_point_id}}" \
  --region "{{user.region}}" --output json
```

## Tag Operations

### Tag Resource
```bash
aws efs tag-resource \
  --resource-id "{{user.file_system_id}}" \
  --tags Key=Name,Value=my-filesystem \
  --region "{{user.region}}" --output json
```

### List Tags
```bash
aws efs list-tags-for-resource \
  --resource-id "{{user.file_system_id}}" \
  --region "{{user.region}}" --output json
```

## Lifecycle Policy

### Put Lifecycle Policy
```bash
aws efs put-lifecycle-configuration \
  --file-system-id "{{user.file_system_id}}" \
  --lifecycle-policies '[{"TransitionToIA": "AFTER_30_DAYS"}]' \
  --region "{{user.region}}" --output json
```
