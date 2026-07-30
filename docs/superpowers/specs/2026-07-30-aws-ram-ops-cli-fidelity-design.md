# Design: aws-ram-ops CLI fidelity + TE cleanup

**Date:** 2026-07-30  
**Scope:** Fix factual CLI errors and token-waste in `aws-ram-ops` references; add golden scenarios.

## Problem (disk-verified)

1. `replace-permission-associations` documented with `--resource-share-arn` — API has no such param; call is **account-wide**.
2. `list-resources` missing required `--resource-owner SELF|OTHER-ACCOUNTS` in examples.
3. Fabricated/unverified permission names (`AmazonEC2SubnetShare`, `AmazonVPCSubnetReadOnlyAccess`); AWS default for subnet is `AWSRAMDefaultPermissionSubnet`.
4. Scenario 4 “只读” `create-permission` includes `CreateNetworkInterface`.
5. `prompt-examples.md` (~331 lines) duplicates `aws-cli-usage.md` / `integration.md`.
6. No `golden-scenarios.yaml` (L4 §16).
7. `boto3` `list_resources` missing `resourceOwner`; `get-resource-share-associations --association-type RESOURCE_SHARE` invalid (`PRINCIPAL`|`RESOURCE` only).
8. Consumer verify path in `integration.md` uses `SELF` after accept — should be `OTHER-ACCOUNTS`.

## Out of scope

- Splitting `operations.md` (425 lines) into multiple files.
- Version bump / README sync (doc-fix only unless SKILL.md changes).

## Acceptance

- [ ] No `--resource-share-arn` on `replace-permission-associations`; per-share change uses `associate-resource-share-permission --replace`.
- [ ] Every `list-resources` / `list_resources` includes `resource-owner` / `resourceOwner`.
- [ ] Subnet default permission = `AWSRAMDefaultPermissionSubnet`; RO via `list-permissions` or CMP with Describe-only.
- [ ] `prompt-examples.md` ≤ ~200 lines; scenarios keep 流程; CLI bodies link to `aws-cli-usage.md`.
- [ ] `golden-scenarios.yaml` ≥5 covering read / confirmed destructive / missing confirm.
