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
  version: "1.1.0"
  last_updated: "2026-07-31"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  type: meta-skill
---

# AWS Skill Generator (Meta-Skill)

Meta-skill that scaffolds new `aws-[service]-ops` runbooks. Does **not** execute live AWS operations — use generated skills for that.

## Trigger & Scope

### SHOULD Use When

- Creating a new AWS service skill from scratch
- Aligning an existing skill to the current template structure
- Updating a skill after AWS API changes or new service capabilities
- User mentions "skill generator", "scaffold", "new aws skill", or "update skill template"

### SHOULD NOT Use When

- Executing live AWS operations — use the generated `aws-[service]-ops` skills
- Billing-only or cost-analysis tasks
- Non-AWS cloud work (Azure, GCP, etc.)
- Modifying SKILL.md frontmatter structure without understanding Charter C1–C6

## Generation Process

```
Input → Analyze Sources → Create Layout → Populate Files → Verify
```

P0/P1 checklist, directory layout, key principles: [`generation-checklist.md`](references/generation-checklist.md). After generation, run Charter C1–C7 self-check: [`post-generation-self-check.md`](references/post-generation-self-check.md) (full adversarial review: [`governance-review.md`](references/governance-review.md)).

## Token Efficiency (C6 Hard Gate)

All generated skills MUST pass `python3 scripts/te_gate.py <skill> --strict` (G1 ≤120 lines, G3/G4 machine checks). TE-1…TE-6 rules and examples: [`token-efficiency-guide.md`](references/token-efficiency-guide.md).

## GCL Integration

Classify every op as read-only / create / mutate / destructive before declaring done. Destructive or `required`-tier skills MUST ship `metadata.gcl`, `## Quality Gate (GCL)`, `references/rubric.md`, and thin `references/prompt-templates.md` (shared skeleton). Full workflow: [`gcl-integration.md`](references/gcl-integration.md).

## Reference Files

| Reference | Content |
|-----------|---------|
| [aws-skill-template.md](references/aws-skill-template.md) | Full skill template structure |
| [generation-checklist.md](references/generation-checklist.md) | P0/P1 checklist, layout, principles |
| [post-generation-self-check.md](references/post-generation-self-check.md) | Charter C1–C7 compliance loop |
| [token-efficiency-guide.md](references/token-efficiency-guide.md) | TE-1…TE-6 with examples |
| [gcl-integration.md](references/gcl-integration.md) | GCL scaffolding for new skills |
| [aws-cli-conventions.md](references/aws-cli-conventions.md) | CLI behavioral notes, retry strategy |
| [boto3-sdk-usage.md](references/boto3-sdk-usage.md) | boto3 patterns, error handling |
| [integration.md](references/integration.md) | Environment setup (uv, credentials) |
| [core-concepts-template.md](references/core-concepts-template.md) | Service architecture template |
| [troubleshooting-template.md](references/troubleshooting-template.md) | Error codes, diagnostics template |
| [governance-review.md](references/governance-review.md) | Pre-merge checklist, adversarial scenarios |
| [gcl-spec.md](references/gcl-spec.md) | GCL spec (5-dim rubric, AWS rules A1–A16) |
| [prompt-skeletons.md](references/prompt-skeletons.md) | Shared G/C/O templates |
| [assets/new-skill-template/prompt-templates.md](assets/new-skill-template/prompt-templates.md) | Copy-paste template for new skills |

## See Also

- [AWS CLI Documentation](https://docs.aws.amazon.com/cli/)
- [boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [Agent Skills OpenSpec](https://agentskills.io/specification)

> After completing a task, review and distill reusable assets per the root AGENTS.md "Compound-Asset Distillation Loop (CADL)".
