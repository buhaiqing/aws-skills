# Integration Setup — Auto Scaling

Uses the same environment setup as all AWS skills. See
[aws-skill-generator/references/integration.md](../../aws-skill-generator/references/integration.md)
for full setup instructions.

## Additional IAM Permissions

The IAM role or user needs these permissions for Auto Scaling operations:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "autoscaling:*",
        "ec2:DescribeLaunchTemplateVersions",
        "ec2:DescribeSubnets",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeInstanceTypes",
        "elasticloadbalancing:DescribeTargetGroups",
        "elasticloadbalancing:DescribeLoadBalancers",
        "cloudwatch:DescribeAlarms"
      ],
      "Resource": "*"
    }
  ]
}
```

## Service-linked Role

Auto Scaling automatically creates a service-linked role:
`AWSServiceRoleForAutoScaling`

This role handles lifecycle hook notifications, CloudWatch alarms, and ELB
registration. If missing, create it:

```bash
aws iam create-service-linked-role \
  --aws-service-name autoscaling.amazonaws.com \
  --output json
```