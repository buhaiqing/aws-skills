# Design: aws-eventbridge-ops P1 fidelity depth

**Date:** 2026-07-30  
**Depends on:** golden scenarios (already landed)  
**Version target:** 1.1.1

## Scope

Surgical P1 from prior audits — no mass TE trim (refs already lean).

| Fix | Files |
|-----|-------|
| max_iter 2→3; Recommended GCL | SKILL.md |
| Safety tokens + `confirm=` prefix; EB4/EB7/MODIFY | SKILL.md |
| Confirmation Strings table; aws_cli_svc; EB hard rules | prompt-templates.md |
| Drop fake `put-event-bus`; add list-rules + bus/schedule/pipe delete patterns | aws-cli-usage.md |
| Mask ApiKeyValue (A9) | boto3-sdk-usage.md |
| Fix Lambda ARNs (add region) | assets/example-config.yaml |
| AIOps changelog + skill version sync | README.md, README_cn.md |
| Inline environment / cross_skill_deps (SR-3, G1 headroom) | SKILL.md |

## Non-goals

EKS work; rubric bulk rewrite; core-concepts Pricing trim (P2).

## Acceptance

- `te_gate.py --skill aws-eventbridge-ops` PASS; SKILL ≤120
- `golden_eval.py run` still 6/6
- No `put-event-bus` in skill tree
- `## Confirmation Strings` present in prompt-templates
- README Existing Skills + AIOps rows show v1.1.1
