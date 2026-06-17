# AWS GuardDuty CLI Usage

## Common Commands

### List Detectors
```bash
guardduty list-detectors --region {{user.region}} --output json
```
JSON Paths:
- Detector IDs: `.DetectorIds[]`

### Create Filter
```bash
guardduty create-filter \
  --name {{user.resource_name}} \
  --detector-id {{user.detector_id}} \
  --description {{user.description}} \
  --action {{user.action}} \
  --rank {{user.rank}} \
  --region {{user.region}} \
  --output json
```
JSON Paths:
- Filter ARN: `.FilterArn`
- Filter ID: `.FilterId`

### Delete Filter
```bash
guardduty delete-filter \
  --name {{user.resource_name}} \
  --detector-id {{user.detector_id}} \
  --region {{user.region}} \
  --output json
```

### List Filters
```bash
guardduty list-filters \
  --detector-id {{user.detector_id}} \
  --region {{user.region}} \
  --output json
```
JSON Paths:
- Filter Names: `.FilterNames[]`

### Get Filter
```bash
guardduty get-filter \
  --name {{user.resource_name}} \
  --detector-id {{user.detector_id}} \
  --region {{user.region}} \
  --output json
```
JSON Paths:
- Filter details: `.`

### Create IP Set
```bash
guardduty create-ip-set \
  --name {{user.resource_name}} \
  --detector-id {{user.detector_id}} \
  --location {{user.location}} \
  --activate {{user.activate}} \
  --region {{user.region}} \
  --output json
```
JSON Paths:
- IP Set ID: `.IpSetId`

### Delete IP Set
```bash
guardduty delete-ip-set \
  --ip-set-id {{user.ip_set_id}} \
  --detector-id {{user.detector_id}} \
  --region {{user.region}} \
  --output json
```

### List Findings
```bash
guardduty list-findings \
  --detector-id {{user.detector_id}} \
  --region {{user.region}} \
  --output json
```
JSON Paths:
- Finding IDs: `.FindingIds[]`

### Get Findings
```bash
guardduty get-findings \
  --detector-id {{user.detector_id}} \
  --finding-ids {{user.finding_ids}} \
  --region {{user.region}} \
  --output json
```
JSON Paths:
- Findings: `.`

## Error Codes

| Error Code | Meaning |
|------------|---------|
| ResourceNotFoundException | The specified resource doesn't exist |
| AccessDeniedException | You don't have permission to perform this action |
| InvalidInputException | The request is missing a required parameter or has an invalid value |
| ThrottlingException | The request was throttled |
| InternalServerErrorException | An internal error occurred |