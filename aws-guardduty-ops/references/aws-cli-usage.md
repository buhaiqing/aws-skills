# AWS CLI Usage - GuardDuty

AWS CLI commands for GuardDuty operations. All commands use `--output json`.

## Common JSON Paths (Reusable)
```
# Detectors: .DetectorIds[0], .Status (get-detector)
# Findings: .FindingIds[], .FindingDetails[].{Id,Type,Severity,AccountId,Region}
# IP Sets: .IpSetIds[], .Name, .Status, .Format (get-ip-set)
# Threat Intel Sets: .ThreatIntelSetIds[], .Name, .Status, .Format (get-threat-intel-set)
# Filters: .FilterNames[], .Action, .Rank (get-filter)
# Members: .Members[].{AccountId,Email,RelationshipStatus}
# Destinations: .DestinationIds[], .DestinationType, .Status (describe-publishing-destination)
```

## Detector Operations

### Create Detector
```bash
aws guardduty create-detector --enable --finding-publishing-frequency FIFTEEN_MINUTES --output json
```

### List / Get / Update / Delete
```bash
aws guardduty list-detectors --output json
aws guardduty get-detector --detector-id {{user.detector_id}} --output json
aws guardduty update-detector --detector-id {{user.detector_id}} --enable --finding-publishing-frequency ONE_HOUR --output json
aws guardduty delete-detector --detector-id {{user.detector_id}} --output json  # Safety: confirm
```

## Finding Operations

### List Findings
```bash
aws guardduty list-findings --detector-id {{user.detector_id}} --output json
aws guardduty list-findings --detector-id {{user.detector_id}} --finding-criteria '{"Criterion":{"severity":{"Eq":["7"]}}}' --output json
```

### Get Finding Details
```bash
aws guardduty get-findings --detector-id {{user.detector_id}} --finding-ids {{user.finding_ids}} --output json
```

### Archive / Unarchive
```bash
aws guardduty archive-findings --detector-id {{user.detector_id}} --finding-ids {{user.finding_ids}} --output json
aws guardduty unarchive-findings --detector-id {{user.detector_id}} --finding-ids {{user.finding_ids}} --output json
```

## Filter Operations

### Create / Update / Delete / List
```bash
aws guardduty create-filter --detector-id {{user.detector_id}} --name {{user.filter_name}} --action ARCHIVE --rank 1 --finding-criteria '{...}' --output json
aws guardduty update-filter --detector-id {{user.detector_id}} --name {{user.filter_name}} --finding-criteria '{...}' --output json
aws guardduty delete-filter --detector-id {{user.detector_id}} --name {{user.filter_name}} --output json  # Safety: confirm
aws guardduty list-filters --detector-id {{user.detector_id}} --output json
aws guardduty get-filter --detector-id {{user.detector_id}} --name {{user.filter_name}} --output json
```

## IP Set Operations

### Create / Update / Delete / List / Activate
```bash
aws guardduty create-ip-set --detector-id {{user.detector_id}} --name "trusted-ips" --format TXT --location "https://s3.amazonaws.com/{{bucket}}/trusted_ips.txt" --activate --output json
aws guardduty update-ip-set --detector-id {{user.detector_id}} --ip-set-id {{user.ip_set_id}} --location "https://s3.amazonaws.com/{{bucket}}/trusted_ips_v2.txt" --output json
aws guardduty delete-ip-set --detector-id {{user.detector_id}} --ip-set-id {{user.ip_set_id}} --output json  # Safety: confirm
aws guardduty list-ip-sets --detector-id {{user.detector_id}} --output json
aws guardduty get-ip-set --detector-id {{user.detector_id}} --ip-set-id {{user.ip_set_id}} --output json
aws guardduty update-ip-set --detector-id {{user.detector_id}} --ip-set-id {{user.ip_set_id}} --no-activate --output json
```

## Threat Intel Set Operations

### Create / Update / Delete / List / Activate
```bash
aws guardduty create-threat-intel-set --detector-id {{user.detector_id}} --name "custom-threats" --format TXT --location "https://s3.amazonaws.com/{{bucket}}/threats.txt" --activate --output json
aws guardduty update-threat-intel-set --detector-id {{user.detector_id}} --threat-intel-set-id {{user.threat_intel_set_id}} --location "https://s3.amazonaws.com/{{bucket}}/threats_v2.txt" --output json
aws guardduty delete-threat-intel-set --detector-id {{user.detector_id}} --threat-intel-set-id {{user.threat_intel_set_id}} --output json  # Safety: confirm
aws guardduty list-threat-intel-sets --detector-id {{user.detector_id}} --output json
aws guardduty get-threat-intel-set --detector-id {{user.detector_id}} --threat-intel-set-id {{user.threat_intel_set_id}} --output json
aws guardduty update-threat-intel-set --detector-id {{user.detector_id}} --threat-intel-set-id {{user.threat_intel_set_id}} --no-activate --output json
```

## Member Account Operations

### Invite / Accept / Disassociate / Delete
```bash
aws guardduty invite-members --detector-id {{user.detector_id}} --account-ids {{member_account_id}} --message "Enable GuardDuty" --output json
aws guardduty list-members --detector-id {{user.detector_id}} --output json
aws guardduty get-members --detector-id {{user.detector_id}} --account-ids {{member_account_id}} --output json
aws guardduty disassociate-members --detector-id {{user.detector_id}} --account-ids {{member_account_id}} --output json
aws guardduty delete-members --detector-id {{user.detector_id}} --account-ids {{member_account_id}} --output json  # Safety: confirm
```

### Accept Invitation (member side)
```bash
aws guardduty accept-invitation --detector-id {{user.detector_id}} --master-id {{master_account_id}} --invitation-id {{invitation_id}} --output json
```

## Publishing Destination Operations

### Create / Describe / Update / Delete
```bash
aws guardduty create-publishing-destination --detector-id {{user.detector_id}} --destination-type S3 --destination-properties '{"DestinationArn":"arn:aws:s3:::{{bucket}}","KmsKeyArn":"arn:aws:kms:{{region}}:{{account}}:key/{{key_id}}"}' --output json
aws guardduty describe-publishing-destination --detector-id {{user.detector_id}} --destination-id {{user.destination_id}} --output json
aws guardduty update-publishing-destination --detector-id {{user.detector_id}} --destination-id {{user.destination_id}} --destination-properties '{"DestinationArn":"arn:aws:s3:::{{new_bucket}}"}' --output json
aws guardduty delete-publishing-destination --detector-id {{user.detector_id}} --destination-id {{user.destination_id}} --output json  # Safety: confirm
aws guardduty list-publishing-destinations --detector-id {{user.detector_id}} --output json
```

## Common Option Flags
```
--finding-publishing-frequency ONE_HOUR | FIFTEEN_MINUTES | ONE_HOUR | SIX_HOURS
--enable | --no-enable
--activate | --no-activate
--format TXT | STIX | OTX_CSV | ALIEN_VAULT | PROOF_POINT | FIRE_EYE
```
