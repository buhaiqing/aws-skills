# Troubleshooting — Amazon Athena

## Common API Error Codes

| Error | HTTP | Meaning | Agent Action |
|-------|------|---------|--------------|
| InvalidParameterValue | 400 | Invalid parameter | Fix args per API docs |
| ResourceNotFoundException | 404 | Resource not found | Verify resource name/ID |
| ThrottlingException | 429 | Rate limit | Backoff; retry 3x |
| InternalServerException | 500 | AWS service error | Retry 3x; HALT |
| SessionAlreadyExistsException | 409 | Notebook session active | End session first |
| IdempotentInvokeException | 409 | Duplicate request | Retry 1x |

## Diagnostic Order

1. **Check workgroup**: `aws athena get-work-group --work-group <name>`
2. **Check query status**: `aws athena get-query-execution --query-execution-id <id>`
3. **Check data catalog**: `aws athena get-data-catalog --name <name>`
4. **Check databases**: `aws athena list-databases --catalog-name <catalog>`
5. **Check table metadata**: `aws athena list-table-metadata --catalog-name <catalog> --database-name <db>`
6. **Check CloudTrail**: `aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=StartQueryExecution`

## Common Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Query stuck QUEUED | Concurrency limit | Wait or increase workgroup limit |
| Query FAILED | SQL syntax error | Check StateChangeReason; fix SQL |
| No results returned | Wrong database | Verify QueryExecutionContext.Database |
| Access denied | IAM permissions | Check workgroup IAM policy |
| Data scanned is huge | Missing partitions | Add WHERE clause on partition columns |
| Workgroup not found | Wrong name/region | `list-work-groups` to verify |
| Catalog not found | Wrong catalog name | `list-data-catalogs` to verify |
| Throttling on list | Too many requests | Add exponential backoff |

## Query Performance Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Slow query | Large data scan | Use columnar format (Parquet/ORC); add partitions |
| High cost | Scanning too much data | Use LIMIT; filter on partition columns |
| Query timeout | Execution > 30 min | Break into smaller queries; optimize joins |
| Memory limit exceeded | Query too complex | Simplify; use CTAS for intermediate results |

## Capacity Reservation Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Reservation not available | Insufficient DPU | Check region availability |
| Reservation not used | No matching workgroup | Associate workgroup with reservation |
