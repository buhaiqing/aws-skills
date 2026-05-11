# AWS RDS Ops Skill

AWS Relational Database Service (RDS) operational skill for AI Agent automation.

## Triggers

**SHOULD activate when:**
- User requests DB instance creation, modification, or deletion
- User asks to create, restore, or manage database snapshots
- User needs read replica setup or management
- User requests parameter group configuration
- User asks about Aurora cluster operations
- User mentions "RDS", "managed database", "MySQL/PostgreSQL on AWS", "Aurora"
- User needs database backup or recovery operations

**SHOULD-NOT activate when:**
- DynamoDB operations (use `aws-dynamodb-ops`)
- ElastiCache operations (use `aws-elasticache-ops`)
- Redshift operations (use `aws-redshift-ops`)
- EC2 self-managed database setup
- DocumentDB operations
- Neptune graph database operations

**Delegation:**
- Security groups → `aws-ec2-ops` (security group creation)
- IAM roles → `aws-iam-ops` (role creation for RDS)
- KMS keys → `aws-kms-ops` (encryption key setup)
- CloudWatch alarms → `aws-cloudwatch-ops` (monitoring setup)
- S3 backup integration → `aws-s3-ops` (S3 import/export)

## Scope

| Operation | Supported | Safety Gate |
|-----------|-----------|-------------|
| Create DB Instance | Yes | None |
| Modify DB Instance | Yes | Parameter validation |
| Delete DB Instance | Yes | **Human confirmation + final snapshot** |
| Create Snapshot | Yes | None |
| Restore from Snapshot | Yes | None |
| Delete Snapshot | Yes | Human confirmation |
| Create Read Replica | Yes | None |
| Promote Read Replica | Yes | None |
| Create Parameter Group | Yes | None |
| Modify Parameter Group | Yes | Static param restart required |
| Delete Parameter Group | Yes | Human confirmation |
| Create Aurora Cluster | Yes | None |
| Add Aurora Instance | Yes | None |
| Delete Aurora Cluster | Yes | **Human confirmation + final snapshot** |

## Variable Convention

| Variable | Source | Example |
|----------|--------|---------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Environment | Never ask user |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Environment | Never ask user |
| `{{env.AWS_DEFAULT_REGION}}` | Environment | us-east-1 |
| `{{user.DBInstanceIdentifier}}` | User input | my-db-prod |
| `{{user.DBEngine}}` | User input | mysql, postgres, aurora |
| `{{user.MasterUsername}}` | User input | admin |
| `{{user.MasterUserPassword}}` | User input | (secure prompt) |
| `{{user.DBInstanceClass}}` | User input | db.t3.micro |

**Never commit real credentials. Always use `{{env.*}}` or `{{user.*}}` placeholders.**

## Execution Flow

### Pre-flight

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

```
3. Confirm region: aws rds describe-db-engine-versions --region {{env.AWS_DEFAULT_REGION}}
4. Check quotas: aws service-quotas get-service-quota --service-code rds --quota-code L-...
5. Validate engine version: aws rds describe-db-engine-versions --engine {{user.DBEngine}}
```

### Execute (Primary: CLI)
```
aws rds create-db-instance \
  --db-instance-identifier {{user.DBInstanceIdentifier}} \
  --db-instance-class {{user.DBInstanceClass}} \
  --engine {{user.DBEngine}} \
  --engine-version {{user.EngineVersion}} \
  --master-username {{user.MasterUsername}} \
  --master-user-password {{user.MasterUserPassword}} \
  --allocated-storage {{user.AllocatedStorage}} \
  --storage-type {{user.StorageType}} \
  --vpc-security-group-ids {{user.SecurityGroupIds}} \
  --output json
```

### Execute (Fallback: boto3)
After 3 CLI failures, switch to SDK:
```python
import boto3
rds = boto3.client('rds', region_name='{{env.AWS_DEFAULT_REGION}}')
response = rds.create_db_instance(
    DBInstanceIdentifier='{{user.DBInstanceIdentifier}}',
    DBInstanceClass='{{user.DBInstanceClass}}',
    Engine='{{user.DBEngine}}',
    # ... parameters
)
```

### Validate
```
1. Poll status: aws rds describe-db-instances --db-instance-identifier {{user.DBInstanceIdentifier}}
2. Wait for terminal state: available (create), deleted (delete)
3. Max wait: 30 minutes for create, 15 minutes for delete
4. Validate endpoint reachable (optional): Connection test via psql/mysql client
```

### Recover
| Error Type | Action |
|------------|---------|
| DBInstanceAlreadyExists | HALT - provide existing instance info |
| InvalidDBInstanceState | HALT - wait or fix state conflict |
| InsufficientStorageCapacity | HALT - suggest smaller storage or different region |
| StorageTypeNotSupported | Retry with gp2/gp3 |
| QuotaExceeded | HALT - request quota increase |
| Throttling (429) | Exponential backoff; max 3 retries |
| 5xx Internal | Retry 3x; then HALT |

## Safety Gates

### Database Deletion (Critical)
```
BEFORE delete-db-instance:
1. Display: "Deleting {{user.DBInstanceIdentifier}} will permanently remove all data"
2. Ask: "Create final snapshot? (recommended)" → collect snapshot name if yes
3. Ask: "Type 'DELETE {{user.DBInstanceIdentifier}}' to confirm"
4. Human must type exact confirmation string
5. Proceed only after confirmation matches
```

### Snapshot Deletion
```
BEFORE delete-db-snapshot:
1. Display: "Snapshot {{user.SnapshotIdentifier}} will be permanently deleted"
2. Ask: "Type 'DELETE SNAPSHOT {{user.SnapshotIdentifier}}' to confirm"
3. Proceed only after confirmation matches
```

### Parameter Group Deletion
```
BEFORE delete-db-parameter-group:
1. Check: No DB instances using this parameter group
2. Ask: "Type 'DELETE PG {{user.ParameterGroupName}}' to confirm"
3. Proceed only after confirmation matches
```

## Output Convention

Always use `--output json` for agent parsing.

Key JSON paths:
- `.DBInstances[0].DBInstanceStatus` - instance state
- `.DBInstances[0].Endpoint.Address` - connection endpoint
- `.DBInstances[0].Endpoint.Port` - connection port
- `.DBInstances[0].DBInstanceArn` - resource ARN
- `.DBSnapshot.DBSnapshotIdentifier` - snapshot ID
- `.DBSnapshot.Status` - snapshot status

## Related Skills

- `aws-ec2-ops` - Security groups, VPC setup
- `aws-iam-ops` - IAM roles for enhanced monitoring, S3 integration
- `aws-kms-ops` - Encryption key management
- `aws-cloudwatch-ops` - Performance Insights, alarms
- `aws-s3-ops` - Database import/export from S3
- `aws-secrets-manager-ops` - Credential management

## Reference Files

- `references/aws-cli-usage.md` - CLI command reference
- `references/boto3-sdk-usage.md` - Python SDK patterns
- `references/core-concepts.md` - RDS architecture, engines, quotas
- `references/troubleshooting.md` - Error codes, recovery procedures
- `assets/example-config.yaml` - Configuration examples