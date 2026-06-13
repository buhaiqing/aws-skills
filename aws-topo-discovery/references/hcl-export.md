# HCL Export Engine Design

This document describes the architecture of the HCL export engine
used by `export-hcl.py` and consumed by `baseline-manager.py`.

## Architecture

```
+-----------------------------------------------------------+
|  CLI Layer:                                               |
|    export-hcl.py (orchestrator)                           |
|    baseline-manager.py (wraps export-hcl + baseline store)|
+---------------------+-------------------------------------+
                      |
                      v
+-----------------------------------------------------------+
|  Library Layer (scripts/lib/):                            |
|    manifest_validator  - schema compliance                |
|    manifest_builder    - dict construction                |
|    sensitive_masker    - password/key masking             |
|    provider_locker     - AWS Provider version             |
|    field_mapper        - JSON -> HCL conversion           |
|    dependency_inference - topological sort                |
|    baseline_local      - local storage backend            |
+---------------------+-------------------------------------+
                      |
                      v
+-----------------------------------------------------------+
|  Data Layer:                                              |
|    MAPPINGS registry (scripts/lib/mappings.py)            |
|    fixtures/*.json (test data)                            |
|    references/field-mappings/*.md (mapping specs)         |
+-----------------------------------------------------------+
```

## Resource Type Coverage (12 types)

| Type | terraform_type | Phase |
|------|---------------|-------|
| vpc | aws_vpc | 1 |
| subnet | aws_subnet | 1 |
| ec2 | aws_instance | 1 |
| rds | aws_db_instance | 1 |
| elb | aws_lb | 1 |
| nat | aws_nat_gateway | 2 |
| eip | aws_eip | 2 |
| sg | aws_security_group | 2 |
| eks | aws_eks_cluster | 2 |
| lambda | aws_lambda_function | 2 |
| s3 | aws_s3_bucket | 2 |
| iam | aws_iam_role | 2 |

## Output File Schema

For each export, 8 files are written atomically:

| File | Content |
|------|---------|
| `provider.tf` | `terraform{}` and `provider "aws" {}` blocks |
| `main.tf` | All resource blocks, topologically ordered |
| `variables.tf` | Variable declarations (e.g. db_password) |
| `outputs.tf` | Important resource ID outputs |
| `terraform.tfstate` | Import helper state (empty) |
| `import.sh` | One `terraform import` per resource |
| `unsupported.tf` | Comments for unsupported types |
| `manifest.json` | Schema-validated export metadata |

## Error Codes

| Code | Range | Meaning | Action |
|------|-------|---------|--------|
| 0 | - | Success | Read SUMMARY, no human action |
| 10-19 | env | Credential/network | Re-run with valid AK |
| 20-29 | config | Invalid arguments | Check CLI args |
| 30-39 | I/O | Filesystem | Check output dir perms |
| 40-49 | API | Mapping/dependency | Check fixtures, review HCL output |

## Sensitive Data Handling

The following fields are masked to variable references:
- `rds.MasterUserPassword` -> `var.rds_password`
- `ec2.password` -> `var.ecs_password`

Sensitive values NEVER appear in:
- HCL output (replaced with var ref)
- manifest.json sensitive_masked (path only)
- import.sh (only IDs, not values)
- stderr/log (paths only, never values)
