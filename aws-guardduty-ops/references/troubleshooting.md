# GuardDuty Troubleshooting

Common GuardDuty error codes, recovery procedures, and operational troubleshooting.

## Error Reference

### Request Errors
| Error | Resolution |
|-------|-----------|
| BadRequestException | HALT — fix request params (invalid detector ID, malformed criteria) |
| ResourceNotFoundException | Verify detector/set/destination ID exists; check region |
| AccessDeniedException | HALT — add `guardduty:*` or specific action to IAM policy |

### Account / Member Errors
| Error | Resolution |
|-------|-----------|
| InvalidInputException | HALT — verify account ID format (12 digits) |
| InvitationAlreadyExists | Member already invited; check `list-invitations` |
| MembershipNotFound | Account not associated; use `invite-members` first |

### Set / Destination Errors
| Error | Resolution |
|-------|-----------|
| InvalidParameterException | HALT — verify S3 URL format, file format, or IP CIDR syntax |
| PublishingDestinationAlreadyExists | Only 1 destination per detector; use `update-publishing-destination` |
| UnableToPublish | Check S3 bucket policy, KMS key permissions, or bucket region |

## Throttling (429)
Exponential backoff strategy:
```python
import time, math
def exponential_backoff(attempt, base=0.5, max_delay=60):
    time.sleep(min(base * math.pow(2, attempt), max_delay))
```

## Finding Investigation Flow
| Symptom | Check | Action |
|---------|-------|--------|
| Unexpected finding | `get-findings` for full detail | Verify if expected traffic; archive if false positive |
| High volume of findings | Review filters; add trusted IPs to IP set | Create `ARCHIVE` filter for known-good patterns |
| No findings after enable | Wait 1-24h; check CloudTrail/DNS/Flow Logs enabled | Verify data sources in detector settings |
| Member findings not visible | `list-members` → check `RelationshipStatus` | Re-invite or accept invitation |

## Recovery Procedures
**Detector**: Identify error → check state → apply fix (retry once) → HALT if persistent.
**Findings**: List → get details → investigate → archive/unarchive.
**Sets**: Verify S3 file accessible → check format → re-upload → update location.
**Members**: Verify invitation status → re-invite if needed → accept on member side.
**Destination**: Verify S3 bucket exists → check bucket policy → verify KMS permissions → retry.
