# Cross-Account STS AssumeRole Setup Guide

This skill's `scan-topo` and `export-hcl` commands support `--assume-role` parameter for cross-account resource scanning via STS AssumeRole.

## Prerequisites

1. Target account has a role with a trust policy allowing the source account to assume it
2. Role has at least `ReadOnlyAccess` policy attached
3. Current account's AK is configured (via environment variables)

## Role Trust Policy Template

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Principal": {
        "AWS": "arn:aws:iam::<source-account-id>:root"
      },
      "Condition": {}
    }
  ]
}
```

## Usage

```bash
# Single account mode (default)
./topo-scan.sh

# Cross-account mode
./topo-scan.sh --assume-role arn:aws:iam::123456789012:role/TopologyReader

# With session name and duration
export-hcl.py --scope all \
    --assume-role arn:aws:iam::123456789012:role/TopologyReader \
    --session-name "my-scan" \
    --duration 7200 \
    --output-dir ./hcl-export/
```

## Security Constraints

- Temporary credentials are **never** written to manifest.json, logs, or output files
- Credentials exist only in script memory, discarded after execution
- On failure: HALT, never fall back to primary credentials
- Role MUST have strictly `ReadOnlyAccess` permissions

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `AccessDenied` on AssumeRole | Role trust policy or permissions | Check role ARN, trust policy, and attached policies |
| `InvalidIdentityToken` | STS token expired or invalid | Re-authenticate and retry |
| `MalformedPolicyDocument` | Trust policy syntax error | Fix the trust policy JSON |
| `Credentials not set` | Primary AK not configured | Set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` |
