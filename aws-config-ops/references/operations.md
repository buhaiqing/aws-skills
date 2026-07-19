# AWS Config Operations Reference

All CLI commands use `--output json`. Boto3 fallback after 3 CLI failures.

## Common Pre-flight (all ops)

```bash
aws --version && aws sts get-caller-identity --output json
```
Log: `[OK] AWS CLI v2.x` and `[OK] Identity: arn:aws:iam::...`.
For Setup Recorder, also verify service-linked role:
```bash
aws iam get-role --role-name AWSServiceRoleForConfig --output json \
  || aws iam create-service-linked-role --aws-service-name config.amazonaws.com --output json
```

## Setup Configuration Recorder

#### Execute — CLI (Primary)
```bash
aws configservice put-configuration-recorder \
  --configuration-recorder "name={{user.recorder_name}},roleARN=arn:aws:iam::{{env.AWS_ACCOUNT_ID}}:role/aws-service-role/config.amazonaws.com/AWSServiceRoleForConfig" \
  --recording-group "allSupported=true,includeGlobalResourceTypes=true" \
  --region "{{user.region}}" --output json
```

#### Validate
`aws configservice describe-configuration-recorders` → check name and roleARN match.

#### Recover
| Error | Action |
|-------|--------|
| InvalidConfigurationRecorderName / InvalidRole | Fix name or role ARN; retry |
| Throttling | Backoff; retry 3x |

## Setup Delivery Channel
Pre-flight: `aws s3api head-bucket --bucket {{user.s3_bucket}}` (verify bucket exists)
```bash
aws configservice put-delivery-channel \
  --delivery-channel "name={{user.channel_name}},s3BucketName={{user.s3_bucket}},s3KeyPrefix={{user.s3_prefix}},snsTopicARN={{user.sns_topic_arn}}" \
  --region "{{user.region}}" --output json
```

#### Validate
`aws configservice describe-delivery-channels --region "{{user.region}}" --output json` → check `s3BucketName` matches {{user.s3_bucket}} and channel name matches.

#### Recover
| Error | Action |
|-------|--------|
| NoSuchS3Bucket / AccessDenied | Verify S3 bucket exists and Config has `PutObject` permission |
| InvalidDeliveryChannelName | Fix channel name (alphanumeric, hyphens, underscores) |
| Throttling | Backoff; retry 3x |

## Start/Stop Recorder
**Stop Safety Gate**: `confirm=STOP_RECORDER {{user.recorder_name}}`
```bash
aws configservice start-configuration-recorder --configuration-recorder-name "{{user.recorder_name}}" --region "{{user.region}}" --output json
aws configservice stop-configuration-recorder --configuration-recorder-name "{{user.recorder_name}}" --region "{{user.region}}" --output json
```

#### Validate
`describe-configuration-recorder-status` → check `recording=false` after stop.

#### Recover
| Error | Action |
|-------|--------|
| NoSuchConfigurationRecorder | Verify recorder name exists |
| Throttling | Backoff; retry 3x |

## Add Managed Config Rule
```bash
aws configservice put-config-rule \
  --config-rule "ConfigRuleName={{user.rule_name}},Source={Owner=AWS,SourceIdentifier={{user.rule_identifier}}},Scope={ComplianceResourceTypes=[\"AWS::S3::Bucket\"]}" \
  --region "{{user.region}}" --output json
```

#### Validate
`aws configservice describe-config-rules --config-rule-names "{{user.rule_name}}" --region "{{user.region}}" --output json` → check `ConfigRuleName` matches and `ConfigRuleState` is `ACTIVE`.

#### Recover
| Error | Action |
|-------|--------|
| LimitExceeded | Delete unused rules or request quota increase |
| InvalidParameterValue | Verify rule identifier exists (use describe-config-rules to list) |
| InsufficientPermissionsException | Verify IAM permissions for config:PutConfigRule |
| Throttling | Backoff; retry 3x |

## Run Compliance Evaluation
```bash
aws configservice start-config-rules-evaluation --config-rule-names "{{user.rule_name}}" --region "{{user.region}}" --output json
# Query results: aws configservice get-compliance-details-by-config-rule --config-rule-name "{{user.rule_name}}" --compliance-types NON_COMPLIANT
```

#### Validate
`aws configservice describe-config-rule-evaluation-status --config-rule-names "{{user.rule_name}}" --region "{{user.region}}" --output json` → check `LastSuccessfulEvaluationTime` is recent.

#### Recover
| Error | Action |
|-------|--------|
| NoSuchConfigRuleException | Verify rule name exists and is ACTIVE |
| Throttling | Backoff; retry 3x |

## Delete Config Rule
**Safety Gate**: `confirm=DELETE_RULE {{user.rule_name}}`
Pre-flight: verify rule exists via `describe-config-rules`.
```bash
aws configservice delete-config-rule --config-rule-name "{{user.rule_name}}" --region "{{user.region}}" --output json
```

#### Validate
`describe-config-rules --config-rule-names "{{user.rule_name}}"` returns empty (NoSuchConfigRuleException expected).

#### Recover
| Error | Action |
|-------|--------|
| NoSuchConfigRuleException | Already deleted; skip |
| ResourceInUseException | Rule part of conformance pack; delete pack first |
| Throttling | Backoff; retry 3x |

## Set Up Aggregator
```bash
# Single account source
aws configservice put-configuration-aggregator \
  --configuration-aggregator-name "{{user.aggregator_name}}" \
  --account-aggregation-sources "[{\"AccountIds\":[\"123456789012\"],\"AllAwsRegions\":true}]" \
  --region "{{user.region}}" --output json
# Organization source (requires Organizations + Trusted Access)
aws configservice put-configuration-aggregator \
  --configuration-aggregator-name "{{user.aggregator_name}}" \
  --organization-aggregation-source "RoleArn=arn:aws:iam::{{env.AWS_ACCOUNT_ID}}:role/aws-service-role/config.amazonaws.com/AWSServiceRoleForConfig,AllAwsRegions=true" \
  --region "{{user.region}}" --output json
```

#### Validate
`aws configservice describe-configuration-aggregators --region "{{user.region}}" --output json` → check `ConfigurationAggregatorName` matches and `ConfigurationStatus` is `CREATE_COMPLETE`.

#### Recover
| Error | Action |
|-------|--------|
| LimitExceeded | Delete unused aggregators or request quota increase |
| InvalidConfigurationAggregator | Fix aggregator name (alphanumeric, hyphens, underscores) |
| Throttling | Backoff; retry 3x |

## Deploy Conformance Pack
```bash
aws configservice put-conformance-pack \
  --conformance-pack-name "{{user.pack_name}}" \
  --template-s3-uri "{{user.pack_template_uri}}" \
  --region "{{user.region}}" --output json
```

#### Validate
`aws configservice describe-conformance-packs --conformance-pack-names "{{user.pack_name}}"` → check `ConformancePackStatus` is `CREATE_COMPLETE` or `UPDATE_COMPLETE`.

#### Recover
| Error | Action |
|-------|--------|
| ConformancePackTemplateValidationException | Fix template YAML/JSON; verify SSM URI accessible |
| LimitExceeded | Delete unused packs or request quota increase |
| Throttling | Backoff; retry 3x |

## Delete Conformance Pack
**Safety Gate**: `confirm=DELETE_PACK {{user.pack_name}}`
```bash
aws configservice delete-conformance-pack \
  --conformance-pack-name "{{user.pack_name}}" \
  --region "{{user.region}}" --output json
```

#### Validate
`describe-conformance-packs` returns empty for {{user.pack_name}}.

#### Recover
| Error | Action |
|-------|--------|
| NoSuchResourceException | Already deleted; skip |
| Throttling | Backoff; retry 3x |

## Delete Delivery Channel
**Safety Gate**: `confirm=DELETE_CHANNEL {{user.channel_name}}`
Pre-flight: verify no other delivery channel exists (deleting the only channel breaks all Config delivery).
```bash
aws configservice describe-delivery-channels --region "{{user.region}}" --output json
```
If only channel exists, warn: deleting will stop all Config deliveries.
```bash
aws configservice delete-delivery-channel \
  --delivery-channel-name "{{user.channel_name}}" \
  --region "{{user.region}}" --output json
```

#### Validate
`describe-delivery-channels` returns empty for {{user.channel_name}}.

#### Recover
| Error | Action |
|-------|--------|
| LastDeliveryChannelDeleteFailed | Delivery in progress; wait and retry |
| Throttling | Backoff; retry 3x |

## Delete Configuration Aggregator
**Safety Gate**: `confirm=DELETE_AGGREGATOR {{user.aggregator_name}}`
Pre-flight: check all aggregators and their authorization sources.
```bash
aws configservice describe-configuration-aggregators --region "{{user.region}}" --output json
```
```bash
aws configservice delete-configuration-aggregator \
  --configuration-aggregator-name "{{user.aggregator_name}}" \
  --region "{{user.region}}" --output json
```

#### Validate
`describe-configuration-aggregators` returns empty for {{user.aggregator_name}}.

#### Recover
| Error | Action |
|-------|--------|
| NoSuchAggregator | Already deleted; skip |
| Throttling | Backoff; retry 3x |

## Delete Aggregation Authorization
**Safety Gate**: `confirm=DELETE_AUTH {{user.aggregator_source}}`
```bash
aws configservice list-aggregation-authorizations --region "{{user.region}}" --output json
```
```bash
aws configservice delete-aggregation-authorization \
  --authorized-account-id "{{user.aggregator_source}}" \
  --configuration-aggregator-name "{{user.aggregator_name}}" \
  --region "{{user.region}}" --output json
```

#### Validate
`list-aggregation-authorizations` no longer lists the authorized account.

#### Recover
| Error | Action |
|-------|--------|
| NoSuchAggregator | Verify aggregator name; check aggregator exists |
| Throttling | Backoff; retry 3x |

## Setup Retention Configuration
```bash
aws configservice put-retention-configuration \
  --retention-period-in-days 365 \
  --region "{{user.region}}" --output json
```
Note: Retention period must be between 1 and 2557 days (7 years).
`confirm=SHORT_RETENTION <days>` required for < 30 days.

#### Validate
`aws configservice describe-retention-configuration --region "{{user.region}}" --output json`

#### Recover
| Error | Action |
|-------|--------|
| InvalidRetentionPeriod | Must be 1-2557 days |
| Throttling | Backoff; retry 3x |

## Delete Retention Configuration
Reverts to default 7-year retention.
**Safety Gate**: `confirm=DELETE_RETENTION`
```bash
aws configservice delete-retention-configuration --region "{{user.region}}" --output json
```

#### Validate
`describe-retention-configuration` returns empty or throws NoSuchRetentionConfigurationException.

#### Recover
| Error | Action |
|-------|--------|
| NoSuchRetentionConfigurationException | Already deleted; skip |
| Throttling | Backoff; retry 3x |

## Custom Config Rule (Lambda-backed)
```bash
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "check-instance-type",
    "Source": {
      "Owner": "CUSTOM_LAMBDA",
      "SourceIdentifier": "arn:aws:lambda:{{user.region}}:{{env.AWS_ACCOUNT_ID}}:function:my-config-rule",
      "SourceDetails": [
        {"EventSource": "aws.config", "MessageType": "ConfigurationItemChangeNotification"}
      ]
    },
    "MaximumExecutionFrequency": "TwentyFourHours"
  }' \
  --region "{{user.region}}" --output json
```
Pre-flight: verify Lambda function exists via `aws lambda get-function --function-name my-config-rule`.

#### Validate
`aws configservice describe-config-rules --config-rule-names "check-instance-type"` → check `Source.Owner=CUSTOM_LAMBDA`.

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameterValue | Check Lambda ARN validity and permissions |
| ResourceNotFoundException | Verify Lambda function exists in region |
| InsufficientPermissionsException | Grant Lambda `config:Put*` permissions |
| Throttling | Backoff; retry 3x |

## Query Resources (SQL-style)
```bash
aws configservice select-resource-config \
  --expression "SELECT resourceId, resourceType, resourceName, tags WHERE resourceType = 'AWS::EC2::Instance'" \
  --region "{{user.region}}" --output json
```

## Get Resource Config History
```bash
aws configservice get-resource-config-history \
  --resource-type "AWS::EC2::Instance" \
  --resource-id "i-1234567890abcdef0" \
  --region "{{user.region}}" --output json
```

## Batch Get Resource Config
```bash
aws configservice batch-get-resource-config \
  --resource-keys '[{"resourceType":"AWS::EC2::Instance","resourceId":"i-1234567890abcdef0"}]' \
  --region "{{user.region}}" --output json
```

## List Discovered Resources
```bash
aws configservice list-discovered-resources \
  --resource-type "AWS::EC2::Instance" \
  --region "{{user.region}}" --output json
```

## Compliance Summary
```bash
aws configservice get-compliance-summary-by-config-rule \
  --config-rule-name "{{user.rule_name}}" \
  --region "{{user.region}}" --output json
```

## Get Compliance Details
```bash
aws configservice get-compliance-details-by-config-rule \
  --config-rule-name "{{user.rule_name}}" \
  --compliance-types NON_COMPLIANT \
  --region "{{user.region}}" --output json
```

## Delete Configuration Recorder
**Pre-flight**: Stop recorder first (deleting active recorder is not allowed).
**Safety Gate**: `confirm=DELETE_RECORDER {{user.recorder_name}}`
```bash
# Step 1: Stop recorder
aws configservice stop-configuration-recorder \
  --configuration-recorder-name "{{user.recorder_name}}" \
  --region "{{user.region}}" --output json
# Step 2: Delete recorder
aws configservice delete-configuration-recorder \
  --configuration-recorder-name "{{user.recorder_name}}" \
  --region "{{user.region}}" --output json
```

#### Validate
`describe-configuration-recorders` returns empty for {{user.recorder_name}}.

#### Recover
| Error | Action |
|-------|--------|
| LastDeliveryChannelDeleteFailed | Delete delivery channel first |
| Throttling | Backoff; retry 3x |

## Deploy Organization Config Rule
```bash
aws configservice put-organization-config-rule \
  --organization-config-rule-name "{{user.rule_name}}" \
  --organization-managed-rule-metadata "{\"RuleIdentifier\":\"{{user.rule_identifier}}\",\"MaximumExecutionFrequency\":\"TwentyFourHours\"}" \
  --region "{{user.region}}" --output json
```
Pre-flight: verify AWS Organizations trusted access is enabled:
```bash
aws organizations list-aws-services-access-for-organization --output json | grep config
```

#### Validate
`aws configservice describe-organization-config-rules --region "{{user.region}}" --output json` → check `OrganizationConfigRuleStatus` is `ACTIVE`.

#### Recover
| Error | Action |
|-------|--------|
| AccessDeniedException | Enable trusted access in AWS Organizations |
| InvalidInput | Verify rule identifier and metadata JSON |
| Throttling | Backoff; retry 3x |

## Delete Organization Config Rule
**Safety Gate**: `confirm=DELETE_ORG_RULE {{user.rule_name}}`
Pre-flight: verify rule exists via `describe-organization-config-rules`.
```bash
aws configservice delete-organization-config-rule \
  --organization-config-rule-name "{{user.rule_name}}" \
  --region "{{user.region}}" --output json
```

#### Validate
`describe-organization-config-rules` returns empty for {{user.rule_name}}.

#### Recover
| Error | Action |
|-------|--------|
| NoSuchOrganizationConfigRuleException | Already deleted; skip |
| Throttling | Backoff; retry 3x |
