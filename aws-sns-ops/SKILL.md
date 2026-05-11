# AWS SNS Ops Skill

AWS SNS (Simple Notification Service) operational skill for AI Agent automation.

## Triggers

**SHOULD activate when:**
- User requests topic creation or deletion
- User needs to manage subscriptions
- User asks about SNS notifications
- User mentions "SNS", "topic", "subscription", "notification"
- User needs to configure message filtering
- User asks about Lambda/SQS integration

**SHOULD-NOT activate when:**
- SQS operations (use `aws-sqs-ops`)
- EventBridge (use `aws-eventbridge-ops`)
- Direct messaging (use application-level messaging)

**Delegation:**
- Lambda → `aws-lambda-ops` (SNS trigger)
- SQS → `aws-sqs-ops` (SQS subscription)
- KMS → `aws-kms-ops` (topic encryption)

## Scope

| Operation | Supported | Safety Gate |
|-----------|-----------|-------------|
| Create Topic | Yes | None |
| Delete Topic | Yes | **Human confirmation** |
| List Topics | Yes | None |
| Publish Message | Yes | None |
| Subscribe | Yes | None |
| Unsubscribe | Yes | None |
| Set Filter Policy | Yes | None |
| Confirm Subscription | Yes | None |

## Variable Convention

| Variable | Source | Example |
|----------|--------|---------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Environment | Never ask user |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Environment | Never ask user |
| `{{env.AWS_DEFAULT_REGION}}` | Environment | us-east-1 |
| `{{user.TopicName}}` | User input | my-topic |
| `{{user.TopicArn}}` | User input | arn:aws:sns:... |
| `{{user.Protocol}}` | User input | email, sqs, lambda, http |
| `{{user.Endpoint}}` | User input | email@example.com |
| `{{user.SubscriptionArn}}` | User input | arn:aws:sns:... |

## Execution Flow

### Pre-flight

**Step 1: Check CLI**
```bash
aws --version
```
Log: `[OK] AWS CLI v2.x.x detected` or `[FAIL] AWS CLI not found. Install: uv pip install awscli`

**Step 2: Load & Verify Credentials**
```bash
aws sts get-caller-identity --output json
```

Log format:
```
[SKILL] Loading AWS credentials...
[OK]   AWS_DEFAULT_REGION={{env.AWS_DEFAULT_REGION}} (from .env)
[OK]   AWS_ACCESS_KEY_ID=**** (from .env, masked)
[OK]   Credential verification passed
[OK]   Identity: arn:aws:iam::{{env.AWS_ACCOUNT_ID}}:user/xxx
```

On failure:
```
[FAIL] AWS credential verification failed.
AWS Error: <exact error message>
Action: See references/integration.md → Error Messages for diagnosis.
```

```
3. Verify topic exists: aws sns get-topic-attributes --topic-arn {{user.TopicArn}}
4. Check permissions
```

### Execute (Primary: CLI)
```
aws sns publish \
  --topic-arn {{user.TopicArn}} \
  --message "{{user.Message}}" \
  --subject "{{user.Subject}}" \
  --output json
```

### Execute (Fallback: boto3)
```python
import boto3
sns = boto3.client('sns', region_name='{{env.AWS_DEFAULT_REGION}}')
response = sns.publish(
    TopicArn='{{user.TopicArn}}',
    Message='{{user.Message}}'
)
```

## Safety Gates

### Topic Deletion
```
BEFORE delete-topic:
1. Display: "Deleting {{user.TopicName}} will remove all subscriptions"
2. Ask: "Type 'DELETE {{user.TopicName}}' to confirm"
```

## Output Convention

Key JSON paths:
- `.TopicArn` - topic ARN
- `.SubscriptionArn` - subscription ARN
- `.MessageId` - published message ID
- `.Endpoint` - subscriber endpoint
- `.Protocol` - subscription protocol

## Related Skills

- `aws-lambda-ops` - Lambda subscription
- `aws-sqs-ops` - SQS subscription
- `aws-kms-ops` - Topic encryption

## Reference Files

- `references/aws-cli-usage.md`
- `references/boto3-sdk-usage.md`
- `references/core-concepts.md`
- `references/troubleshooting.md`
- `assets/example-config.yaml`