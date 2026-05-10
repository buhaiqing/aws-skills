# AWS CLI Usage - Route53

AWS CLI commands for Route53 operations. All commands use `--output json`.

## Hosted Zone Operations

### Create Hosted Zone
```bash
aws route53 create-hosted-zone \
  --name {{user.ZoneName}} \
  --caller-reference {{user.CallerReference}} \
  --vpc VPCRegion={{user.Region}},VPCId={{user.VPCId}} \
  --hosted-zone-config Comment="{{user.Comment}}",PrivateZone=true \
  --output json
```

**JSON paths:**
- `.HostedZone.Id` → /hostedzone/Z123456789
- `.HostedZone.Name` → zone name
- `.DelegationSet.NameServers[]` → name servers

### Get Hosted Zone
```bash
aws route53 get-hosted-zone \
  --id {{user.ZoneId}} \
  --output json
```

### List Hosted Zones
```bash
aws route53 list-hosted-zones \
  --max-items 100 \
  --output json
```

### Delete Hosted Zone
```bash
aws route53 delete-hosted-zone \
  --id {{user.ZoneId}} \
  --output json
```

## Record Set Operations

### List Resource Record Sets
```bash
aws route53 list-resource-record-sets \
  --hosted-zone-id {{user.ZoneId}} \
  --output json
```

### Change Resource Record Sets
```bash
# Create or update record
aws route53 change-resource-record-sets \
  --hosted-zone-id {{user.ZoneId}} \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "{{user.RecordName}}",
        "Type": "{{user.RecordType}}",
        "TTL": {{user.TTL}},
        "ResourceRecords": [{"Value": "{{user.RecordValue}}"}]
      }
    }]
  }' \
  --output json
```

**JSON paths:**
- `.ChangeInfo.Id` → change ID
- `.ChangeInfo.Status` → PENDING or INSYNC

### Delete Record Set
```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id {{user.ZoneId}} \
  --change-batch '{
    "Changes": [{
      "Action": "DELETE",
      "ResourceRecordSet": {
        "Name": "{{user.RecordName}}",
        "Type": "{{user.RecordType}}",
        "TTL": {{user.TTL}},
        "ResourceRecords": [{"Value": "{{user.RecordValue}}"}]
      }
    }]
  }' \
  --output json
```

## Health Check Operations

### Create Health Check
```bash
aws route53 create-health-check \
  --caller-reference {{user.CallerReference}} \
  --health-check-config '{
    "IPAddress": "{{user.IPAddress}}",
    "Port": {{user.Port}},
    "Type": "{{user.CheckType}}",
    "ResourcePath": "{{user.Path}}",
    "FullyQualifiedDomainName": "{{user.FQDN}}",
    "RequestInterval": 30,
    "FailureThreshold": 3
  }' \
  --output json
```

### Get Health Check
```bash
aws route53 get-health-check \
  --health-check-id {{user.HealthCheckId}} \
  --output json
```

### Update Health Check
```bash
aws route53 update-health-check \
  --health-check-id {{user.HealthCheckId}} \
  --ip-address {{user.NewIP}} \
  --port {{user.NewPort}} \
  --resource-path {{user.NewPath}} \
  --output json
```

### Delete Health Check
```bash
aws route53 delete-health-check \
  --health-check-id {{user.HealthCheckId}} \
  --output json
```

## Test DNS Answer
```bash
aws route53 test-dns-answer \
  --hosted-zone-id {{user.ZoneId}} \
  --record-name {{user.RecordName}} \
  --record-type {{user.RecordType}} \
  --output json
```

## Common Options

```bash
--hosted-zone-id {{user.ZoneId}}  # Hosted zone ID
--name {{user.Name}}              # Record name
--type {{user.Type}}              # A, AAAA, CNAME, MX, TXT, etc.
--ttl {{user.TTL}}                # Time to live in seconds
--action UPSERT|CREATE|DELETE     # Change action
```

## Routing Policies

### Simple Routing
```json
{
  "Name": "simple.example.com",
  "Type": "A",
  "TTL": 300,
  "ResourceRecords": [{"Value": "1.2.3.4"}]
}
```

### Failover Routing
```json
{
  "Name": "failover.example.com",
  "Type": "A",
  "Failover": "PRIMARY",
  "TTL": 60,
  "ResourceRecords": [{"Value": "1.2.3.4"}],
  "HealthCheckId": "{{health-check-id}}"
}
```

### Weighted Routing
```json
{
  "Name": "weighted.example.com",
  "Type": "A",
  "SetIdentifier": "server-1",
  "Weight": 70,
  "TTL": 60,
  "ResourceRecords": [{"Value": "1.2.3.4"}]
}
```

### Latency-based Routing
```json
{
  "Name": "latency.example.com",
  "Type": "A",
  "SetIdentifier": "us-east-1",
  "Region": "us-east-1",
  "TTL": 60,
  "ResourceRecords": [{"Value": "1.2.3.4"}]
}
```

### Geolocation Routing
```json
{
  "Name": "geo.example.com",
  "Type": "A",
  "SetIdentifier": "us-location",
  "GeoLocation": {"CountryCode": "US"},
  "TTL": 60,
  "ResourceRecords": [{"Value": "1.2.3.4"}]
}
```