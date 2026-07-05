# DynamoDB Size Limit Errors — Detailed Recovery

## ItemCollectionSizeLimitExceededException

LSI collection exceeds 10GB. Options:

- Reduce item size
- Split large items
- Use GSI instead of LSI
- Redesign partition key distribution

## 400KB Item Limit

### 1. Compress Attributes

```python
import gzip, base64
compressed = base64.b64encode(gzip.compress(data.encode())).decode()
# Store compressed in Binary (B) type
```

### 2. Split into Multiple Items

```python
# Item1: metadata + part1
# Item2: part2
# Item3: part3
```

### 3. Store Large Data in S3

```python
item = {
    'id': {'S': item_id},
    'metadata': {'S': json.dumps(metadata)},
    's3_path': {'S': f's3://bucket/{item_id}/data'}
}
```