# AWS CLI Usage — EventBridge

> JSON paths are centralized in `SKILL.md` §Common JSON Paths (TE-4).

## Command Map

| Goal | CLI Command |
|------|-------------|
| Put event bus | `aws events create-event-bus` / `put-event-bus` |
| Describe event bus | `aws events describe-event-bus` |
| Delete event bus | `aws events delete-event-bus` |
| Put rule | `aws events put-rule` |
| Describe rule | `aws events describe-rule` |
| Delete rule | `aws events delete-rule` |
| Put targets | `aws events put-targets` |
| Remove targets | `aws events remove-targets` |
| List targets | `aws events list-targets-by-rule` |
| Create connection | `aws events create-connection` |
| Create API destination | `aws events create-api-destination` |
| Create archive | `aws events create-archive` |
| Start replay | `aws events start-replay` |
| Enable/disable rule | `aws events enable-rule` / `disable-rule` |
| Put permission | `aws events put-permission` |
| Create schedule | `aws scheduler create-schedule` |
| Delete schedule | `aws scheduler delete-schedule` |
| Get schedule | `aws scheduler get-schedule` |
| List schedules | `aws scheduler list-schedules` |
| Create pipe | `aws pipes create-pipe` |
| Delete pipe | `aws pipes delete-pipe` |
| Describe pipe | `aws pipes describe-pipe` |
| List pipes | `aws pipes list-pipes` |

## Common Patterns

### Event Rule with Lambda Target
```bash
aws events put-rule \
  --name "ec2-state-change" \
  --event-pattern '{"source": ["aws.ec2"], "detail-type": ["EC2 Instance State-change Notification"]}' \
  --state ENABLED \
  --region us-east-1 \
  --output json

aws events put-targets \
  --rule "ec2-state-change" \
  --targets '[{"Id":"1","Arn":"arn:aws:lambda:us-east-1:123456789012:function:my-handler"}]' \
  --region us-east-1 \
  --output json
```

### Schedule (rate-based)
```bash
aws scheduler create-schedule \
  --name "my-schedule" \
  --schedule-expression "rate(5 minutes)" \
  --target '{"Arn":"arn:aws:lambda:us-east-1:123456789012:function:my-handler","RoleArn":"arn:aws:iam::123456789012:role/scheduler-role","Input":"{\"key\":\"value\"}"}' \
  --flexible-time-window '{"Mode":"OFF"}' \
  --region us-east-1 \
  --output json
```

### Archive and Replay
```bash
aws events create-archive \
  --archive-name "my-archive" \
  --event-source-arn "arn:aws:events:us-east-1:123456789012:event-bus/default" \
  --retention-days 30 \
  --region us-east-1 \
  --output json

aws events start-replay \
  --replay-name "my-replay" \
  --event-source-arn "arn:aws:events:us-east-1:123456789012:archive/my-archive" \
  --destination '{"Arn":"arn:aws:events:us-east-1:123456789012:event-bus/default"}' \
  --event-start-time "2026-06-01T00:00:00Z" \
  --event-end-time "2026-06-02T00:00:00Z" \
  --region us-east-1 \
  --output json
```

### Delete Rule (with targets cleanup)
```bash
# Step 1: List targets
aws events list-targets-by-rule --rule "my-rule" --region us-east-1 --output json

# Step 2: Remove all targets
aws events remove-targets \
  --rule "my-rule" \
  --ids "1" "2" \
  --region us-east-1 \
  --output json

# Step 3: Delete rule
aws events delete-rule --name "my-rule" --region us-east-1 --output json
```

### Event Pipe
```bash
aws pipes create-pipe \
  --name "my-pipe" \
  --source "arn:aws:sqs:us-east-1:123456789012:my-queue" \
  --target "arn:aws:lambda:us-east-1:123456789012:function:my-handler" \
  --role-arn "arn:aws:iam::123456789012:role/pipe-role" \
  --region us-east-1 \
  --output json
```

### Cross-account Event Bus Permission
```bash
aws events put-permission \
  --event-bus-name "default" \
  --action "events:PutEvents" \
  --principal "123456789012" \
  --statement-id "AllowCrossAccount" \
  --region us-east-1 \
  --output json
```

## Retry Strategy

| Error | Retry? | Max |
|-------|--------|-----|
| ValidationError | No | 0 |
| ResourceNotFoundException | No | 0 |
| ConcurrentModificationException | Yes | 3 with backoff |
| ThrottlingException | Yes | 3 with backoff |
| InternalException | Yes | 3 with backoff |