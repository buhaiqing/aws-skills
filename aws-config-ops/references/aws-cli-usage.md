# AWS CLI Usage — AWS Config

## Common JSON Paths (Centralized)

```
# Recorder:         .ConfigurationRecorders[0].{name,roleARN,recordingGroup.{allSupported,includeGlobalResourceTypes,resourceTypes}}
# Recording Status: .ConfigurationRecorderStatus{name,lastStatus,lastStartTime,recording}
# Delivery:         .DeliveryChannels[0].{name,s3BucketName,s3KeyPrefix,snsTopicARN,snapshotDeliveryProperties.deliveryFrequency}
# Rules:            .ConfigRules[].{ConfigRuleName,ConfigRuleId,ConfigRuleState,Source.{Owner,SourceIdentifier},Scope.ComplianceResourceTypes,MaximumExecutionFrequency}
# Rule Status:      .ConfigRuleEvaluationStatus[].{ConfigRuleName,FirstActivatedTime,LastErrorCode,LastFailedEvaluationTime}
# Compliance:       .EvaluationResults[].{ComplianceResourceType,ComplianceResourceId,ComplianceType,Annotation}
# Aggregator:       .ConfigurationAggregators[].{ConfigurationAggregatorName,ConfigurationAggregatorArn}
# Pack:             .ConformancePackDetails[].{ConformancePackName,ConformancePackId,TemplateSSMUri}
# Org Rule:         .OrganizationConfigRules[].{OrganizationConfigRuleName,OrganizationConfigRuleId}
# Discovered:       .resourceIdentifiers[].{resourceType,resourceId,resourceName}
```

## Command Map

| Goal | CLI Command |
|------|-------------|
| Setup recorder | `aws configservice put-configuration-recorder` |
| Describe recorder | `aws configservice describe-configuration-recorders` |
| Start recorder | `aws configservice start-configuration-recorder` |
| Stop recorder | `aws configservice stop-configuration-recorder` |
| Delete recorder | `aws configservice delete-configuration-recorder` |
| Setup delivery channel | `aws configservice put-delivery-channel` |
| Describe delivery channels | `aws configservice describe-delivery-channels` |
| Delete delivery channel | `aws configservice delete-delivery-channel` |
| Add/update config rule | `aws configservice put-config-rule` |
| Describe config rules | `aws configservice describe-config-rules` |
| Delete config rule | `aws configservice delete-config-rule` |
| Start evaluation | `aws configservice start-config-rules-evaluation` |
| Get compliance details | `aws configservice get-compliance-details-by-config-rule` |
| List compliant/non-compliant | `aws configservice get-compliance-summary-by-config-rule` |
| Put conformance pack | `aws configservice put-conformance-pack` |
| Describe conformance packs | `aws configservice describe-conformance-packs` |
| Delete conformance pack | `aws configservice delete-conformance-pack` |
| Put aggregator | `aws configservice put-configuration-aggregator` |
| Describe aggregators | `aws configservice describe-configuration-aggregators` |
| Delete aggregator | `aws configservice delete-configuration-aggregator` |
| Put organization rule | `aws configservice put-organization-config-rule` |
| Describe org rules | `aws configservice describe-organization-config-rules` |
| Delete org rule | `aws configservice delete-organization-config-rule` |
| List discovered resources | `aws configservice list-discovered-resources` |
| Get resource config history | `aws configservice get-resource-config-history` |
| Select resources (SQL) | `aws configservice select-resource-config` |
| Put retention configuration | `aws configservice put-retention-configuration` |

## Common Patterns

### Full Setup (Recorder + Delivery + Start)
```bash
# Step 1: Create service-linked role (if not exists)
aws iam create-service-linked-role --aws-service-name config.amazonaws.com --output json

# Step 2: Put configuration recorder
aws configservice put-configuration-recorder \
  --configuration-recorder "name=default,roleARN=arn:aws:iam::123456789012:role/aws-service-role/config.amazonaws.com/AWSServiceRoleForConfig" \
  --recording-group "allSupported=true,includeGlobalResourceTypes=true" \
  --region us-east-1 \
  --output json

# Step 3: Put delivery channel (requires S3 bucket)
aws configservice put-delivery-channel \
  --delivery-channel "name=default,s3BucketName=my-config-bucket,s3KeyPrefix=config,configSnapshotDeliveryProperties={deliveryFrequency=TwentyFourHours}" \
  --region us-east-1 \
  --output json

# Step 4: Start recorder
aws configservice start-configuration-recorder \
  --configuration-recorder-name default \
  --region us-east-1 \
  --output json
```

### Add Managed Rule
```bash
aws configservice put-config-rule \
  --config-rule 'ConfigRuleName=s3-public-read-prohibited,Source={Owner=AWS,SourceIdentifier=S3_BUCKET_PUBLIC_READ_PROHIBITED},Scope={ComplianceResourceTypes=["AWS::S3::Bucket"]}' \
  --region us-east-1 \
  --output json
```

### List All Non-Compliant Resources
```bash
aws configservice get-compliance-details-by-config-rule \
  --config-rule-name s3-public-read-prohibited \
  --compliance-types NON_COMPLIANT \
  --region us-east-1 \
  --output json
```

### Check Recorder Status
```bash
aws configservice describe-configuration-recorder-status \
  --configuration-recorder-names default \
  --region us-east-1 \
  --output json \
  | jq '.ConfigurationRecordersStatus[] | {name, recording, lastStatus, lastStartTime}'
```

### List Discovered Resources
```bash
aws configservice list-discovered-resources \
  --resource-type AWS::EC2::Instance \
  --region us-east-1 \
  --output json
```

### Query Resources with SQL
```bash
aws configservice select-resource-config \
  --expression "SELECT resourceId, resourceType, resourceName, tags WHERE resourceType = 'AWS::EC2::Instance'" \
  --region us-east-1 \
  --output json
```

### Batch Get Resource Config
```bash
aws configservice batch-get-resource-config \
  --resource-keys '[{"resourceType":"AWS::EC2::Instance","resourceId":"i-1234567890abcdef0"}]' \
  --region us-east-1 \
  --output json
```

## Retry Strategy

| Error Code | Retry? | Max Retries |
|------------|--------|-------------|
| InvalidParameter | No | 0 |
| AccessDenied | No | 0 |
| ResourceNotFoundException | No | 0 |
| NoSuchConfigRuleException | No | 0 |
| MaxNumberOfConfigRulesExceeded | No | HALT, request increase |
| ThrottlingException | Yes | 3 with exponential backoff |
| LastDeliveryChannelDeleteFailed | No | HALT; delivery in progress |
| InsufficientPermissionsException | No | HALT; check IAM |
| InternalError | Yes | 3 with backoff |