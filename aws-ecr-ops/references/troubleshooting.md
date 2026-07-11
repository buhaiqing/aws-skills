# AWS ECR — Troubleshooting

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `RepositoryNotFoundException` | Repository does not exist | Check name spelling; create if needed |
| `RepositoryAlreadyExistsException` | Name collision | Use different name; or delete & recreate after confirmation |
| `RepositoryNotEmptyException` | Images present; `delete-repository` without `--force` | Warn user; use `--force` if confirmed |
| `ImageNotFoundException` | Tag/digest not found | List images to verify available tags |
| `InvalidParameterException` | Bad name, tag, or policy JSON | Validate name (alphanumeric, `-`, `_`, `.`, `/`); fix policy JSON |
| `LifecyclePolicyNotFoundException` | No policy on this repo | Create one via `put-lifecycle-policy` |
| `AccessDeniedException` | Missing IAM permissions | Check `ecr:*` / `GetAuthorizationToken` in IAM policy |
| `ScanNotFoundException` | No scan result available | Wait for scan to complete; or no image pushed |
| `TooManyTagsException` | >100 tags on image | Clean up old tags; use digests for CI references |
| `KmsException` | KMS key access issue (`encryption-type: KMS`) | Verify KMS key permissions for ECR |
| Throttling (429) | Rate limit exceeded | Exponential backoff; implement retry with jitter |

## Docker Login Failures

| Symptom | Cause | Fix |
|---------|-------|-----|
| `denied: Your authorization token has expired` | Token expired (12h default) | Re-run `get-login-password` |
| `denied: User: arn:aws:iam::... is not authorized` | IAM lacks `ecr:GetAuthorizationToken` | Add `ecr:GetAuthorizationToken` to IAM policy |
| `denied: access to the resource is not authorized` | No `ecr:BatchGetImage` on repository | Add `ecr:BatchGetImage`, `ecr:GetDownloadUrlForLayer` |
| `Error saving credentials` | Docker credential store issue | Check `~/.docker/config.json`; avoid `credStore` conflicts |

## Image Push/Pull Failures

| Symptom | Cause | Fix |
|---------|-------|-----|
| `no basic auth credentials` | Not logged in | Run `get-login-password` + `docker login` |
| `manifest invalid` | Image format not supported | Use multi-arch image; check platform |
| `image size exceeds limit` | > 5 GB manifest size | Split image; use layer optimization |
| `TooManyRequestsException` | API throttling | Backoff; reduce concurrent client requests |
| `ImageTagAlreadyExistsException` | Immutable tag set | Use different tag; delete existing tag; use digest |

## Lifecycle Policy Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| Images not expiring | Policy rule error | Verify `rules[].selection.*` syntax; test with dry-run |
| `InvalidParameterException` on policy | JSON malformed | Validate JSON; check rule structure |
| Policy not applied | Rule index conflict | Use unique `rulePriority` values (lowest = highest priority) |
