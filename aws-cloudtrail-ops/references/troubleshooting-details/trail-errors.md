# CloudTrail Trail Errors — Detailed Recovery

## TrailAlreadyExists

Trail name exists in region.

```bash
# Check existing trails
aws cloudtrail describe-trails --trail-name-list {{trail_name}}

# Use different name or update
aws cloudtrail update-trail --name {{trail_name}} ...
```

## TrailNotFound

Deleted/wrong name/wrong region.

```bash
# List all trails
aws cloudtrail describe-trails --output json

# Check specific region
aws cloudtrail describe-trails --trail-name-list {{trail_name}} --region {{region}}

# Trail might be in different home region
aws cloudtrail describe-trails --query "trailList[?Name=='{{trail_name}}']"
```

## InvalidTrailName

Name doesn't meet requirements: 3-128 chars, alphanumeric/underscore/hyphen/period, unique per region.
