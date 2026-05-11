# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

AWS cloud resource/service operational skills for AI Agent automation. Each skill (`aws-[service]-ops`) is an agent-readable runbook for AWS operations.

## Architecture

### Meta-Skill Pattern
`aws-skill-generator` scaffolds all other skills. It is NOT executed directly—load it when creating new `aws-[service]-ops` skills.

### Skill Structure
Each operational skill follows this separation:
- **SKILL.md** (~70-120 lines): What to do (triggers, scope, execution flow overview)
- **references/**: How to do (CLI commands, SDK code, troubleshooting details)

```
aws-[service]-ops/
├── SKILL.md              # Concise: triggers, scope, Pre-flight → Execute → Validate → Recover
├── references/
│   ├── aws-cli-usage.md  # CLI command map, JSON paths (verified with real runs)
│   ├── boto3-sdk-usage.md # SDK patterns, error handling
│   ├── core-concepts.md  # Service architecture, quotas
│   └── troubleshooting.md
│   └── integration.md    # uv setup, credentials
└── assets/
```

## Execution Model

**Dual-path execution**:
1. **Primary**: AWS CLI (`aws [service] [command] --output json`)
2. **Fallback**: boto3 SDK (after 3 CLI failures)

**Always** use `--output json` for agent parsing.

## Flow Pattern

Every operation follows:
```
Pre-flight → Execute → Validate → Recover
```

- **Pre-flight**: CLI available, credentials, region, quota checks
- **Execute**: CLI command OR SDK call
- **Validate**: Poll until terminal state with max wait
- **Recover**: HALT vs retry based on error type

## Credential Convention

| Placeholder | Rule |
|-------------|------|
| `{{env.AWS_ACCESS_KEY_ID}}` | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Use default only if skill allows |
| `{{user.*}}` | Ask once; reuse |

**Never commit real keys. Always use `{{env.*}}` placeholders.**

### Environment Loading

Credentials are loaded via `.env` file (see `.env.example` template):

1. Copy `.env.example` → `.env` at project root
2. Fill in real credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, etc.)
3. `.env` is blocked by `.gitignore` — never committed

**Priority order**:
1. Shell environment variables (highest)
2. `.env` file values
3. Default values (lowest)

## Safety Gates

Destructive operations (delete, terminate) require explicit human confirmation before CLI/SDK execution.

## Error Recovery

| Error Type | Action |
|------------|--------|
| InvalidParameter (400) | Fix args; retry once |
| QuotaExceeded | HALT |
| Throttling (429) | Exponential backoff; max 3 retries |
| 5xx Internal | Retry 3x; then HALT |

## Creating New Skills

When user requests new AWS service skill:
1. Load `aws-skill-generator` meta-skill
2. Collect: product name, primary resource, AWS docs URL, CLI support evidence, boto3 module
3. Generate directory structure from template
4. Populate SKILL.md with triggers, scope, flow overview
5. Fill references with CLI commands, SDK examples, troubleshooting
6. Run governance adversarial scenarios before considering complete

## Governance Pre-Merge Checklist

- Triggers: SHOULD/SHOULD-NOT concrete; delegation matches existing skills
- Credentials: `{{env.*}}` only; no paste-secrets instruction
- Destructive: human confirmation step present
- CLI fidelity: `--output json` used; JSON paths verified
- Dual-path: CLI + SDK both documented
- Recovery: HALT vs retry specified for quota, throttling

## Reference

- aws-skill-generator/SKILL.md — Meta-skill usage
- aws-skill-generator/references/aws-skill-template.md — Full template
- aws-skill-generator/references/governance-review.md — Review checklist + adversarial scenarios