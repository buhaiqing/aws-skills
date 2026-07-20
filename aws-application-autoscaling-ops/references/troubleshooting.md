# Troubleshooting — Application Auto Scaling

## Error Table

| Error | Resolution |
|-------|-----------|
| `ObjectNotFoundException` | Resource_id / policy_name typo; verify with `describe-*` |
| `ValidationException` | Verify resource_id format matches ServiceNamespace |
| `LimitExceededException` | Request quota increase (Service Quotas L-7B6389E7) |
| `ConcurrentUpdateException` | Backoff 5s; retry once |
| `FailedResourceAccessException` | IAM missing; verify `application-autoscaling:*` + service role trust |
| `InternalServiceException` | Backoff; HALT after 3 retries |
| `ThrottlingException` | Reduce API call rate; backoff retry |
| `AccessDeniedException` | IAM missing `application-autoscaling:*` permission |

## Polling Limits

- `describe-scalable-targets`: < 5s typical, max 30s
- `describe-scaling-policies`: < 5s typical
- `put-scaling-policy`: < 10s typical

## Common Issues

### Target Tracking not scaling

- Verify `PredefinedMetricType = ECSServiceAverageCPUUtilization` (not `Memory`)
- Check CloudWatch metric `ECS/ContainerInsights` is enabled on cluster
- Verify `ScaleInCooldown >= 300` (default 300 prevents flapping)

### Capacity bound violation

- `MinCapacity > MaxCapacity` → ValidationException
- `MinCapacity = 0` allowed but `desiredCount` requires `>= 1` task in ECS

### Policy persists after deregister

- Always `delete-scaling-policy` first, then `deregister-scalable-target`
- Otherwise describe-scalable-targets returns empty but policy lingers
