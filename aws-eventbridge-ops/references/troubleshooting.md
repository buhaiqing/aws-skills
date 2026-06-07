# Troubleshooting — EventBridge

## Common API Errors

| Error | Meaning | Action |
|-------|---------|--------|
| ResourceNotFoundException | Bus/rule/target not found | Verify name and region |
| ConcurrentModificationException | Resource being modified | Retry with backoff |
| LimitExceededException | Quota reached | HALT; request increase |
| ValidationException | Invalid parameters | Fix args per API docs |
| ThrottlingException | Rate limit | Backoff; retry 3x |
| InternalException | Service error | Retry 3x; HALT |

## Rule Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Rule never triggers | Event pattern too narrow or wrong bus | Test with `test-event-pattern` |
| Rule triggers too often | Event pattern too broad | Narrow pattern fields |
| Target not invoked | Target ARN invalid | Verify target exists and region matches |
| Cannot delete rule | Targets still attached | `remove-targets` first |
| Rule disabled automatically | Managed by AWS service | Check `ManagedBy` field |
| Schedule rule doesn't fire | Expression in wrong timezone | EventBridge uses UTC |

## Schedule (Scheduler) Issues

| Symptom | Resolution |
|---------|------------|
| Schedule not firing | Check `State=ENABLED`; verify target role has permissions |
| Schedule can't create | Verify `flexible-time-window` is set (required in some regions) |
| Schedule deleted but still running | CloudFront cache; wait ~30s |
| Target role insufficient | Check `iam:PassRole` permission on scheduler service |

## Pipe Issues

| Symptom | Resolution |
|---------|------------|
| Pipe stuck CREATING | Check target role and source permissions |
| Pipe not processing | Verify `DesiredState=RUNNING` |
| Enrichment not working | Check enrichment Lambda function and permissions |

## Archive / Replay

| Symptom | Resolution |
|---------|------------|
| Archive not capturing events | Verify bus ARN is correct; filter may be too narrow |
| Replay fails | Archive may not have events in time range; check `State=AVAILABLE` |
| Replay stuck | Events being replayed at original rate; can take time |

## API Destination Issues

| Symptom | Resolution |
|---------|------------|
| API destination invocation fails | Check connection state is `ACTIVE`; endpoint reachable |
| Connection AUTHORIZATION_ERROR | Check API keys or OAuth credentials |
| Invocation rate exceeded | Set `invocation-rate-limit-per-second`