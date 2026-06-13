# GitLab OIDC → AWS AssumeRole (AIOps Cruise)

Use **`assets/ci-cd-templates/gitlab-ci-cruise-oidc.yml`** when GitLab CI should assume an AWS role without long-lived access keys.

Generate trust policy: `python3 runbooks/scripts/generate-oidc-trust-policy.py --provider gitlab ...` — see [`ci-oidc-trust.md`](ci-oidc-trust.md).

## GitLab CI variables

| Variable | Required | Notes |
|----------|----------|-------|
| `AWS_CRUISE_ROLE_ARN` | yes | ReadOnly cruise role |
| `AWS_CRUISE_RESOURCE_GROUP` | yes | Patrol scope |
| `CRUISE_REGION` | no | Default `us-east-1` |
| `GITLAB_OIDC_AUD` | no | Token audience; default `https://gitlab.com` |

## IAM OIDC provider (GitLab.com)

Create identity provider:

- **Provider URL**: `https://gitlab.com`
- **Audience**: `https://gitlab.com` (must match `GITLAB_OIDC_AUD` / `id_tokens.aud`)

## Trust policy example (single project)

Replace account, project path, and branch as needed:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::123456789012:oidc-provider/gitlab.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "gitlab.com:aud": "https://gitlab.com"
        },
        "StringLike": {
          "gitlab.com:sub": "project_path:mygroup/aws-skills:ref_type:branch:ref:main"
        }
      }
    }
  ]
}
```

Attach **ReadOnlyAccess** (or tighter custom policy) to the role. Cruise is read-only; never attach PowerUser/Admin.

## Self-hosted GitLab

- OIDC provider URL: `https://gitlab.example.com`
- Set `GITLAB_OIDC_AUD` and `id_tokens.GITLAB_OIDC_TOKEN.aud` to your issuer audience
- Trust policy `sub` condition uses your instance hostname in the condition keys (see GitLab AWS OIDC docs)

## Pipeline flow

```
id_tokens.GITLAB_OIDC_TOKEN
  → aws sts assume-role-with-web-identity
  → export session creds
  → daily-health-check.py --render-topology
  → artifacts: cruise + topology
```

## Fallback

Long-lived keys: use [`gitlab-ci-cruise.yml`](../assets/ci-cd-templates/gitlab-ci-cruise.yml) with `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` CI variables (not recommended for production).
