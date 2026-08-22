> 见 [AGENTS.md §14](../AGENTS.md) 索引

## 14. Token Efficiency Hard Gate & Deduplication Spec (TE Hard Gate)

> Repo-wide hard requirement, constraining both the output of
> `aws-skill-generator` **and** anyone manually editing a skill.
> Same source as `aws-skill-generator/SKILL.md` §Token Efficiency Requirements
> (C6 MUST-PASS). Full thresholds / dedup precedents / existing-asset remediation
> strategy in [`docs/te-hard-gate.md`](docs/te-hard-gate.md).

**Core thresholds (C6 hard metrics, any fail ⇒ no merge):**
- **G1** `SKILL.md` ≤ 120 lines; **G2** no >5-line hardcoded static table (use
  an API instead, TE-1); **G3** JSON paths declared only once at top (TE-4);
  **G4** no cross-file duplicated flow / boilerplate (TE-6); **G5** boto3 no
  docstring (TE-2); **G6** compact error table (TE-3).
- **Dedup principle**: content appearing in ≥2 skills must be extracted to a
  single source of truth (precedent: `_sync_prompt_skeletons.py` reduced 31
  skills' ~5,800 lines of GCL boilerplate to a 231-line skeleton + thin deltas).
- **Incremental remediation of existing assets**: new/changed skills must meet
  the bar; of the 34 existing `aws-*-ops` over-length ones
  (ec2/cloudwatch/cloudtrail/dynamodb/config/ram/acm/waf), trim back to ≤120
  lines as opportunity allows.

### Compound asset example: discipline must dogfood itself (from finsecops-optimization retro)

> Reusable pattern (cross-task / cross-enterprise LLM ecosystem general):
> **Problem** → repo discipline (e.g., "write spec+plan before implement") is
> easily and quietly violated by later changes, with no self-check anchor.
> **Anti-pattern** → discipline lives only in AGENTS.md; the landing commit does
> not reference the corresponding spec/plan.
> **Correct approach** → the discipline's **own rollout commit** must carry the
> spec+plan that references the discipline (precedent: when `33f18ba` added the
> `Spec + Plan Before Implement` rule, it also landed
> `2026-07-19-finsecops-optimization-design.md` + the corresponding plan). Make
> the discipline "obey itself", so any agent reviewing the commit can verify the
> discipline was dogfooded, not merely declared.

