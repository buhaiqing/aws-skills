# Core Concepts — EventBridge

## What is EventBridge

- **Purpose**: Serverless event bus for connecting AWS services, SaaS partners, and custom apps
- **Category**: Application Integration
- **Console**: https://console.aws.amazon.com/events/
- **Docs**: https://docs.aws.amazon.com/eventbridge/latest/userguide/

## EventBridge Components

| Component | Description |
|-----------|-------------|
| **Event Bus** | Router that receives and delivers events. Accounts have `default` bus; can create custom buses |
| **Rule** | Matches incoming events and routes to targets. Can use event pattern or schedule expression |
| **Target** | Destination for matched events (Lambda, SQS, SNS, Step Functions, API Gateway, etc.) |
| **Connection** | Stores authorization config (API Key, Basic, OAuth) for API destinations |
| **API Destination** | HTTP endpoint target using a connection for auth |
| **Archive** | Stores events from a bus for later replay |
| **Replay** | Replays events from an archive to a bus |
| **Schedule** | (Scheduler) Triggers targets on a cron/rate schedule, separate from EventBridge rules |
| **Pipe** | (Pipes) Point-to-point integration from source → enrichment → target, no code needed |

## Architecture

```
Event Sources (AWS services, SaaS, custom) → Event Bus → Rules (filter)
                                                              ↓
                                                          Targets
                                                    (Lambda, SQS, SNS,
                                                     Step Functions, HTTP)

Schedule Expression → Rule → Target
                    OR
Schedule (Scheduler) → Target

Source → Pipe → (Enrichment) → Target
```

## Rule Types

| Type | Trigger | Example |
|------|---------|---------|
| Event Pattern | Match event structure | `{"source": ["aws.ec2"], "detail-type": ["EC2 Instance State-change Notification"]}` |
| Schedule Expression | Time-based | `rate(5 minutes)` or `cron(0 9 ? * MON-FRI *)` |

## Common Event Patterns

```json
{"source": ["aws.ec2"]}
{"source": ["aws.s3"], "detail-type": ["Object Created"]}
{"source": ["aws.codebuild"], "detail-type": ["CodeBuild Build State Change"], "detail": {"build-status": ["FAILED"]}}
{"source": ["aws.health"], "detail-type": ["AWS Health Event"]}
```

## Support Targets (Use API for current limits)

```bash
# Default target limit per rule is 5 (adjustable up to 100)
# Check current quotas:
aws service-quotas get-service-quota \
  --service-code events \
  --quota-code L-8179BFB3 \
  --region "{{user.region}}" --output json
```

| Target Type | Default per rule |
|-------------|-----------------|
| Lambda, SQS, SNS, Step Functions, Event Bus, Kinesis, Logs | 5 each |
| API Destination | 1 |

## Quotas (Use API for current values)

```bash
# List all EventBridge quotas:
aws service-quotas list-service-quotas --service-code events --region "{{user.region}}" --output json

# Key quotas (defaults, check API for current):
# Rules per bus: 300 | Targets per rule: 5 (up to 100)
# Event buses per account: 100 | Schedules per account: 1,000
# Pipes per account: 100 | Archive retention: 7–1200 days
```

## Pricing

See [AWS EventBridge Pricing](https://aws.amazon.com/eventbridge/pricing/) for current rates. Key components:
- Custom event ingestion: per million events
- Cross-account/region events: per million events
- API destinations: per million invocations
- Archives: per GB/month
- Scheduler: per million invocations
- Pipes: free (pay for downstream resources)

## Best Practices

- Use `default` bus for AWS service events; create custom buses for application events
- Always specify `event-pattern` precisely to avoid unintended invocations
- Set DLQ (Dead Letter Queue) on critical event targets
- Use `InputPath` or `InputTransformer` to filter event data before sending to targets
- Enable archive for mission-critical event buses for replay capability
- Use Scheduler for simple time-based triggers; use EventBridge rules for event-driven patterns
- Tag rules and buses for cost allocation and management