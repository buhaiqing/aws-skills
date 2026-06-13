# RDS Instance Field Mapping

**AWS API**: `rds describe-db-instances` -> `aws_db_instance`

## Mapping Rules

| HCL Attribute | API JSON Path | Type | Required | Notes |
|---------------|---------------|------|----------|-------|
| `identifier` | `DBInstanceIdentifier` | string | Y | Block name derived from this |
| `engine` | `Engine` | string | Y | e.g. `mysql`, `postgres` |
| `engine_version` | `EngineVersion` | string | Y | e.g. `8.0.35` |
| `instance_class` | `DBInstanceClass` | string | Y | e.g. `db.r5.large` |
| `allocated_storage` | `AllocatedStorage` | int | Y | Storage in GB |
| `port` | `Endpoint.Port` | int | N | Default per engine |
| `db_subnet_group_name` | `DBSubnetGroup.DBSubnetGroupName` | string | N | Subnet group |
| `password` | (not in API) | string | Y | **sensitive=true**, masked to `var.rds_password` |

## Block Name

`{db_instance_identifier}` (e.g. `prod_mysql_01`)

## Stable Import ID

`{db_instance_identifier}` (e.g. `prod-mysql-01`)

## Notes

- `MasterUserPassword` is NOT returned by describe API — always use `var.rds_password`
- `MasterUsername` is returned and mapped to `username`
