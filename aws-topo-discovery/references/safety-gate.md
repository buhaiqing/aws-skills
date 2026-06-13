# Safety Gate Specification

## Core Principle

All execution paths in this Skill MUST strictly enforce **Read-Only** policy.

## Allowed Operations

| API Prefix | Description |
|-----------|-------------|
| `Describe*` | Query resource details/list |
| `List*` | Query resource list |
| `Get*` | Query single resource details |
| `sts assume-role` | **Special case**: Allowed for cross-account scanning via STS AssumeRole. Changes caller identity but does NOT modify target resources. Only triggered when `--assume-role` is explicitly specified. |

## Forbidden Operations

| API Prefix | Risk |
|-----------|------|
| `Create*` | Create/provision resources |
| `Delete*` | Delete/release resources |
| `Modify*` | Modify configuration/state |
| `Update*` | Update resource metadata |
| `Associate*` | Associate/bind resources (e.g. EIP) |
| `Disassociate*` | Disassociate/unbind resources |
| `Authorize*` | Authorize (e.g. security group rules) |
| `Revoke*` | Revoke authorization |
| `Stop*` / `Start*` | Stop/start instances |
| `Reboot*` | Reboot instances |
| `Run*` / `Invoke*` | Execute commands/actions |
| `Terminate*` | Terminate instances |
| `Attach*` / `Detach*` | Attach/detach volumes, policies |
| `Release*` | Release resources (e.g. EIP) |
| `Put*` | Put data/config (e.g. S3 objects, CloudWatch) |

## Pre-Execution Validation

All CLI commands must pass regex validation before execution:
```python
ALLOWED_PATTERN = r"^(describe-|list-|get-|sts assume-role)"
FORBIDDEN_PATTERN = r"(create-|delete-|modify-|update-|associate-|disassociate-|authorize-|revoke-|stop-|start-|reboot-|run-|terminate-|invoke-|attach-|detach-|release-|put-)"
```
Any command matching the forbidden pattern causes immediate HALT.

> **Note**: `sts assume-role` is only called when `--assume-role` parameter is explicitly passed. This operation changes caller identity but does NOT modify any cloud resources — it is an allowed exception.

## Credential Safety

- Access Key IDs (`AKIA*`) and Secret Keys MUST NEVER appear in output, logs, or traces
- All credential references must be masked: `AKIA******XXXX` (first 4 + last 4 chars)
- Session tokens must be masked to `***<length>`
