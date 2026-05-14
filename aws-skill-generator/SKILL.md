---
name: aws-skill-generator
description: >-
  Use when the user wants to create a new AWS cloud operational skill, scaffold
  AWS service capabilities, or update an existing AWS skill after API changes
  — even without explicitly using words like "skill," "scaffold," or "generator."
  Generates complete skill structure from AWS documentation, CLI references,
  and boto3 SDK. NOT for executing live AWS operations.
license: MIT
compatibility: >-
  Access to AWS official documentation, AWS CLI docs, boto3 SDK references,
  aws-skill-generator/references/aws-skill-template.md, and agentskills.io
  frontmatter conventions.
metadata:
  author: aws
  version: "1.0.0"
  last_updated: "2026-05-10"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  type: meta-skill
---

# AWS Skill Generator (Meta-Skill)

## What This Skill Does

This **meta-skill** scaffolds new AWS operational skills (`aws-[service]-ops`) for this repository. It does NOT execute live AWS operations—use the generated skills for that.

## When to Use

| Use This Skill | Do NOT Use |
|----------------|------------|
| Creating a new AWS service skill | Executing AWS operations directly |
| Aligning existing skill to template | Billing-only or IAM-only tasks |
| Updating skill after AWS API changes | Non-AWS cloud work |

## Generation Process Overview

```
Input → Analyze Sources → Create Layout → Populate Files → Verify
```

## Quick Start Checklist

### P0 — MUST Complete
- [ ] Product name + primary resource type identified
- [ ] Official AWS docs URL provided
- [ ] AWS CLI support verified (`aws [service] help`)
- [ ] SDK (boto3) module identified
- [ ] Trigger & Scope with SHOULD/SHOULD-NOT defined
- [ ] `{{env.*}}` placeholders (no secret literals)
- [ ] Execution flows: Pre-flight → Execute → Validate → Recover
- [ ] Safety gates for destructive operations
- [ ] Dual-path: AWS CLI (primary) + boto3 SDK (fallback)

### P1 — SHOULD Complete
- [ ] Cross-service delegation documented
- [ ] Idempotency behavior documented
- [ ] Response JSON paths verified with real runs
- [ ] Troubleshooting error code table

## Directory Layout

```
aws-[service]-ops/
├── SKILL.md              # What to do (triggers, scope, flows)
├── references/
│   ├── aws-cli-usage.md  # How to: CLI commands, JSON paths
│   ├── boto3-sdk-usage.md # How to: SDK methods, examples
│   ├── core-concepts.md  # Service architecture, limits
│   ├── troubleshooting.md # Error codes, diagnostics
│   └── integration.md    # Environment setup (uv, credentials)
└── assets/
    └── example-config.yaml
```

## Key Principles

| Principle | Enforcement |
|-----------|-------------|
| **CLI-first with SDK fallback** | Primary path: AWS CLI; fallback: boto3 after 3 CLI failures |
| **OpenAPI accuracy** | All fields traceable to AWS API docs |
| **Safety gates** | Human confirmation before destructive operations |
| **Credential isolation** | Only `{{env.*}}` placeholders; never real secrets |

## Reference Files (How to Details)

| Reference | Content |
|-----------|---------|
| [aws-skill-template.md](references/aws-skill-template.md) | Full skill template structure |
| [aws-cli-conventions.md](references/aws-cli-conventions.md) | CLI behavioral notes, output handling, retry strategy |
| [boto3-sdk-usage.md](references/boto3-sdk-usage.md) | boto3 patterns, error handling, polling |
| [integration.md](references/integration.md) | Environment setup (uv, credentials, multi-cloud) |
| [core-concepts-template.md](references/core-concepts-template.md) | Service architecture template |
| [troubleshooting-template.md](references/troubleshooting-template.md) | Error codes, diagnostics template |
| [governance-review.md](references/governance-review.md) | Pre-merge checklist, adversarial scenarios |

## See Also

- [AWS CLI Documentation](https://docs.aws.amazon.com/cli/)
- [boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [Agent Skills OpenSpec](https://agentskills.io/specification)