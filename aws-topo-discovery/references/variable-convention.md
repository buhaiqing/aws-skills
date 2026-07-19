# Variable Convention

| Placeholder | Meaning | Source |
|-------------|---------|--------|
| `{{env.AWS_ACCESS_KEY_ID}}` | AK ID | From runtime env, NEVER ask user |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | AK Secret | From runtime env, NEVER exposed |
| `{{env.AWS_DEFAULT_REGION}}` | Region | From runtime env |
| `{{env.AWS_SESSION_TOKEN}}` | Session Token | From runtime env, for STS temporary credentials |
| `{{env.AWS_PROFILE}}` | Named Profile | From runtime env, overrides explicit keys |
| `{{user.report_mode}}` | Brief/Detailed | User decision (step 1) |
| `{{user.topology_format}}` | ASCII/Mermaid | User decision (step 2) |
| `{{user.output_structure}}` | Single-file/Multi-file | User decision (step 3) |
| `{{user.project_name}}` | Project name | User input or extracted from VPC name |
| `{{output.topology_data}}` | Scan results | From CLI execution |
| `{{output.vpc_name}}` | VPC name | From DescribeVpcs response |
