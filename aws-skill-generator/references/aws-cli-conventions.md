# AWS CLI Conventions (Empirical Notes)

## Critical Behavioral Notes

### Output Format

**Rule**: Always use `--output json` for agent execution.

```bash
# CORRECT
aws [service] [command] --output json

# WRONG (text output harder to parse)
aws [service] [command] --output text
```

### Pagination Handling

AWS CLI automatically paginates. For large result sets:

```bash
# CLI handles pagination internally
aws [service] list-[resources] --output json

# For explicit control (rare)
aws [service] list-[resources] --starting-token TOKEN --max-items N
```

### Credential Sources (Priority Order)

| Priority | Source | Notes |
|----------|--------|-------|
| 1 | Environment vars | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` |
| 2 | AWS credentials file | `~/.aws/credentials` |
| 3 | IAM role | EC2/Lambda instance role |

**CLI reads credentials in this order automatically.**

### Region Handling

```bash
# Via environment
export AWS_DEFAULT_REGION=us-east-1

# Via command flag
aws [service] [command] --region us-west-2

# Via config file
# ~/.aws/config: region = us-east-1
```

### Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| `--output text` used | Use `--output json` |
| Missing `--region` | Set `AWS_DEFAULT_REGION` or pass flag |
| Paginated results truncated | Use `--no-paginate` for single page OR rely on CLI auto-pagination |
| Timestamp format varies | Parse per AWS API docs; may be Unix epoch or ISO 8601 |

## Retry Strategy

| Error Code | Retry? | Max Retries |
|------------|--------|-------------|
| 400 (InvalidParameter) | No | 0 |
| 403 (AccessDenied) | No | 0 |
| 404 (NotFound) | No | 0 |
| 429 (Throttling) | Yes | 3 with exponential backoff |
| 500 (InternalError) | Yes | 3 with exponential backoff |
| 503 (ServiceUnavailable) | Yes | 3 with exponential backoff |

## JSON Path Examples (Per Service)

Replace these examples with verified paths from actual AWS CLI runs:

```json
// EC2 describe-instances
{
  "Reservations": [
    {
      "Instances": [
        {
          "InstanceId": "i-12345",
          "State": { "Name": "running" }
        }
      ]
    }
  ]
}
// JSON path: .Reservations[0].Instances[0].InstanceId

// S3 list-buckets
{
  "Buckets": [
    { "Name": "my-bucket", "CreationDate": "2026-05-10T10:00:00Z" }
  ]
}
// JSON path: .Buckets[0].Name
```

## Idempotency

AWS CLI commands are generally idempotent for:
- Describe/List operations
- Delete operations (404 on second attempt)

For Create operations:
- Use unique names/IDs
- Some services support idempotency tokens (e.g., EC2 `--client-token`)