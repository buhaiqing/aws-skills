# AWS CLI Usage — Amazon Athena

## Common JSON Paths (Centralized)

```
# WorkGroup:      .WorkGroup.{Name,Configuration.ResultConfiguration.OutputLocation,State,Description}
# NamedQuery:     .NamedQuery.{NamedQueryId,Name,Database,QueryString,Description,WorkGroup}
# DataCatalog:    .DataCatalog.{Name,Type,ConnectionType,Status,Error}
# QueryExec:      .QueryExecution.{QueryExecutionId,Query,StatementType,State,StateChangeReason,Statistics.EngineExecutionTimeInMillis,Statistics.DataScannedBytes,ResultConfiguration.OutputLocation}
# QueryResults:   .ResultSet.{Rows[{Data[{VarCharValue}]}],ResultSetMetadata.ColumnInfo[{Name,Type}]}
# PreparedStmt:   .PreparedStatement.{PreparedStatementName,QueryStatement,WorkGroupName,Description}
```

## Command Map

| Goal | CLI Command |
|------|-------------|
| Create workgroup | `aws athena create-work-group` |
| List workgroups | `aws athena list-work-groups` |
| Get workgroup | `aws athena get-work-group` |
| Update workgroup | `aws athena update-work-group` |
| Delete workgroup | `aws athena delete-work-group` |
| Create named query | `aws athena create-named-query` |
| List named queries | `aws athena list-named-queries` |
| Get named query | `aws athena get-named-query` |
| Update named query | `aws athena update-named-query` |
| Delete named query | `aws athena delete-named-query` |
| Start query execution | `aws athena start-query-execution` |
| Stop query execution | `aws athena stop-query-execution` |
| Get query execution | `aws athena get-query-execution` |
| Get query results | `aws athena get-query-results` |
| List query executions | `aws athena list-query-executions` |
| Get query runtime stats | `aws athena get-query-runtime-statistics` |
| Create data catalog | `aws athena create-data-catalog` |
| List data catalogs | `aws athena list-data-catalogs` |
| Get data catalog | `aws athena get-data-catalog` |
| Update data catalog | `aws athena update-data-catalog` |
| Delete data catalog | `aws athena delete-data-catalog` |
| List databases | `aws athena list-databases` |
| Get database | `aws athena get-database` |
| List table metadata | `aws athena list-table-metadata` |
| Get table metadata | `aws athena get-table-metadata` |
| Create prepared statement | `aws athena create-prepared-statement` |
| List prepared statements | `aws athena list-prepared-statements` |
| Get prepared statement | `aws athena get-prepared-statement` |
| Update prepared statement | `aws athena update-prepared-statement` |
| Delete prepared statement | `aws athena delete-prepared-statement` |
| Tag resource | `aws athena tag-resource` |
| Untag resource | `aws athena untag-resource` |
| List tags | `aws athena list-tags-for-resource` |

## Common Patterns

### Create Workgroup with Output Location
```bash
aws athena create-work-group \
  --name "analytics-wg" \
  --description "Analytics workgroup" \
  --configuration "ResultConfiguration={OutputLocation=s3://my-query-results/athena/}" \
  --region us-east-1 \
  --output json
```

### Start Query and Poll for Results
```bash
# Start
EXEC_ID=$(aws athena start-query-execution \
  --query-string "SELECT count(*) FROM my_table" \
  --query-execution-context "Database=mydb" \
  --result-configuration "OutputLocation=s3://my-query-results/athena/" \
  --work-group "analytics-wg" \
  --region us-east-1 \
  --output json | jq -r '.QueryExecutionId')

# Poll until complete
aws athena get-query-execution \
  --query-execution-id "$EXEC_ID" \
  --region us-east-1 \
  --output json | jq '.QueryExecution.State'

# Get results
aws athena get-query-results \
  --query-execution-id "$EXEC_ID" \
  --region us-east-1 \
  --output json
```

### List All Non-Running Queries in Workgroup
```bash
aws athena list-query-executions \
  --work-group "analytics-wg" \
  --region us-east-1 \
  --output json
```

### List Databases in Catalog
```bash
aws athena list-databases \
  --catalog-name "mydatacatalog" \
  --region us-east-1 \
  --output json
```

## Retry Strategy

| Error Code | Retry? | Max Retries |
|------------|--------|-------------|
| InvalidParameterValue | No | 0 |
| AccessDenied | No | 0 |
| ResourceNotFoundException | No | 0 |
| ThrottlingException | Yes | 3 with exponential backoff |
| InternalServerException | Yes | 3 with backoff |
| IdempotentInvokeException | Yes | 1 |
| SessionAlreadyExistsException | No | HALT — end existing session first |
