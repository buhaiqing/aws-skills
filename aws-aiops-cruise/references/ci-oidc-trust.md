# CI/CD — OIDC trust policy generator

Generate IAM **AssumeRoleWithWebIdentity** trust policies for the read-only cruise role.

## GitHub Actions

1. Create OIDC provider: `token.actions.githubusercontent.com` (audience `sts.amazonaws.com`)
2. Generate trust policy:

```bash
python3 aws-aiops-cruise/runbooks/scripts/generate-oidc-trust-policy.py \
  --provider github \
  --account-id 123456789012 \
  --repo myorg/aws-skills \
  --ref main \
  --output trust-github.json
```

3. Attach to IAM role used by [`github-actions-cruise.yml`](../assets/ci-cd-templates/github-actions-cruise.yml) (`AWS_CRUISE_ROLE_ARN`)

## GitLab CI

1. Create OIDC provider: `gitlab.com` (or self-hosted host)
2. Generate trust policy:

```bash
python3 aws-aiops-cruise/runbooks/scripts/generate-oidc-trust-policy.py \
  --provider gitlab \
  --account-id 123456789012 \
  --project-path mygroup/aws-skills \
  --ref main \
  --output trust-gitlab.json
```

3. Use with [`gitlab-ci-cruise-oidc.yml`](../assets/ci-cd-templates/gitlab-ci-cruise-oidc.yml)

Self-hosted GitLab:

```bash
python3 aws-aiops-cruise/runbooks/scripts/generate-oidc-trust-policy.py \
  --provider gitlab \
  --account-id 123456789012 \
  --project-path mygroup/aws-skills \
  --gitlab-host gitlab.example.com \
  --ref main
```

## Role permissions

Attach **ReadOnlyAccess** or a custom policy scoped to cruise APIs. Never attach admin policies to CI patrol roles.

## See also

- [`gitlab-oidc-integration.md`](gitlab-oidc-integration.md) — GitLab pipeline variables and flow
- [`github-actions-cruise.yml`](../assets/ci-cd-templates/github-actions-cruise.yml)
