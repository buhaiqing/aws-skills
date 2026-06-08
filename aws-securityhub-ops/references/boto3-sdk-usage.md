# boto3 SDK Usage — Security Hub

Python boto3 patterns for Security Hub operations.

## Client Initialization
```python
import boto3
from botocore.exceptions import ClientError
sh = boto3.client('securityhub', region_name='{{env.AWS_DEFAULT_REGION}}')
```

## Hub Management

### Enable Security Hub
```python
def enable_security_hub(auto_enable_controls=True, enable_default_standards=True):
    try:
        return sh.enable_security_hub(
            EnableDefaultStandards=enable_default_standards,
            AutoEnableControls=auto_enable_controls
        )
    except ClientError as e: handle_sh_error(e)
```

### Describe Hub
```python
def describe_hub():
    try: return sh.describe_hub()
    except ClientError as e: handle_sh_error(e)
```

### Disable Security Hub
```python
def disable_security_hub():
    try: return sh.disable_security_hub()
    except ClientError as e: handle_sh_error(e)
```

## Insight Management

### Create Insight
```python
def create_insight(name, filters, group_by_attribute="ResourceId"):
    try:
        return sh.create_insight(
            Name=name, Filters=filters, GroupByAttribute=group_by_attribute
        )
    except ClientError as e: handle_sh_error(e)
```

### GetInsights
```python
def get_insights(insight_arns=None):
    params = {}
    if insight_arns: params['InsightArns'] = insight_arns
    try: return sh.get_insights(**params)
    except ClientError as e: handle_sh_error(e)
```

### UpdateInsight
```python
def update_insight(insight_arn, filters=None, name=None, group_by_attribute=None):
    params = {'InsightArn': insight_arn}
    if filters: params['Filters'] = filters
    if name: params['Name'] = name
    if group_by_attribute: params['GroupByAttribute'] = group_by_attribute
    try: return sh.update_insight(**params)
    except ClientError as e: handle_sh_error(e)
```

### DeleteInsight
```python
def delete_insight(insight_arn):
    try: return sh.delete_insight(InsightArn=insight_arn)
    except ClientError as e: handle_sh_error(e)
```

## Action Target Management

### CreateActionTarget
```python
def create_action_target(name, description, target_id):
    try:
        return sh.create_action_target(
            Name=name, Description=description, Id=target_id
        )
    except ClientError as e: handle_sh_error(e)
```

### DescribeActionTargets
```python
def describe_action_targets(action_target_arns):
    try:
        return sh.describe_action_targets(ActionTargetArns=action_target_arns)
    except ClientError as e: handle_sh_error(e)
```

### UpdateActionTarget
```python
def update_action_target(action_target_arn, name=None, description=None):
    params = {'ActionTargetArn': action_target_arn}
    if name: params['Name'] = name
    if description: params['Description'] = description
    try: return sh.update_action_target(**params)
    except ClientError as e: handle_sh_error(e)
```

### DeleteActionTarget
```python
def delete_action_target(action_target_arn):
    try: return sh.delete_action_target(ActionTargetArn=action_target_arn)
    except ClientError as e: handle_sh_error(e)
```

## Finding Management

### BatchImportFindings
```python
def batch_import_findings(findings):
    try: return sh.batch_import_findings(Findings=findings)
    except ClientError as e: handle_sh_error(e)
```

### BatchUpdateFindings
```python
def batch_update_findings(finding_identifiers, workflow=None, note=None, severity=None):
    params = {'FindingIdentifiers': finding_identifiers}
    if workflow: params['Workflow'] = workflow
    if note: params['Note'] = note
    if severity: params['Severity'] = severity
    try: return sh.batch_update_findings(**params)
    except ClientError as e: handle_sh_error(e)
```

### GetFindings
```python
def get_findings(filters=None, sort_criteria=None, max_results=50):
    params = {'MaxResults': max_results}
    if filters: params['Filters'] = filters
    if sort_criteria: params['SortCriteria'] = sort_criteria
    try: return sh.get_findings(**params)
    except ClientError as e: handle_sh_error(e)
```

## Standards Management

### BatchEnableStandards
```python
def batch_enable_standards(standards_arns):
    try:
        return sh.batch_enable_standards(
            StandardsSubscriptionRequests=[
                {'StandardsArn': arn} for arn in standards_arns
            ]
        )
    except ClientError as e: handle_sh_error(e)
```

### BatchDisableStandards
```python
def batch_disable_standards(standards_subscription_arns):
    try:
        return sh.batch_disable_standards(
            StandardsSubscriptionArns=standards_subscription_arns
        )
    except ClientError as e: handle_sh_error(e)
```

### GetEnabledStandards
```python
def get_enabled_standards():
    try: return sh.get_enabled_standards()
    except ClientError as e: handle_sh_error(e)
```

### DescribeStandardsControls
```python
def describe_standards_controls(standards_subscription_arn):
    try:
        return sh.describe_standards_controls(
            StandardsSubscriptionArn=standards_subscription_arn
        )
    except ClientError as e: handle_sh_error(e)
```

## Controls Management

### UpdateStandardsControl
```python
def update_standards_control(standards_control_arn, control_status, disabled_reason=None):
    params = {
        'StandardsControlArn': standards_control_arn,
        'ControlStatus': control_status
    }
    if disabled_reason: params['DisabledReason'] = disabled_reason
    try: return sh.update_standards_control(**params)
    except ClientError as e: handle_sh_error(e)
```

## Product Subscription

### ListEnabledProductsForImport
```python
def list_enabled_products():
    try: return sh.list_enabled_products_for_import()
    except ClientError as e: handle_sh_error(e)
```

### EnableImportFindingsForProduct
```python
def enable_import_findings(product_arn):
    try: return sh.enable_import_findings_for_product(ProductArn=product_arn)
    except ClientError as e: handle_sh_error(e)
```

### DisableImportFindingsForProduct
```python
def disable_import_findings(product_subscription_arn):
    try:
        return sh.disable_import_findings_for_product(
            ProductSubscriptionArn=product_subscription_arn
        )
    except ClientError as e: handle_sh_error(e)
```

## Automation Rules

### CreateAutomationRule
```python
def create_automation_rule(name, rule_order, criteria, actions, status="ENABLED"):
    try:
        return sh.create_automation_rule(
            RuleName=name, RuleOrder=rule_order, RuleStatus=status,
            Criteria=criteria, Actions=actions
        )
    except ClientError as e: handle_sh_error(e)
```

### ListAutomationRules
```python
def list_automation_rules():
    try: return sh.list_automation_rules()
    except ClientError as e: handle_sh_error(e)
```

### UpdateAutomationRule
```python
def update_automation_rule(rule_arn, rule_status=None, criteria=None, actions=None):
    params = {'RuleArn': rule_arn}
    if rule_status: params['RuleStatus'] = rule_status
    if criteria: params['Criteria'] = criteria
    if actions: params['Actions'] = actions
    try: return sh.update_automation_rule(**params)
    except ClientError as e: handle_sh_error(e)
```

### DeleteAutomationRule
```python
def delete_automation_rule(rule_arn):
    try: return sh.delete_automation_rule(RuleArn=rule_arn)
    except ClientError as e: handle_sh_error(e)
```

## Configuration Policy (Organizations)

### CreateConfigurationPolicy
```python
def create_configuration_policy(name, configuration_policy, description=None):
    params = {'Name': name, 'ConfigurationPolicy': configuration_policy}
    if description: params['Description'] = description
    try: return sh.create_configuration_policy(**params)
    except ClientError as e: handle_sh_error(e)
```

### GetConfigurationPolicy
```python
def get_configuration_policy(policy_id):
    try: return sh.get_configuration_policy(Identifier=policy_id)
    except ClientError as e: handle_sh_error(e)
```

### UpdateConfigurationPolicy
```python
def update_configuration_policy(policy_id, name=None, configuration_policy=None):
    params = {'Identifier': policy_id}
    if name: params['Name'] = name
    if configuration_policy: params['ConfigurationPolicy'] = configuration_policy
    try: return sh.update_configuration_policy(**params)
    except ClientError as e: handle_sh_error(e)
```

### DeleteConfigurationPolicy
```python
def delete_configuration_policy(policy_id):
    try: return sh.delete_configuration_policy(Identifier=policy_id)
    except ClientError as e: handle_sh_error(e)
```

## Error Handling
```python
def handle_sh_error(error):
    code = error.response['Error']['Code']
    msg = error.response['Error']['Message']
    recovery_map = {
        'ResourceNotFoundException': 'HALT — verify ARN exists',
        'InvalidAccessException': 'HALT — check IAM permissions for securityhub:*',
        'LimitExceededException': 'HALT — request quota increase',
        'InvalidInputException': 'HALT — fix request parameters',
        'InternalException': 'RETRY — AWS internal error, retry 3x',
        'AccessDeniedException': 'HALT — insufficient IAM permissions',
    }
    recovery = recovery_map.get(code, 'HALT — check AWS docs')
    raise Exception(f"SecurityHub Error [{code}]: {msg}\nRecovery: {recovery}")
```
