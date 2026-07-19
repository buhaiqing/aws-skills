# Well-Architected Assessment

This skill's operations are evaluated against AWS [Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/).

## Security

| Area | Guidance |
| **IAM** | Require: `ReadOnlyAccess` policy only. Principle: least privilege, read-only access |
| **Credentials** | `{{env.*}}` only. All AK/Secret values in output must be masked (e.g., `AKIA***`) |
| **Data Sensitivity** | VPC IDs, instance IDs, and IP ranges are sensitive infrastructure data. Restrict report distribution |

## Reliability

| Area | Guidance |
| **Failure Isolation** | Skip individual VPCs on error but continue scanning. Partial results are still valuable |
| **Change Tracking** | Regular topology discovery enables change tracking and drift detection |
| **Disaster Recovery** | N/A (read-only skill). Use reports as baseline for post-incident infrastructure comparison |

## Cost Optimization

This skill uses read-only Describe APIs which are free. Minimal API call volume:
- **Optimization:** Use batch APIs where possible. Use `--max-items` for pagination
- **Waste:** N/A for read-only discovery

## Operational Excellence

- **Parallel Collection:** EC2/RDS/ELB/VPC APIs can be queried simultaneously
- **CI/CD Integration:** Run in CI pipeline for regular topology drift detection
- **JSON Output:** Compatible with jq for automated analysis

## Performance

| Operation | Expected API Calls | Time Estimate |
| Full scan (all VPCs, multi-region) | ~10-20 Describe calls | < 30s |
| Brief mode | ~5 Describe calls | < 10s |
| + Health overlay | +0 (reuses existing data) | +0s |
| + CF origin config (detailed/overlay) | +N `get-distribution-config` (parallel, cap 5) | +5–30s |
| + HCL export | ~10-30 API calls | < 60s |
