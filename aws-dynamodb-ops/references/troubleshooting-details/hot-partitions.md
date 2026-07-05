# DynamoDB Hot Partitions — Detailed Recovery

## Diagnosis

Enable Contributor Insights:

```bash
aws dynamodb update-contributor-insights \
  --table-name {{table_name}} \
  --contributor-insights-action ENABLE

aws dynamodb describe-contributor-insights \
  --table-name {{table_name}}
```

## Resolution Strategies

### 1. Write Sharding

```python
def get_shard_key(timestamp: str, num_shards: int = 10) -> str:
    shard = hash(timestamp) % num_shards
    return f"{timestamp}#{shard}"
```

### 2. Random Suffix

```python
import uuid
def distribute_writes(key: str) -> str:
    return f"{key}#{uuid.uuid4().hex[:4]}"
```

### 3. High-Cardinality Composite Keys

```python
key = f"{user_id}#{timestamp}#{uuid.uuid4().hex}"
```