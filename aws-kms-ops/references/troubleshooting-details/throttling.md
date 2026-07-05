# KMS Throttling — Detailed Resolution

## API Throttling

```bash
# Check CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/KMS \
  --metric-name ThrottledRequests \
  --dimensions Name=KeyId,Value={{key_id}} \
  --start-time "2024-01-01T00:00:00Z" --end-time "2024-01-31T23:59:59Z" \
  --period 3600 --statistics Sum
```

**Backoff pattern:**
```python
import time, random
def retry_with_backoff(operation, max_retries=10):
    for attempt in range(max_retries):
        try:
            return operation()
        except ClientError as e:
            if e.response['Error']['Code'] == 'ThrottlingException':
                delay = min(2 ** attempt * 0.1 + random.uniform(0, 0.5), 60)
                time.sleep(delay)
            else:
                raise
    raise Exception("Max retries exceeded")
```

## Rate Limits by Key Type

| Key Type | Rate Limit | Mitigation |
|----------|-----------|------------|
| Symmetric | ~10,000 req/s | Usually sufficient |
| RSA_2048 | ~500 ops/s | Cache decrypted data keys |
| RSA_3072 | ~100 ops/s | Cache decrypted data keys |
| ECC | ~1,000+ ops/s | Cache decrypted data keys |
