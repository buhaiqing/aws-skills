# Repository TODO Tracker

> Auto-generated from codebase audit on 2026-06-12. Update status as items are completed.

---

## HIGH Priority — Charter Violations / Data Integrity

### H1. Broken cross-references to non-existent skills

Delegate names must point to skills that actually exist in this repo (AGENTS.md rule).

| # | Source Skill | Broken Reference | File | Status |
|---|-------------|-----------------|------|--------|
| H1.1 | aws-ec2-ops | `aws-cost-ops` | `aws-ec2-ops/SKILL.md:79` | DONE |
| H1.2 | aws-iam-ops | `aws-cost-ops` | `aws-iam-ops/SKILL.md:68` | DONE |
| H1.3 | aws-s3-ops | `aws-cost-ops` | `aws-s3-ops/SKILL.md:69` | DONE |
| H1.4 | aws-ssm-ops | `aws-cost-ops` | `aws-ssm-ops/SKILL.md:59` | DONE |
| H1.5 | aws-sqs-ops | `aws-kinesis-ops` | `aws-sqs-ops/SKILL.md:60` | DONE |
| H1.6 | aws-vpc-ops | `aws-network-ops` | `aws-vpc-ops/SKILL.md:66` | DONE |
| H1.7 | aws-lambda-ops | `aws-apigateway-ops` | `aws-lambda-ops/SKILL.md:66` | DONE |
| H1.8 | aws-waf-ops | `aws-apigateway-ops` | `aws-waf-ops/SKILL.md:76` | DONE |
| H1.9 | aws-waf-ops | `aws-shield-ops` (marked "future") | `aws-waf-ops/SKILL.md:77` | DONE |

**Fix options**: Either create the missing skill, or change the delegation to reference an existing skill / remove the broken reference.

---

### H2. Missing `## Variable Convention` and non-standard placeholders (C4 violation)

| # | Skill | Issue | File | Status |
|---|-------|-------|------|--------|
| H2.1 | aws-cloudwatch-ops | Uses `## Placeholder Convention` + `{{r.*}}`/`{{u.*}}`/`{{o.*}}` | `aws-cloudwatch-ops/SKILL.md:75` | DONE |
| H2.2 | aws-sns-ops | Uses `## Placeholder Convention` + `{{r.*}}`/`{{u.*}}`/`{{o.*}}` | `aws-sns-ops/SKILL.md:77` | DONE |

**Fix**: Rename section to `## Variable Convention`, change placeholders to `{{env.*}}`/`{{user.*}}`/`{{output.*}}`.

---

### H3. Missing explicit `## Execution Flow Pattern` (Charter flow requirement)

| # | Skill | File | Status |
|---|-------|------|--------|
| H3.1 | aws-cloudwatch-ops | `aws-cloudwatch-ops/SKILL.md` | DONE |
| H3.2 | aws-ssm-ops | `aws-ssm-ops/SKILL.md` | DONE |
| H3.3 | aws-waf-ops | `aws-waf-ops/SKILL.md` | DONE |

**Fix**: Add `## Execution Flow Pattern` with Pre-flight -> Execute -> Validate -> Recover for each operation.

---

### H4. Skills not in AGENTS.md Section 11.5 GCL table (but have GCL files)

| # | Skill | Has rubric.md | Has prompt-templates.md | Status |
|---|-------|-------------|----------------------|--------|
| H4.1 | aws-athena-ops | Yes | Yes | DONE |
| H4.2 | aws-guardduty-ops | Yes | Yes | DONE |
| H4.3 | aws-opensearch-ops | Yes | Yes | DONE |
| H4.4 | aws-ram-ops | Yes | Yes | DONE |
| H4.5 | aws-securityhub-ops | Yes | Yes | DONE |

**Fix**: Add rows to AGENTS.md Section 11.5 Per-Skill Defaults table with appropriate GCL level and max_iter.

---

### H5. Missing rows in README_cn.md

| # | Skill | README.md | README_cn.md | Status |
|---|-------|-----------|--------------|--------|
| H5.1 | aws-aiops-orchestrator | Present (v0.1.0) | Present (v0.1.0) | N/A — false positive, already present |
| H5.2 | aws-athena-ops | Present (v1.0.0) | Present (v1.0.0) | N/A — false positive, already present |

**Fix**: Add corresponding rows to README_cn.md Existing Skills table.

---

## MEDIUM Priority — Consistency / Documentation Drift

### M1. SKILL.md versions not reflected in README tables

AGENTS.md: "README.md and README_cn.md must be kept in sync when version-bumping a skill."

| # | Skill | SKILL.md Version | EN README | CN README | Status |
|---|-------|-----------------|-----------|-----------|--------|
| M1.1 | aws-cloudfront-ops | v1.1.0 | "Complete" | "Complete" | DONE |
| M1.2 | aws-cloudtrail-ops | v1.0.0 | "Complete" | "Complete" | DONE |
| M1.3 | aws-cloudwatch-ops | v2.2.0 | "Complete" | "Complete" | DONE |
| M1.4 | aws-dynamodb-ops | v1.1.0 | "Complete" | "Complete" | DONE |
| M1.5 | aws-ec2-ops | v1.3.0 | "Complete" | "GCL pilot v1.3.0" | DONE |
| M1.6 | aws-eks-ops | v1.0.0 | "Complete" | "Complete" | DONE |
| M1.7 | aws-elasticache-ops | v1.0.0 | "Complete" | "Complete" | DONE |
| M1.8 | aws-elb-ops | v2.2.0 | "Complete" | "Complete" | DONE |
| M1.9 | aws-lambda-ops | v1.1.0 | "Complete" | "Complete" | DONE |
| M1.10 | aws-opensearch-ops | v1.0.0 | "Complete" | "Complete" | DONE |
| M1.11 | aws-rds-ops | v1.1.0 | "Complete" | "Complete" | DONE |
| M1.12 | aws-route53-ops | v1.2.0 | "Complete" | "Complete" | DONE |
| M1.13 | aws-secretsmanager-ops | v1.0.0 | "Complete" | "Complete" | DONE |
| M1.14 | aws-skill-generator | v1.0.0 | "Complete" | "Complete" | DONE |
| M1.15 | aws-sns-ops | v1.1.0 | "Complete" | "Complete" | DONE |
| M1.16 | aws-sqs-ops | v1.1.0 | "Complete" | "Complete" | DONE |
| M1.17 | aws-stepfunctions-ops | v1.1.0 | "Complete" | "Complete" | DONE |
| M1.18 | aws-vpc-ops | v1.3.0 | "Complete" | "Complete" | DONE |

**Fix**: Update both README tables to show actual version numbers from SKILL.md frontmatter.

---

### M2. 28 of 30 skills missing explicit `## Token Efficiency` section (C6)

Per Charter C6, TE-1 through TE-6 must be applied. Only `aws-autoscaling-ops` and `aws-config-ops` have this section explicitly.

| # | Status |
|---|--------|
| M2.1 | DONE — 28 skills updated with `## Token Efficiency` section |

**Fix**: Add `## Token Efficiency` section to each SKILL.md referencing TE-1 through TE-6 compliance.

---

### M3. EC2 version asymmetric between EN and CN READMEs

| # | Detail | Status |
|---|--------|--------|
| M3.1 | EN: no version shown; CN: "GCL pilot v1.3.0" | DONE |

**Fix**: Make both show `v1.3.0` consistently.

---

### M4. aws-aiops-orchestrator version mismatch

| # | Detail | Status |
|---|--------|--------|
| M4.1 | SKILL.md: `0.1.0-design`, README.md: `v0.1.0` | DONE |

**Fix**: Align to one version. Decide if `-design` suffix is kept or dropped.

---

## LOW Priority — Nice-to-Have / Cosmetic

### L1. aws-skill-generator listed as GCL "optional" but missing rubric.md/prompt-templates.md

| # | Detail | Status |
|---|--------|--------|
| L1.1 | Listed in AGENTS.md §11.5 as optional (max_iter=3) but has no GCL files | WONTFIX — meta-skill that scaffolds other skills; GCL not applicable |

---

### L2. aws-aiops-orchestrator missing standard reference files

| # | Missing File | Status |
|---|-------------|--------|
| L2.1 | aws-cli-usage.md | WONTFIX — meta-skill delegates; no CLI/SDK operations |
| L2.2 | boto3-sdk-usage.md | WONTFIX — meta-skill delegates; no CLI/SDK operations |
| L2.3 | core-concepts.md | WONTFIX — meta-skill delegates; no CLI/SDK operations |
| L2.4 | troubleshooting.md | WONTFIX — meta-skill delegates; no CLI/SDK operations |

---

### L3. Multiple SKILL.md files use `---` horizontal rules in body

Can confuse naive frontmatter parsers. Files with the most `---` usage:

| # | Skill | `---` Count | Status |
|---|-------|-----------|--------|
| L3.1 | aws-elb-ops | 12 | DONE (10 replaced with ***) |
| L3.2 | aws-waf-ops | 10 | DONE (9 replaced with ***) |
| L3.3 | aws-acm-ops | 8 | DONE (6 replaced with ***) |

**Fix**: Consider replacing body `---` with `***` or `___` to avoid ambiguity with frontmatter delimiters.

---

## Progress Summary

| Priority | Total | Done | Remaining |
|----------|-------|------|-----------|
| HIGH     | 21    | 21   | 0        |
| MEDIUM   | 22    | 22   | 0        |
| LOW      | 8     | 8    | 0         |
| **Total** | **51** | **51** | **0** |

---

*Last updated: 2026-06-12 (ALL 51 items resolved — 21 HIGH + 22 MEDIUM + 8 LOW)*
