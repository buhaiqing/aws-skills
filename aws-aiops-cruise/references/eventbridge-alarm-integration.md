# EventBridge Alarm → AIOps Cruise Integration

## Pattern

```
CloudWatch Alarm (ALARM)
        │
        ▼
EventBridge (CloudWatch Alarm State Change)
        │
        ├── SNS → Lambda / Chatbot / manual
        │
        └── SSM Automation / ECS task → alarm-trigger.sh
                    │
                    ▼
            emergency-troubleshoot.py
                    │
                    ▼
            aiops_context JSON → aws-aiops-orchestrator (if ≥3 CRITICAL)
```

## Deploy CloudFormation snippet

Template: [`assets/ci-cd-templates/eventbridge-alarm-cruise.json`](../assets/ci-cd-templates/eventbridge-alarm-cruise.json)

```bash
aws cloudformation deploy \
  --template-file aws-aiops-cruise/assets/ci-cd-templates/eventbridge-alarm-cruise.json \
  --stack-name aws-aiops-cruise-alerts \
  --capabilities CAPABILITY_IAM
```

Subscribe your runner (examples):

- **Lambda**: parse SNS message → invoke `alarm-trigger.sh` with `--alarm-name`
- **SSM Automation**: run `python3 .../emergency-troubleshoot.py` on hybrid worker with IAM read-only
- **Manual**: SNS email → on-call runs:

```bash
bash aws-aiops-cruise/runbooks/scripts/alarm-trigger.sh \
  --alarm-name prod-alb-target-5xx \
  --resource-group prod-web-rg \
  --region us-east-1 \
  --symptom 502
```

## Event pattern (JSON)

```json
{
  "source": ["aws.cloudwatch"],
  "detail-type": ["CloudWatch Alarm State Change"],
  "detail": {
    "state": { "value": ["ALARM"] }
  }
}
```

## IAM (read-only cruise worker)

Minimum for patrol scripts:

- `cloudwatch:GetMetricStatistics`, `cloudwatch:DescribeAlarms`
- `elasticloadbalancing:Describe*`, `ec2:Describe*`, `rds:Describe*`
- `pi:GetResourceMetrics` (Performance Insights)
- `xray:GetServiceGraph` (optional `--enable-xray`)
- `cloudfront:ListDistributions`
- `sns:Publish` (EventBridge target only — not required on cruise worker)

## Multi-region

Create one rule per region or use EventBridge global endpoint with `region` field in input transformer.

## Safety

Cruise remains **read-only**. EventBridge only triggers diagnosis — no auto-remediation without `aws-aiops-orchestrator` + human confirm.
