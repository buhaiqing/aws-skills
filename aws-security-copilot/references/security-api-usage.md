# Security API Usage Reference

> Common JSON paths for GuardDuty, Security Hub, Config, IAM Access Analyzer, Secrets Manager, KMS, CloudTrail.

## Common JSON Paths

```json
// GuardDuty finding IDs
[].FindingIds[]

// GuardDuty severity
[].Severity

// Security Hub finding ARN
[].ProductArn

// Security Hub severity label
[].Severity.Label

// Config rule compliance
[].Compliance.ComplianceType

// IAM Access Analyzer finding resource
[].Resource

// Secrets Manager secret lastRotated
[].LastRotatedDate

// KMS key keyManager
[].KeyManager

// CloudTrail eventTime
[].CloudTrailEvent.eventTime
```

## GuardDuty

```bash
# List finding IDs (filter HIGH/CRITICAL)
aws guardduty list-findings \
  --detector-id {{guardduty_detector_id}} \
  --finding-criteria '{"SeverityNames":{"Eq":["HIGH","CRITICAL"]}}' \
  --output json

# Get finding details
aws guardduty get-findings \
  --detector-id {{guardduty_detector_id}} \
  --finding-ids '{{output.finding_ids[]}}' \
  --output json
```

JSON paths: `FindingIds[]`, `Service.Action.ActionType`, `Service.Resource.ResourceType`, `Service.Severity`

## Security Hub

```bash
# Get findings by severity
aws securityhub get-findings \
  --filters '{"SeverityLabel":[{"Value":"CRITICAL","Comparison":"EQUALS"}]}' \
  --output json

# Get insight results
aws securityhub get-insight-results \
  --insight-arn {{securityhub_insight_arn}} \
  --output json
```

JSON paths: `Findings[].Id`, `Findings[].Severity.Label`, `Findings[].Resources[].Id`, `Findings[].Types[]`

## Config

```bash
# Compliance summary
aws configservice get-compliance-summary-by-config-rule \
  --config-rules {{config_rule_names}} \
  --output json

# Get conformance pack compliance
aws configservice get-conformance-pack-compliance-summary \
  --conformance-pack-arn {{conformance_pack_arn}} \
  --output json
```

JSON paths: `ComplianceSummaries[].ComplianceType`, `ComplianceSummaries[].ComplianceContributorCount.CompliantRules`

## IAM Access Analyzer

```bash
# List policy findings
aws accessanalyzer list-findings \
  --analyzer-arn {{accessanalyzer_arn}} \
  --filter '{"status":{"eq":["ACTIVE"]}}' \
  --output json
```

JSON paths: `findings[].id`, `findings[].resource`, `findings[].issueId`, `findings[].action[]`

## Secrets Manager

```bash
# List secrets
aws secretsmanager list-secrets \
  --output json
```

JSON paths: `SecretList[].Name`, `SecretList[].LastRotatedDate`, `SecretList[].Tags[?Key==`CreatedBy`].Value`

## KMS

```bash
# List keys
aws kms list-keys \
  --output json

# Get key rotation status
aws kms get-key-rotation-status \
  --key-id {{kms_key_id}} \
  --output json
```

JSON paths: `Keys[].KeyId`, `KeyRotationStatus.KeyRotationEnabled`

## CloudTrail

```bash
# Lookup events
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventSource,AttributeValue=iam.amazonaws.com \
  --output json
```

JSON paths: `Events[].CloudTrailEvent` (JSON string, parse further), `Events[].EventTime`, `Events[].EventName`
