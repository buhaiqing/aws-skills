# AWS GuardDuty Troubleshooting

## Common Issues & Solutions

### Issue: No detectors found in region
**Error**: `ResourceNotFoundException: The detector is not found.`
**Cause**: GuardDuty is not enabled in the specified region
**Resolution**: Enable GuardDuty first with `aws guardduty enable-guardduty --region {{user.region}}`

### Issue: Access denied when listing detectors
**Error**: `AccessDeniedException: User: arn:aws:iam::123456789012:user/xxx is not authorized to perform: guardduty:ListDetectors`
**Cause**: Missing IAM permissions for GuardDuty
**Resolution**: Add IAM policy with permissions: `guardduty:ListDetectors`, `guardduty:DescribeDetector`

### Issue: Filter already exists
**Error**: `ResourceAlreadyExistsException: The filter already exists.`
**Cause**: A filter with the same name already exists in the detector
**Resolution**: Use a different filter name or delete the existing filter first

### Issue: Throttling errors
**Error**: `ThrottlingException: Rate exceeded`
**Cause**: Too many requests in a short period
**Resolution**: Wait and retry with exponential backoff, or request a service quota increase

### Issue: Internal server error
**Error**: `InternalServerErrorException: An internal error occurred.`
**Cause**: AWS GuardDuty service issue
**Resolution**: Retry after some time, or contact AWS support if the issue persists

### Issue: Cannot delete detector
**Error**: `ResourceCannotBeDeletedException: The detector cannot be deleted.`
**Cause**: The detector has active members or is the primary detector in an organization
**Resolution**: Disable GuardDuty for all member accounts first, then delete the detector

## Error Code Reference

| Error Code | Description |
|------------|-------------|
| AccessDeniedException | You don't have permission to perform the action |
| ResourceNotFoundException | The specified resource doesn't exist |
| ResourceAlreadyExistsException | The resource already exists |
| InvalidInputException | The input is invalid |
| ThrottlingException | The request was throttled |
| InternalServerErrorException | An internal error occurred |
| ResourceCannotBeDeletedException | The resource cannot be deleted |

## Debugging Tips

1. **Check GuardDuty status**: `aws guardduty get-detector --detector-id {{user.detector_id}} --region {{user.region}}`
2. **List current filters**: `aws guardduty list-filters --detector-id {{user.detector_id}} --region {{user.region}}`
3. **Check IAM permissions**: Use `aws sts get-caller-identity` to verify your current identity
4. **Verify region**: Ensure you're using the correct region where GuardDuty is enabled