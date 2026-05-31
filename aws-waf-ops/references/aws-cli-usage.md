# AWS CLI Usage — WAF

## Common JSON Paths

```
# Create Web ACL:   .Summary.{Id,ARN,Name}
# Get Web ACL:      .WebACL.{Id,ARN,Name,DefaultAction,VisibilityConfig}
# List Web ACLs:    .WebACLs[].{Id,ARN,Name}
# Associate:        Empty (success)
# Get Sampled:      .SampledRequests[].{Request,Timestamp,Action}
# List Resources:   .WebACL.AssociatedResources[]
```

## Command Map

| Goal | CLI Command |
|------|-------------|
| Create Web ACL | `aws wafv2 create-web-acl` |
| Get Web ACL | `aws wafv2 get-web-acl` |
| List Web ACLs | `aws wafv2 list-web-acls` |
| Update Web ACL | `aws wafv2 update-web-acl` |
| Delete Web ACL | `aws wafv2 delete-web-acl` |
| Associate with resource | `aws wafv2 associate-web-acl` |
| Disassociate | `aws wafv2 disassociate-web-acl` |
| Add logging | `aws wafv2 put-logging-configuration` |
| Get sampled requests | `aws wafv2 get-sampled-requests` |

## Quick Start

### Create + Associate Web ACL (One-Command Flow)

```bash
# 1. Create Web ACL with AWS Managed Rules
WEB_ACL_ID=$(aws wafv2 create-web-acl \
  --name prod-web-acl --scope REGIONAL \
  --default-action Allow={} \
  --rules '[
    {"Name":"AWS-AWSManagedRulesCommonRuleSet","Priority":0,
     "Statement":{"ManagedRuleGroupStatement":{"VendorName":"AWS","Name":"AWSManagedRulesCommonRuleSet"}},
     "OverrideAction":{"None":{}},
     "VisibilityConfig":{"SampledRequestsEnabled":true,"CloudWatchMetricsEnabled":true,"MetricName":"CommonRuleSet"}},
    {"Name":"RateLimit","Priority":1,
     "Statement":{"RateBasedStatement":{"Limit":2000,"AggregateKeyType":"IP"}},
     "Action":{"Block":{}},
     "VisibilityConfig":{"SampledRequestsEnabled":true,"CloudWatchMetricsEnabled":true,"MetricName":"RateLimit"}}
  ]' \
  --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=prod-web-acl \
  --query 'Summary.Id' --output text)

# 2. Get full ARN
WEB_ACL_ARN=$(aws wafv2 get-web-acl --name prod-web-acl --scope REGIONAL --id $WEB_ACL_ID --query 'WebACL.ARN' --output text)

# 3. Associate with ALB
aws wafv2 associate-web-acl --web-acl-arn $WEB_ACL_ARN --resource-arn arn:aws:elasticloadbalancing:region:account:loadbalancer/app/my-alb/xxx

echo "Web ACL created and associated: $WEB_ACL_ARN"
```

### Check Sampled Requests

```bash
aws wafv2 get-sampled-requests \
  --web-acl-arn {{web_acl_arn}} \
  --rule-metric-name {{rule_metric_name}} \
  --scope REGIONAL \
  --time-window StartTime={{t0-3h}},EndTime={{t0}}
```

### AIOps Commands

```bash
# WAF effectiveness: blocked vs allowed ratio
aws cloudwatch get-metric-statistics --namespace AWS/WAFV2 \
  --metric-name BlockedRequests \
  --dimensions Name=WebACL,Value={{web_acl_name}} Name=Rule,Value=All \
  --statistics Sum --period 3600 \
  --start-time "$(date -d '-24 hours' -u ...)" --end-time "$(date -u ...)"

# Check if WAF is associated with an ALB
aws wafv2 get-web-acl-for-resource --resource-arn {{lb_arn}}

# Auto-enable rate limiting (AH-08)
aws wafv2 update-web-acl --name {{web_acl_name}} --scope REGIONAL --id {{id}} \
  --rules '[
    {"Name":"EmergencyRateLimit","Priority":100,
     "Statement":{"RateBasedStatement":{"Limit":1000,"AggregateKeyType":"IP"}},
     "Action":{"Block":{}},
     "VisibilityConfig":{"SampledRequestsEnabled":true,"CloudWatchMetricsEnabled":true,"MetricName":"EmergencyRateLimit"}}
  ]'
```
