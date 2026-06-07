# Integration Setup — EventBridge

See: `aws-skill-generator/references/integration.md` for general setup.

## IAM Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "events:*",
      "scheduler:*",
      "pipes:*",
      "iam:PassRole"
    ],
    "Resource": "*"
  }]
}
```

## Scheduler Service Role

EventBridge Scheduler needs a role with `iam:PassRole` to invoke targets:

```bash
aws iam create-role \
  --role-name AWSServiceRoleForScheduler \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"scheduler.amazonaws.com"},"Action":"sts:AssumeRole"}]}' \
  --output json
```