# Integration Guide — Athena: S3, IAM & Glue Data Catalog

_Latest update: 2026-06-27_

This document covers how to integrate Athena with its key dependencies:
S3 (query results + data source), IAM (permissions), and Glue Data Catalog
(metadata). Both services are free-tier eligible for basic usage.

---

## 1. S3 Integration

### What S3 Provides

Athena reads data from S3 and writes query results back to S3. Two S3 buckets
are typically involved:

| Bucket Role | Access Needed | Notes |
|-------------|--------------|-------|
| Data source | Read-only (`s3:GetObject`) | Tables backed by Parquet/CSV/JSON in S3 |
| Query results | Read-write | Athena writes `.csv` results per execution |

### IAM Policy for Athena Query Execution

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-data-bucket/*",
        "arn:aws:s3:::my-data-bucket"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-athena-results/*",
        "arn:aws:s3:::my-athena-results"
      ]
    }
  ]
}
```

### Pre-flight S3 Checks

```bash
# Verify data bucket is accessible
aws s3api head-bucket --bucket my-data-bucket

# Verify results bucket exists and is writable
aws s3api head-bucket --bucket my-athena-results

# Check Athena service has permissions (via IAM role attached to Athena)
aws sts get-caller-identity
```

---

## 2. IAM Integration

### Athena Service-Linked Role

Athena requires a service-linked role for cross-account access and
workgroup configuration. Create if missing:

```bash
aws iam create-service-linked-role \
  --aws-service-name athena.amazonaws.com
```

### Workgroup IAM Policies

Workgroups can enforce IAM policies via `Configuration.EncruptionConfiguration`.
Use `aws-iam-ops` for policy management.

### Cross-Account Sharing via RAM

For cross-account Athena access, RAM shares the data source S3 bucket
(or the entire VPC/subnet for VPC-based endpoints). See `aws-ram-ops`.

---

## 3. Glue Data Catalog Integration

### Glue as Default Catalog

Athena uses the AWS Glue Data Catalog as its default metadata store.
Glue databases and tables are shared across Athena, Glue, and Lake Formation.

### Key Glue CLI Commands (via Athena API)

```bash
# List databases in Glue catalog
aws athena list-databases --catalog-name AwsDataCatalog

# List tables in a database
aws athena list-table-metadata \
  --catalog-name AwsDataCatalog \
  --database-name mydb

# Get table schema
aws athena get-table-metadata \
  --catalog-name AwsDataCatalog \
  --database-name mydb \
  --table-name mytable
```

### Glue Partition Management

```bash
# Repair table partitions (loads new partitions from S3)
aws athena start-query-execution \
  --query-string "MSCK REPAIR TABLE mydb.mytable" \
  --query-execution-context Database=mydb \
  --result-configuration OutputLocation=s3://my-athena-results/partition-repair/
```

---

## 4. CloudWatch Integration

### Query Runtime Metrics

Athena publishes metrics to CloudWatch under namespace `AWS/Athena`:

| Metric | Description |
|--------|-------------|
| `EngineExecutionTime` | Query runtime in ms |
| `DataScannedBytes` | Bytes scanned per query |
| `QueryPlanningTime` | Query planning time in ms |
| `QueryQueueTime` | Time spent waiting in queue |
| `ResultReuse` | Whether results were reused |

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Athena \
  --metric-name DataScannedBytes \
  --start-time 2026-06-27T00:00:00Z \
  --end-time 2026-06-27T12:00:00Z \
  --period 3600 \
  --statistics Average,Sum \
  --region us-east-1
```

### Workgroup CloudWatch Metrics

Workgroups can have dedicated metric streams to CloudWatch:

```bash
aws athena get-work-group \
  --work-group my-workgroup \
  --query '.WorkGroup.Configuration.PublishMetricsEnabled'
```

---

## 5. Cost Optimization Integration

### Query Cost via CloudWatch

Athena charges $5 per TB of data scanned. Track via CloudWatch:

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Athena \
  --metric-name DataScannedBytes \
  --start-time 2026-06-01T00:00:00Z \
  --end-time 2026-06-30T23:59:59Z \
  --period 86400 \
  --statistics Sum \
  --region us-east-1 | \
  jq '.Datapoints[].Sum | . / 1099511627776 | . * 5'  # TB × $5
```

### Cost-Saving Patterns

| Pattern | Savings |
|---------|---------|
| Use columnar formats (Parquet/ORC) | 30–90% |
| Partition by date/event-type | 50–95% |
| Compress data (gz, snappy) | 30–60% |
| Use workgroup result reuse | 20–80% on repeated queries |
| Limit with WHERE clauses | Proportional to data filtered |

---

## 6. Troubleshooting Integration

### Athena Query Failures via CloudTrail

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=StartQueryExecution \
  --start-time 2026-06-27T00:00:00Z \
  --region us-east-1
```

### Glue Catalog Errors

```bash
# Check Glue database exists
aws athena list-databases --catalog-name AwsDataCatalog \
  --query 'DatabaseList[?Name==`mydb`]'

# Check Glue table exists
aws athena list-table-metadata \
  --catalog-name AwsDataCatalog \
  --database-name mydb \
  --query 'TableMetadataList[?Name==`mytable`]'
```

### Cross-Service Diagnostic Flow

```
Athena query fails
    ├── StateChangeReason says "AccessDenied"
    │     └── Check IAM policy (aws-iam-ops)
    ├── StateChangeReason says "Table not found"
    │     └── Check Glue database/table (list-databases / list-table-metadata)
    ├── Query stuck QUEUED
    │     └── Check workgroup concurrency (get-work-group)
    ├── High cost on CloudWatch
    │     └── Check DataScannedBytes; suggest Parquet/partitioning
    └── Results not in S3
          └── Check output location; verify bucket permissions
```
