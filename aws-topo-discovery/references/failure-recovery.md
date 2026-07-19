# Failure Recovery

| Error Pattern | Max Retries | Backoff | Agent Action |
|--------------|-------------|---------|--------------|
| `InvalidClientTokenId` / `AuthFailure` | 0 | - | HALT. Credentials invalid. User must provide valid AK. |
| `SignatureDoesNotMatch` | 0 | - | HALT. AK/Secret mismatch or time skew. Check credentials. |
| `AccessDenied` / `UnauthorizedAccess` | 0 | - | HALT. Insufficient permissions. User needs `ReadOnlyAccess` or custom read-only policy. |
| `Throttling` / 429 | 3 | Exponential | Back off 2s, 4s, 8s. Retry. |
| `InternalError` / 5xx | 3 | 2s fixed | Retry; continue with partial data if persistent. |
| `InvalidRegion` / `RegionNotFoundException` | 0 | - | HALT. Check `{{env.AWS_DEFAULT_REGION}}`. |
| `InvalidVpcID.NotFound` | 0 | - | Skip VPC, continue scanning. |
| Command Timeout (>30s) | 1 | - | Kill process; log timeout; continue with other resources. |
