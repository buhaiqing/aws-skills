# CloudTrail CloudWatch Logs Errors — Detailed Recovery

## InvalidCloudWatchLogsLogGroup

Log group not created before trail configuration.

```bash
# Create log group
aws logs create-log-group --log-group-name {{log_group_name}}

# Get log group ARN
log_group_arn=$(aws logs describe-log-groups \
  --log-group-name-prefix {{log_group_name}} \
  --query "logGroups[0].arn" --output text)

# Update trail
aws cloudtrail update-trail --name {{trail_name}} \
  --cloud-watch-logs-log-group-arn ${log_group_arn} \
  --cloud-watch-logs-role-arn {{role_arn}}
```

## InvalidCloudWatchLogsRole

IAM role lacks CloudTrail to CloudWatch Logs permissions.

```bash
# Create role with trust policy
aws iam create-role --role-name CloudTrail_CloudWatchLogs_Role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{"Effect": "Allow", "Principal": {"Service": "cloudtrail.amazonaws.com"}, "Action": "sts:AssumeRole"}]
  }'

# Attach policy
aws iam put-role-policy --role-name CloudTrail_CloudWatchLogs_Role \
  --policy-name CloudTrailPolicy --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{"Effect": "Allow", "Action": ["logs:CreateLogStream", "logs:PutLogEvents"], "Resource": "arn:aws:logs:*:*:log-group:{{log_group_name}}:log-stream:*"}]
  }'
```
