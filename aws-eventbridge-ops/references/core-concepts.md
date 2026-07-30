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

## Quotas and Targets (query live — TE-1)

Never hardcode limits. Resolve via Service Quotas before create/scale:

```bash
# All EventBridge (events) quotas
aws service-quotas list-service-quotas \
  --service-code events --region "{{user.region}}" --output json

# Targets per rule (quota code may vary by account — prefer list + filter)
aws service-quotas get-service-quota \
  --service-code events --quota-code L-8179BFB3 \
  --region "{{user.region}}" --output json

# Scheduler / Pipes quotas (separate service codes)
aws service-quotas list-service-quotas \
  --service-code scheduler --region "{{user.region}}" --output json
aws service-quotas list-service-quotas \
  --service-code pipes --region "{{user.region}}" --output json
```

Pricing: [AWS EventBridge Pricing](https://aws.amazon.com/eventbridge/pricing/).

## Best Practices

- `default` bus for AWS service events; custom buses for app events
- Precise `event-pattern`; DLQ on critical targets; `InputPath` / `InputTransformer` to shrink payloads
- Archive mission-critical buses; prefer Scheduler for pure cron, rules for event-driven
- Tag rules/buses for cost allocation
