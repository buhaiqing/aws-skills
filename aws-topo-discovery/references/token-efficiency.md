# Token Efficiency

All 6 TE rules applied (see `aws-skill-generator` SKILL.md §Token Efficiency Requirements):
- TE-1: No hardcoded region/CIDR tables — use `describe-vpcs` / `describe-subnets` / `describe-regions`
- TE-2: Inline comments only in boto3 code (no docstrings)
- TE-3: Compact error tables throughout
- TE-4: JSON paths centralized in `## Common JSON Paths` above; details in `references/execution-commands.md`
- TE-5: N/A — no `assets/example-config.yaml` (CI templates in `assets/ci-cd-templates/`)
- TE-6: Extracted execution flows in `references/execution-flows.md` (content out of SKILL.md per C6 line-count limit)
