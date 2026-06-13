#!/usr/bin/env python3
"""Generate IAM trust policy JSON for GitHub Actions or GitLab CI OIDC (read-only cruise role)."""

from __future__ import annotations

import argparse
import json
import sys


def github_trust(account_id: str, repo: str, ref: str, ref_type: str) -> dict:
    sub = f"repo:{repo}:ref:refs/{ref_type}/{ref}"
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Federated": f"arn:aws:iam::{account_id}:oidc-provider/token.actions.githubusercontent.com"
                },
                "Action": "sts:AssumeRoleWithWebIdentity",
                "Condition": {
                    "StringEquals": {"token.actions.githubusercontent.com:aud": "sts.amazonaws.com"},
                    "StringLike": {"token.actions.githubusercontent.com:sub": sub},
                },
            }
        ],
    }


def gitlab_trust(
    account_id: str,
    project_path: str,
    ref: str,
    ref_type: str,
    gitlab_host: str,
) -> dict:
    sub = f"project_path:{project_path}:ref_type:{ref_type}:ref:{ref}"
    aud = f"https://{gitlab_host}"
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Federated": f"arn:aws:iam::{account_id}:oidc-provider/{gitlab_host}"},
                "Action": "sts:AssumeRoleWithWebIdentity",
                "Condition": {
                    "StringEquals": {f"{gitlab_host}:aud": aud},
                    "StringLike": {f"{gitlab_host}:sub": sub},
                },
            }
        ],
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Generate OIDC IAM trust policy for AIOps cruise CI")
    p.add_argument("--provider", choices=("github", "gitlab"), required=True)
    p.add_argument("--account-id", required=True, help="AWS account ID (12 digits)")
    p.add_argument("--ref", default="main", help="Branch or tag name")
    p.add_argument("--ref-type", choices=("branch", "tag"), default="branch")
    p.add_argument("--repo", default="", help="GitHub repo org/name (github provider)")
    p.add_argument("--project-path", default="", help="GitLab project path group/project (gitlab provider)")
    p.add_argument("--gitlab-host", default="gitlab.com", help="GitLab OIDC host (self-hosted: gitlab.example.com)")
    p.add_argument("--output", default="", help="Write JSON to file (default: stdout)")
    args = p.parse_args()

    if args.provider == "github":
        if not args.repo:
            print("[ERROR] --repo required for github (e.g. myorg/aws-skills)", file=sys.stderr)
            return 2
        policy = github_trust(args.account_id, args.repo, args.ref, args.ref_type)
    else:
        if not args.project_path:
            print("[ERROR] --project-path required for gitlab", file=sys.stderr)
            return 2
        policy = gitlab_trust(
            args.account_id, args.project_path, args.ref, args.ref_type, args.gitlab_host
        )

    text = json.dumps(policy, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"Wrote {args.output}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
