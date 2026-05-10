# SNS Troubleshooting

Common SNS error codes, recovery procedures.

## Error Code Reference

### NotFound
```
Error: Topic or subscription not found
```
**Resolution**:
```bash
# List topics
aws sns list-topics --output json

# List subscriptions
aws sns list-subscriptions --output json
```

### EndpointDisabled
```
Error: Endpoint is disabled
```
**Cause**: Email bounced or endpoint invalid.
**Resolution**: Update endpoint or remove subscription.

### InvalidParameter
```
Error: Invalid parameter value
```
**Common causes**:
- Invalid email format
- Non-existent Lambda ARN
- Wrong SQS queue URL

## Common Issues

### Email Not Received
**Causes:**
- Not confirmed
- In spam folder
- Wrong email address
- Bounced

**Resolution:**
1. Check spam folder
2. Resend confirmation
3. Check email address
4. Verify subscription status

### Lambda Not Triggered
**Causes:**
- Lambda permission missing
- Lambda error
- Wrong ARN

**Resolution:**
```bash
# Check Lambda permissions
aws lambda get-policy --function-name {{lambda_name}}

# Add SNS permission if missing
aws lambda add-permission \
  --function-name {{lambda_name}} \
  --action lambda:InvokeFunction \
  --principal sns.amazonaws.com \
  --source-arn {{topic_arn}}
```

### Messages Not Filtered
**Causes:**
- Wrong filter policy syntax
- Attributes not matching

**Resolution:**
```bash
# Check filter policy
aws sns get-subscription-attributes \
  --subscription-arn {{sub_arn}} \
  --attribute-names FilterPolicy
```

## Recovery Procedures

### Subscription Recovery
```
1. Check subscription status
2. Re-subscribe if deleted
3. Confirm email subscription
4. Test with publish
```

### Topic Recovery
```
1. Verify topic exists
2. Check subscriptions
3. Re-create if deleted
4. Re-subscribe endpoints
```