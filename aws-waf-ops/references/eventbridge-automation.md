# EventBridge Automation — ELB Config Change Auto-Trigger

_Lastest update: 2026-05-31_

This document defines EventBridge rules that automatically trigger AIOps workflows
when ELB configuration changes occur.

---

## Event Pattern: LB Attribute Change

Triggers when LB attributes are modified (deletion_protection, cross_zone, access_logs):

```json
{
  "source": ["aws.elasticloadbalancing"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventSource": ["elasticloadbalancing.amazonaws.com"],
    "eventName": ["ModifyLoadBalancerAttributes"]
  }
}
```

## Event Pattern: Security Group Change

Triggers when LB security groups are modified — common RCA trigger:

```json
{
  "source": ["aws.elasticloadbalancing"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventSource": ["elasticloadbalancing.amazonaws.com"],
    "eventName": ["SetSecurityGroups"]
  }
}
```

## Event Pattern: Target Registration Change

Triggers when targets are registered/deregistered — for health RCA correlation:

```json
{
  "source": ["aws.elasticloadbalancing"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventSource": ["elasticloadbalancing.amazonaws.com"],
    "eventName": ["RegisterTargets", "DeregisterTargets"]
  }
}
```

## Target: Lambda Function

```json
{
  "targets": [{
    "arn": "arn:aws:lambda:region:account:function:trigger-aiops-compliance-scan",
    "input": "{\"trigger\":\"compliance-scan\"}"
  }]
}
```

## Create EventBridge Rule (CLI)

```bash
event_pattern='{
  "source": ["aws.elasticloadbalancing"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventSource": ["elasticloadbalancing.amazonaws.com"],
    "eventName": ["ModifyLoadBalancerAttributes", "SetSecurityGroups"]
  }
}'

aws events put-rule \
  --name elb-config-change-trigger \
  --event-pattern "$event_pattern" \
  --description "AIOps: Trigger compliance scan on ELB config change"

aws events put-targets \
  --rule elb-config-change-trigger \
  --targets "Id=1,Arn=arn:aws:lambda:region:account:function:trigger-aiops-compliance-scan"
```

## AIOps Workflow Triggered

| Config Change | Triggered AIOps Action |
|--------------|------------------------|
| ModifyLoadBalancerAttributes | Compliance scan: verify deletion_protection, cross_zone, access_logs |
| SetSecurityGroups | RC-03 RCA: check if new SG blocks health check traffic |
| RegisterTargets | AH-01 validate: verify new target becomes healthy within 5 min |
| DeregisterTargets | Cost check: verify target count still meets HA requirements |
