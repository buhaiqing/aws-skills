# AWS CLI Usage - Route53

AWS CLI commands for Route53 operations. All commands use `--output json`.

## Common JSON Paths (Centralized)

```
# Create Zone:     .HostedZone.Id  (strip "/hostedzone/" prefix)
#                  .DelegationSet.NameServers[]
# List Zones:      .HostedZones[].{Id,Name,ResourceRecordSetCount}
# Change Record:   .ChangeInfo.{Id,Status}
# List Records:    .ResourceRecordSets[].{Name,Type,TTL,ResourceRecords}
# Create HC:       .HealthCheck.Id
# Test DNS:        .TestResult
```

## Hosted Zone Operations

### Create Hosted Zone
```bash
aws route53 create-hosted-zone \
  --name {{user.ZoneName}} \
  --caller-reference {{user.CallerReference}} \
  --hosted-zone-config Comment="{{user.Comment}}"
```

### Get Hosted Zone
```bash
aws route53 get-hosted-zone --id {{user.ZoneId}}
```

### List Hosted Zones
```bash
aws route53 list-hosted-zones --max-items 100
```

### Delete Hosted Zone
```bash
aws route53 delete-hosted-zone --id {{user.ZoneId}}
```

## Record Set Operations

### List Resource Record Sets
```bash
aws route53 list-resource-record-sets --hosted-zone-id {{user.ZoneId}}
```

### Change Resource Record Sets (UPSERT)
```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id {{user.ZoneId}} \
  --change-batch '{
    "Changes":[{"Action":"UPSERT","ResourceRecordSet":{"Name":"{{user.RecordName}}","Type":"{{user.RecordType}}","TTL":{{user.TTL}},"ResourceRecords":[{"Value":"{{user.RecordValue}}"}]}}]
  }'
```

### Delete Record Set
```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id {{user.ZoneId}} \
  --change-batch '{
    "Changes":[{"Action":"DELETE","ResourceRecordSet":{"Name":"{{user.RecordName}}","Type":"{{user.RecordType}}","TTL":{{user.TTL}},"ResourceRecords":[{"Value":"{{user.RecordValue}}"}]}}]
  }'
```

## Health Check Operations

### Create Health Check
```bash
aws route53 create-health-check \
  --caller-reference {{user.CallerReference}} \
  --health-check-config '{"IPAddress":"{{user.IPAddress}}","Port":{{user.Port}},"Type":"{{user.CheckType}}","ResourcePath":"{{user.Path}}","FailureThreshold":3}'
```

### Get/Update/Delete Health Check
```bash
aws route53 get-health-check --health-check-id {{user.HealthCheckId}}
aws route53 update-health-check --health-check-id {{user.HealthCheckId}} --port {{user.NewPort}}
aws route53 delete-health-check --health-check-id {{user.HealthCheckId}}
```

## Test DNS Answer
```bash
aws route53 test-dns-answer \
  --hosted-zone-id {{user.ZoneId}} \
  --record-name {{user.RecordName}} \
  --record-type {{user.RecordType}}
```

## Routing Policy Examples

### Failover (Primary)
```json
{"Name":"failover.example.com","Type":"A","Failover":"PRIMARY","TTL":60,"ResourceRecords":[{"Value":"1.2.3.4"}],"HealthCheckId":"{{id}}"}
```

### Weighted
```json
{"Name":"weighted.example.com","Type":"A","SetIdentifier":"server-1","Weight":70,"TTL":60,"ResourceRecords":[{"Value":"1.2.3.4"}]}
```

### Latency-based
```json
{"Name":"latency.example.com","Type":"A","SetIdentifier":"us-east-1","Region":"us-east-1","TTL":60,"ResourceRecords":[{"Value":"1.2.3.4"}]}
```

### Geolocation
```json
{"Name":"geo.example.com","Type":"A","SetIdentifier":"us","GeoLocation":{"CountryCode":"US"},"TTL":60,"ResourceRecords":[{"Value":"1.2.3.4"}]}
```