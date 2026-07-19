# Budget Alerts & CloudWatch Alarms

## List Existing Budgets

```bash
aws budgets describe-budgets \
  --account-id {{env.AWS_ACCOUNT_ID}} \
  --output json
```

## Common JSON Paths

```python
# Budget response
$.Budgets[].BudgetName
$.Budgets[].BudgetLimit.Amount
$.Budgets[].BudgetLimit.Unit
$.Budgets[].CostFilters
$.Budgets[].CostTypes
```

## CloudWatch Alert on Budget

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name aws-finops-budget-{{BUDGET_NAME}}-alert \
  --alarm-description "Alert when budget {{BUDGET_NAME}} exceeds 80%" \
  --namespace AWS/Billing \
  --metric-name EstimatedCharges \
  --dimensions Name=LinkedAccount,Value={{env.AWS_ACCOUNT_ID}} Name=Currency,Value=USD \
  --period 21600 \
  --evaluation-periods 1 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --statistic Maximum \
  --output json
```

## Budget Threshold Reference

See `assets/budget-thresholds.yaml` for standard thresholds (% of budget).
