# AWS CLI Usage — Security Hub

AWS CLI commands for Security Hub operations. All commands use `--output json`.

## Common JSON Paths (Reusable)
```
# Hub:          .HubArn, .SubscribedAt, .AutoEnableControls
# Insights:     .Insights[].{InsightArn,Name,Filters,GroupByAttribute}
# ActionTargets: .ActionTargets[].{ActionTargetArn,Name,Description}
# Findings:     .Findings[].{Id,Title,Severity.Label,Compliance.Status,Workflow.Status,RecordState,ProductArn}
# Standards:    .Standards[].{StandardsArn,StandardsInput.Name,Enabled}
# Controls:     .Controls[].{ControlId,Title,ControlStatus,Compliance.Status}
# Products:     .ProductSubscriptions[]
# AutomationRules: .AutomationRules[].{RuleArn,RuleName,RuleStatus}
```

## Hub Management

### Enable Security Hub
```bash
aws securityhub enable-security-hub \
  --enable-default-standards \
  --auto-enable-controls \
  --region {{user.region}} \
  --output json
```

### Describe Hub
```bash
aws securityhub describe-hub --region {{user.region}} --output json
```

### Disable Security Hub
```bash
# Pre-flight: list enabled standards and product subscriptions
aws securityhub get-enabled-standards --region {{user.region}} --output json
aws securityhub list-enabled-products-for-import --region {{user.region}} --output json

# Execute (requires explicit confirmation)
aws securityhub disable-security-hub --region {{user.region}} --output json
```

## Insight Management

### Create Insight
```bash
aws securityhub create-insight \
  --name "{{user.insight_name}}" \
  --filters '{"SeverityLabel": [{"Comparison": "EQUALS", "Value": "CRITICAL"}]}' \
  --group-by-attribute "ResourceId" \
  --region {{user.region}} \
  --output json
```

### Get Insights
```bash
aws securityhub get-insights --insight-arns "{{user.insight_arn}}" --region {{user.region}} --output json
aws securityhub get-insights --region {{user.region}} --output json  # all insights
```

### Update Insight
```bash
aws securityhub update-insight \
  --insight-arn "{{user.insight_arn}}" \
  --filters '{"SeverityLabel": [{"Comparison": "EQUALS", "Value": "HIGH"}]}' \
  --region {{user.region}} \
  --output json
```

### Delete Insight
```bash
# Pre-flight: verify insight exists
aws securityhub get-insights --insight-arns "{{user.insight_arn}}" --region {{user.region}} --output json

# Execute (requires explicit confirmation)
aws securityhub delete-insight --insight-arn "{{user.insight_arn}}" --region {{user.region}} --output json
```

## Action Target Management

### Create Action Target
```bash
aws securityhub create-action-target \
  --name "{{user.action_target_name}}" \
  --description "{{user.action_target_description}}" \
  --id "{{user.action_target_id}}" \
  --region {{user.region}} \
  --output json
```

### Describe Action Targets
```bash
aws securityhub describe-action-targets \
  --action-target-arns "{{user.action_target_arn}}" \
  --region {{user.region}} \
  --output json
```

### Update Action Target
```bash
aws securityhub update-action-target \
  --action-target-arn "{{user.action_target_arn}}" \
  --name "{{user.new_name}}" \
  --description "{{user.new_description}}" \
  --region {{user.region}} \
  --output json
```

### Delete Action Target
```bash
# Pre-flight: verify action target exists
aws securityhub describe-action-targets \
  --action-target-arns "{{user.action_target_arn}}" \
  --region {{user.region}} \
  --output json

# Execute (requires explicit confirmation)
aws securityhub delete-action-target \
  --action-target-arn "{{user.action_target_arn}}" \
  --region {{user.region}} \
  --output json
```

## Finding Management

### Batch Import Findings
```bash
aws securityhub batch-import-findings \
  --findings '[{"SchemaVersion": "2018-10-08", "Id": "{{user.finding_id}}", "ProductArn": "arn:aws:securityhub:{{user.region}}:{{env.AWS_ACCOUNT_ID}}:product/{{env.AWS_ACCOUNT_ID}}/default", "GeneratorId": "{{user.generator_id}}", "AwsAccountId": "{{env.AWS_ACCOUNT_ID}}", "Types": ["Software and Configuration Checks/Vulnerabilities/CVE"], "CreatedAt": "{{user.timestamp}}", "UpdatedAt": "{{user.timestamp}}", "Severity": {"Label": "HIGH"}, "Title": "{{user.finding_title}}", "Description": "{{user.finding_description}}", "Resources": [{"Type": "AwsEc2Instance", "Id": "{{user.resource_arn}}"}]}]' \
  --region {{user.region}} \
  --output json
```

### Batch Update Findings
```bash
aws securityhub batch-update-findings \
  --finding-identifiers '[{"Id": "{{user.finding_id}}", "ProductArn": "{{user.product_arn}}"}]' \
  --workflow '{"Status": "RESOLVED"}' \
  --note '{"Text": "Resolved via automation", "UpdatedBy": "aws-agent"}' \
  --region {{user.region}} \
  --output json
```

### Get Findings
```bash
aws securityhub get-findings \
  --filters '{"SeverityLabel": [{"Comparison": "EQUALS", "Value": "CRITICAL"}]}' \
  --sort-criteria '[{"Field": "SeverityLabel", "SortOrder": "desc"}]' \
  --max-items 50 \
  --region {{user.region}} \
  --output json
```

## Standards Management

### Get Enabled Standards
```bash
aws securityhub get-enabled-standards --region {{user.region}} --output json
```

### Enable Standard
```bash
aws securityhub batch-enable-standards \
  --standards-subscription-requests '[{"StandardsArn": "{{user.standard_arn}}"}]' \
  --region {{user.region}} \
  --output json
```

### Disable Standard
```bash
aws securityhub batch-disable-standards \
  --standards-subscription-arns '["{{user.standards_subscription_arn}}"]' \
  --region {{user.region}} \
  --output json
```

### Describe Standards Controls
```bash
aws securityhub describe-standards-controls \
  --standards-subscription-arn "{{user.standards_subscription_arn}}" \
  --region {{user.region}} \
  --output json
```

## Controls Management

### Update Control Status
```bash
aws securityhub update-standards-control \
  --standards-control-arn "{{user.standards_control_arn}}" \
  --control-status "DISABLED" \
  --disabled-reason "{{user.disabled_reason}}" \
  --region {{user.region}} \
  --output json
```

### Enable Control
```bash
aws securityhub update-standards-control \
  --standards-control-arn "{{user.standards_control_arn}}" \
  --control-status "ENABLED" \
  --region {{user.region}} \
  --output json
```

## Product Subscription

### List Enabled Products
```bash
aws securityhub list-enabled-products-for-import --region {{user.region}} --output json
```

### Enable Import Findings for Product
```bash
aws securityhub enable-import-findings-for-product \
  --product-arn "{{user.product_arn}}" \
  --region {{user.region}} \
  --output json
```

### Disable Import Findings for Product
```bash
# Pre-flight: verify product is enabled
aws securityhub list-enabled-products-for-import --region {{user.region}} --output json

# Execute (requires explicit confirmation)
aws securityhub disable-import-findings-for-product \
  --product-subscription-arn "{{user.product_subscription_arn}}" \
  --region {{user.region}} \
  --output json
```

## Automation Rules

### Create Automation Rule
```bash
aws securityhub create-automation-rule \
  --rule-name "{{user.rule_name}}" \
  --rule-order {{user.rule_order}} \
  --rule-status "ENABLED" \
  --criteria '{"SeverityLabel": [{"Comparison": "EQUALS", "Value": "CRITICAL"}]}' \
  --actions '[{"Type": "FINDING_FIELDS_UPDATE", "FindingFieldsUpdate": {"Workflow": {"Status": "NEW"}, "Severity": {"Label": "CRITICAL"}, "Note": {"Text": "Auto-triaged", "UpdatedBy": "automation-rule"}}}]' \
  --region {{user.region}} \
  --output json
```

### List Automation Rules
```bash
aws securityhub list-automation-rules --region {{user.region}} --output json
```

### Update Automation Rule
```bash
aws securityhub update-automation-rule \
  --rule-arn "{{user.automation_rule_arn}}" \
  --rule-status "DISABLED" \
  --region {{user.region}} \
  --output json
```

### Delete Automation Rule
```bash
# Pre-flight: verify rule exists
aws securityhub list-automation-rules --region {{user.region}} --output json

# Execute (requires explicit confirmation)
aws securityhub delete-automation-rule \
  --rule-arn "{{user.automation_rule_arn}}" \
  --region {{user.region}} \
  --output json
```

## Configuration Policy (Organizations)

### Create Configuration Policy
```bash
aws securityhub create-configuration-policy \
  --name "{{user.policy_name}}" \
  --configuration-policy '{"SecurityHub": {"ServiceEnabled": true, "EnabledStandardIdentifiers": ["arn:aws:securityhub:::ruleset/cis-aws-foundations-benchmark/v/1.2.0"], "SecurityControlsConfiguration": {"EnabledSecurityControlIdentifiers": ["IAM.1", "S3.1"], "DisabledSecurityControlIdentifiers": []}}}' \
  --description "{{user.policy_description}}" \
  --region {{user.region}} \
  --output json
```

### Get Configuration Policy
```bash
aws securityhub get-configuration-policy \
  --identifier "{{user.policy_id}}" \
  --region {{user.region}} \
  --output json
```

### Update Configuration Policy
```bash
aws securityhub update-configuration-policy \
  --identifier "{{user.policy_id}}" \
  --name "{{user.new_policy_name}}" \
  --configuration-policy '{"SecurityHub": {"ServiceEnabled": true, "EnabledStandardIdentifiers": ["arn:aws:securityhub:::ruleset/cis-aws-foundations-benchmark/v/1.2.0"], "SecurityControlsConfiguration": {"EnabledSecurityControlIdentifiers": ["IAM.1", "S3.1", "EC2.1"], "DisabledSecurityControlIdentifiers": []}}}' \
  --region {{user.region}} \
  --output json
```

### Delete Configuration Policy
```bash
# Pre-flight: verify policy exists and is not attached
aws securityhub get-configuration-policy --identifier "{{user.policy_id}}" --region {{user.region}} --output json
aws securityhub list-configuration-policy-associations --region {{user.region}} --output json

# Execute (requires explicit confirmation)
aws securityhub delete-configuration-policy \
  --identifier "{{user.policy_id}}" \
  --region {{user.region}} \
  --output json
```

## Common Filter Patterns
```
# Critical findings
--filters '{"SeverityLabel": [{"Comparison": "EQUALS", "Value": "CRITICAL"}]}'

# Unresolved findings
--filters '{"WorkflowStatus": [{"Comparison": "EQUALS", "Value": "NEW"}]}'

# By resource type
--filters '{"ResourceType": [{"Comparison": "EQUALS", "Value": "AwsEc2Instance"}]}'

# By compliance status
--filters '{"ComplianceStatus": [{"Comparison": "EQUALS", "Value": "FAILED"}]}'

# By record state
--filters '{"RecordState": [{"Comparison": "EQUALS", "Value": "ACTIVE"}]}'
```
