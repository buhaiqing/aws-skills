# boto3 SDK Usage — ACM

## Client Setup

```python
import boto3
from datetime import datetime, timedelta
from dateutil import parser

# Standard client
client = boto3.client('acm', region_name='us-east-1')
```

## Common Patterns

### Request Certificate (DNS Validation)

```python
response = client.request_certificate(
    DomainName='example.com',
    ValidationMethod='DNS',
    SubjectAlternativeNames=['www.example.com'],
    Tags=[{'Key': 'AIOps', 'Value': 'true'}]
)
cert_arn = response['CertificateArn']
print(f"Certificate requested: {cert_arn}")
```

### Describe Certificate

```python
response = client.describe_certificate(CertificateArn=cert_arn)
cert = response['Certificate']
print(f"Status: {cert['Status']}")
print(f"Expires: {cert['NotAfter']}")
print(f"Type: {cert['Type']}")
print(f"In use by: {cert.get('InUseBy', [])}")
```

### Get Validation DNS Records

```python
response = client.describe_certificate(CertificateArn=cert_arn)
for option in response['Certificate']['DomainValidationOptions']:
    record = option.get('ResourceRecord')
    if record:
        print(f"Domain: {option['DomainName']}")
        print(f"  Record: {record['Name']} {record['Type']} → {record['Value']}")
```

### List All Certificates (Paginated)

```python
certificates = []
paginator = client.get_paginator('list_certificates')
for page in paginator.paginate(CertificateStatuses=['ISSUED']):
    certificates.extend(page['CertificateSummaryList'])

for cert in certificates:
    desc = client.describe_certificate(CertificateArn=cert['CertificateArn'])
    c = desc['Certificate']
    print(f"{c['DomainName']:30s} expires: {c['NotAfter']}")
```

### Delete Certificate

```python
# Safety: Check InUseBy first
desc = client.describe_certificate(CertificateArn=cert_arn)
in_use = desc['Certificate'].get('InUseBy', [])
if in_use:
    print(f"WARNING: Certificate in use by: {in_use}")
    # Require user confirmation before continuing

client.delete_certificate(CertificateArn=cert_arn)
print("Certificate deleted")
```

## AIOps: Expiry Monitoring

### Get Days Until Expiry

```python
def days_until_expiry(cert_arn: str) -> int:
    """Calculate days until certificate expiry"""
    response = client.describe_certificate(CertificateArn=cert_arn)
    expires = parser.parse(response['Certificate']['NotAfter'])
    remaining = (expires - datetime.now(expires.tzinfo)).days
    return remaining
```

### Certificate Health Audit

```python
def audit_certificates(regions: list[str]) -> dict:
    """Audit certificate health across multiple regions
    
    Returns summary with expiring dates and risk categories
    """
    results = {
        'total': 0,
        'expiring_30d': [],
        'expiring_7d': [],
        'expired': [],
        'unused': []
    }
    
    for region in regions:
        client = boto3.client('acm', region_name=region)
        paginator = client.get_paginator('list_certificates')
        
        for page in paginator.paginate(CertificateStatuses=['ISSUED']):
            for cert_summary in page['CertificateSummaryList']:
                results['total'] += 1
                cert = client.describe_certificate(
                    CertificateArn=cert_summary['CertificateArn']
                )['Certificate']
                
                days = days_until_expiry(cert_summary['CertificateArn'])
                in_use = len(cert.get('InUseBy', []))
                
                if days < 0:
                    results['expired'].append(cert['DomainName'])
                elif days < 7:
                    results['expiring_7d'].append({
                        'domain': cert['DomainName'],
                        'region': region,
                        'days': days
                    })
                elif days < 30:
                    results['expiring_30d'].append({
                        'domain': cert['DomainName'],
                        'region': region,
                        'days': days
                    })
                
                if in_use == 0:
                    results['unused'].append({
                        'domain': cert['DomainName'],
                        'region': region
                    })
    
    return results

# Usage
regions = ['us-east-1', 'us-west-2', 'eu-west-1']
audit = audit_certificates(regions)
print(f"Total: {audit['total']}")
print(f"Expired: {audit['expired']}")
print(f"Expiring in 7 days: {audit['expiring_7d']}")
print(f"Expiring in 30 days: {audit['expiring_30d']}")
print(f"Unused: {audit['unused']}")
```

### Force Renewal Check

```python
def check_and_renew(cert_arn: str) -> str:
    """Check renewal status and trigger if needed
    
    Returns status message
    """
    response = client.describe_certificate(CertificateArn=cert_arn)
    cert = response['Certificate']
    
    if cert['Status'] != 'ISSUED':
        return f"Certificate not in ISSUED state: {cert['Status']}"
    
    days = days_until_expiry(cert_arn)
    renewal = cert.get('RenewalEligibility', 'INELIGIBLE')
    
    if renewal == 'ELIGIBLE' and days < 30:
        client.renew_certificate(CertificateArn=cert_arn)
        return f"Renewal triggered. Domain: {cert['DomainName']}, Days remaining: {days}"
    elif renewal != 'ELIGIBLE':
        return f"Not eligible for renewal. Type: {cert['Type']}, Renewal: {renewal}"
    else:
        return f"Renewal not needed yet. Days remaining: {days}"
```

## Error Handling

```python
import botocore.exceptions

try:
    response = client.request_certificate(
        DomainName='example.com',
        ValidationMethod='DNS'
    )
except botocore.exceptions.ClientError as e:
    code = e.response['Error']['Code']
    message = e.response['Error']['Message']
    
    if code == 'LimitExceededException':
        print(f"Certificate quota exceeded: {message}")
    elif code == 'InvalidDomainValidationOptionsException':
        print(f"Invalid domain: {message}")
    elif code == 'TooManyTagsException':
        print(f"Too many tags: {message}")
    else:
        print(f"Error {code}: {message}")
```

## Common Patterns

| Operation | Method | Key Parameters |
|-----------|--------|---------------|
| Request | `request_certificate()` | DomainName, ValidationMethod, SubjectAlternativeNames |
| Describe | `describe_certificate()` | CertificateArn |
| List | `list_certificates()` | CertificateStatuses, Pagination |
| Delete | `delete_certificate()` | CertificateArn |
| Renew | `renew_certificate()` | CertificateArn |
| Import | `import_certificate()` | Certificate, PrivateKey, CertificateChain |
| Get | `get_certificate()` | CertificateArn |
