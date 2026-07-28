# AWS IAM — Operations Detail
> Sourced from `aws-iam-ops/SKILL.md` §Operation: <name>.
> This file holds per-operation Pre-flight → Execute → Validate → Recover.
> SKILL.md keeps an `## Operations Index` table that links here.

## Common Pre-flight

Every IAM op: Pre-flight (`aws --version && aws sts get-caller-identity`) → Execute (CLI primary, boto3 fallback after 3 failures) → Validate → Recover.

```
[SKILL] Loading AWS credentials...
[OK]   AWS_DEFAULT_REGION={{env.AWS_DEFAULT_REGION}} (from .env)
[OK]   AWS_ACCESS_KEY_ID=**** (from .env, masked)
[OK]   Credential verification passed
[OK]   Identity: arn:aws:iam::{{env.AWS_ACCOUNT_ID}}:user/xxx
```

| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `aws --version` | Install AWS CLI v2 |
| Credentials | `aws sts get-caller-identity` | HALT; see `references/integration.md` → Error Messages |
| User/Role/Policy name valid | Check naming rules | Suggest valid name |
| Path valid (optional) | Verify path format | Use default `/` |

## IAM Operations (read-write)

### Operation: Create User

#### Pre-flight

**Step 1: Check CLI**
```bash
aws --version
```
Log: `[OK] AWS CLI v2.x.x detected` or `[FAIL] AWS CLI not found. Install: uv pip install awscli`

**Step 2: Load & Verify Credentials**
```bash
aws sts get-caller-identity --output json
```

Log format:
```
[SKILL] Loading AWS credentials...
[OK]   AWS_DEFAULT_REGION={{env.AWS_DEFAULT_REGION}} (from .env)
[OK]   AWS_ACCESS_KEY_ID=**** (from .env, masked)
[OK]   Credential verification passed
[OK]   Identity: arn:aws:iam::{{env.AWS_ACCOUNT_ID}}:user/xxx
```

On failure:
```
[FAIL] AWS credential verification failed.
AWS Error: <exact error message>
Action: See references/integration.md → Error Messages for diagnosis.
```

| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `aws --version` | Install AWS CLI v2 |
| Credentials | `aws sts get-caller-identity` | HALT; log precise error; guide user to integration.md |
| User name valid | Check naming rules | Suggest valid name |
| Path valid (optional) | Verify path format | Use default `/` |

#### Execute — CLI (Primary)
```bash
aws iam create-user \
  --user-name "{{user.user_name}}" \
  --path "{{user.path}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
import boto3
client = boto3.client('iam')
response = client.create_user(
    UserName='{{user.user_name}}',
    Path='{{user.path}}'
)
```

#### Validate
```bash
aws iam get-user --user-name "{{user.user_name}}" --output json
```

#### Recover
| Error | Action |
|-------|--------|
| EntityAlreadyExists | HALT; user already exists |
| InvalidInput | Fix name/path; retry once |
| Throttling (429) | Backoff, retry 3x |

### Operation: Create Role

#### Pre-flight
- Trust policy JSON must be provided
- Verify trust policy structure (Principal, Action, Condition)

#### Execute — CLI
```bash
aws iam create-role \
  --role-name "{{user.role_name}}" \
  --assume-role-policy-document file://trust-policy.json \
  --output json
```

#### Validate
```bash
aws iam get-role --role-name "{{user.role_name}}" --output json
```

### Operation: Attach Policy to Role

#### Execute — CLI
```bash
aws iam attach-role-policy \
  --role-name "{{user.role_name}}" \
  --policy-arn "{{user.policy_arn}}" \
  --output json
```

### Operation: Create Access Key (Sensitive)

**Safety Gate**: MUST warn user about credential handling.
> "Access Key will be generated. Store credentials securely—do NOT commit to code."

#### Execute — CLI
```bash
aws iam create-access-key --user-name "{{user.user_name}}" --output json
```

#### Present to User
| Field | JSON Path | Notes |
|-------|-----------|-------|
| AccessKeyId | `.AccessKey.AccessKeyId` | Public identifier |
| SecretAccessKey | `.AccessKey.SecretAccessKey` | **SHOW ONCE only; user must save immediately** |
| Status | `.AccessKey.Status` | Active/Inactive |

### Operation: Delete User (Destructive)

**Safety Gate**: MUST obtain explicit confirmation.
> "Delete user {{user.user_name}} and all associated access keys, policies? IRREVERSIBLE."

#### Pre-flight
- List attached policies
- List access keys
- List group memberships

#### Execute — CLI
```bash
# Detach policies first
aws iam list-attached-user-policies --user-name "{{user.user_name}}" --output json | jq -r '.AttachedPolicies[].PolicyArn' | xargs -I {} aws iam detach-user-policy --user-name "{{user.user_name}}" --policy-arn {}

# Delete access keys
aws iam list-access-keys --user-name "{{user.user_name}}" --output json | jq -r '.AccessKeyMetadata[].AccessKeyId' | xargs -I {} aws iam delete-access-key --user-name "{{user.user_name}}" --access-key-id {}

# Remove from groups
aws iam list-groups-for-user --user-name "{{user.user_name}}" --output json | jq -r '.Groups[].GroupName' | xargs -I {} aws iam remove-user-from-group --user-name "{{user.user_name}}" --group-name {}

# Delete user
aws iam delete-user --user-name "{{user.user_name}}" --output json
```

### Operation: List Users

#### Execute — CLI
```bash
aws iam list-users --output json
```

### Operation: Get Credential Report

**Use case**: Audit all IAM users for access key age and MFA status (RB-SEC-18 S6: root account credential audit).

#### Execute — CLI
```bash
# Step 1: generate (if not already cached — cached for ~4h)
aws iam generate-credential-report --output json
# Step 2: retrieve
aws iam get-credential-report --output json | jq -r '.Content' | base64 -d | head -5
```

#### Execute — boto3 (Fallback)
```python
client.generate_credential_report()
resp = client.get_credential_report()
import csv, io
reader = csv.DictReader(io.StringIO(resp['Content'].decode()))
for row in reader:
    print(f"{row['user']}: key_last_used={row.get('access_key_1_last_used', 'N/A')}")
```

#### Validate
Confirm report is `COMPLETE` state before parsing.

#### Recover
| Error | Action |
|-------|--------|
| ReportNotComplete | Retry after 5s (report generation takes ~10s) |
| AccessDenied | Requires iam:GetCredentialReport permission |
