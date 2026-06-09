# Core Concepts — Amazon Athena

## What is Athena

- **Purpose**: Serverless interactive query service for analyzing data in S3 using standard SQL
- **Category**: Analytics
- **Console**: https://console.aws.amazon.com/athena/
- **Docs**: https://docs.aws.amazon.com/athena/

## Primary Resources

| Resource | Description |
|----------|-------------|
| Work Group | Isolation boundary for queries; controls output location, encryption, engine version |
| Named Query | Saved SQL query with name, database, and optional workgroup |
| Data Catalog | Metadata catalog (Glue Data Catalog or Lambda-based) for tables/databases |
| Query Execution | A single SQL query run against Athena; async with polling |
| Prepared Statement | Parameterized SQL template for repeated execution |
| Capacity Reservation | Reserved DPU capacity for consistent performance |

## Architecture

```
SQL Query → Work Group → Query Engine (Presto/Trino)
                              ↓
                    Data Catalog (table metadata)
                              ↓
                    S3 (data scanned)
                              ↓
                    Result → S3 output location
```

## Query Execution Lifecycle

```
QUEUED → RUNNING → SUCCEEDED / FAILED / CANCELLED
```

- `QUEUED`: Waiting for resources
- `RUNNING`: Query actively executing
- `SUCCEEDED`: Results available in S3
- `FAILED`: Query error (check StateChangeReason)
- `CANCELLED`: User-initiated cancellation

## Data Catalog Types

| Type | Connection | Use Case |
|------|-----------|----------|
| GLUE | AWS Glue | Default; managed Hive metastore |
| LAMBDA | Custom Lambda | Custom catalog integration |
| HIVE | EMR Hive Metastore | Existing Hive metastore |

## Quotas

| Quota | Default | Adjustable? |
|-------|---------|-------------|
| Concurrent queries per workgroup | 20 | Yes |
| Query execution time | 30 minutes | Yes |
| Query result size | 1 GB | Yes |
| Data scanned per query | Unlimited (costs $5/TB) | N/A |
| Named queries per workgroup | 100 | Yes |
| Prepared statements per workgroup | 1000 | Yes |
| Workgroups per account | 1000 | Yes |
| Data catalogs per account | 50 | Yes |

## Cost Model

- **Query execution**: $5 per TB scanned
- **Capacity reservations**: Per-DPU-hour pricing
- **Output storage**: Standard S3 pricing
- **Cost optimization**: Use columnar formats (Parquet, ORC), partition data, use WHERE clauses
