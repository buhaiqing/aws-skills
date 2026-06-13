# manifest.json Schema (v1.0)

Each `export-hcl` output directory's `manifest.json` must conform to this schema.
The schema itself is defined in [`manifest-schema.json`](./manifest-schema.json) using JSON Schema Draft-07.

## Fields

### Required Fields (14)

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | string (const `"1.0"`) | Locked to 1.0 |
| `generator` | string (const `"aws-topo-discovery"`) | Generator identifier |
| `generator_version` | string (semver) | Generator version, e.g. `"1.0.0"` |
| `generated_at` | string (ISO 8601 date-time) | Generation time, UTC, format `YYYY-MM-DDTHH:MM:SSZ` |
| `account_id` | string (minLength 1) | AWS account ID (12-digit string) |
| `region` | string (minLength 1) | Region, e.g. `"us-east-1"` |
| `scope` | string (minLength 1) | Scan scope, `"all"` or `"vpc-xxx"` |
| `provider_version` | string (semver) | AWS Provider lock version, e.g. `"5.50.0"` |
| `resource_count` | integer (>= 0) | Total exported resources |
| `by_type` | object (string -> integer) | Resource count by type, e.g. `{"vpc": 1, "ec2": 12}` |
| `sensitive_masked` | array of string | Masked field paths, e.g. `["rds.master_user_password"]` |
| `unsupported_types` | array of string | Unsupported resource types |
| `import_ids_stable` | boolean | Whether re-export produces stable IDs |
| `execution_time_ms` | integer (>= 0) | Export duration in milliseconds |

### Optional Fields (2)

| Field | Type | Description |
|-------|------|-------------|
| `account_alias` | string | Account alias (human-readable) |
| `role_arn` | string (ARN regex) | Cross-account source role ARN, e.g. `arn:aws:iam::123456789012:role/TopologyReader` |

### Strictness

- `additionalProperties: false` — no extra keys allowed

## Example

```json
{
  "schema_version": "1.0",
  "generator": "aws-topo-discovery",
  "generator_version": "1.0.0",
  "generated_at": "2026-06-13T15:00:00Z",
  "account_id": "123456789012",
  "account_alias": "prod-finance",
  "role_arn": "arn:aws:iam::123456789012:role/TopologyReader",
  "region": "us-east-1",
  "scope": "vpc-xxx",
  "provider_version": "5.50.0",
  "resource_count": 47,
  "by_type": {
    "vpc": 1,
    "subnet": 3,
    "ec2": 12,
    "rds": 2,
    "elb": 2
  },
  "sensitive_masked": [
    "rds.master_user_password"
  ],
  "unsupported_types": [],
  "import_ids_stable": true,
  "execution_time_ms": 12345
}
```

## Validation

```python
import json
from scripts.lib.manifest_validator import ManifestValidator

manifest = json.load(open("infra-baseline/2026-06-13/manifest.json"))
ManifestValidator().validate(manifest)  # raises ManifestValidationError on failure
```

## Version Evolution

- **v1.0** (current): 14 required + 2 optional fields
- Future: any breaking change requires new `schema_version`
