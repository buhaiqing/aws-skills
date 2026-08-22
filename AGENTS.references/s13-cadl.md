> 见 [AGENTS.md §13](../AGENTS.md) 索引

## 13. Compound-Asset Distillation Loop (CADL)

**A working loop, not a single rule**: after any substantive task, the Agent
must complete "extract → decide landing → write → gate" before finishing — a
task without distillation is an unfinished task. Make every pitfall, review,
and cross-skill collaboration into a reusable asset for next time, building
compound interest.

> CADL loop mechanism, adapted to this repo's terminology: `{{env.*}}`/
> `{{user.*}}`/`{{output.*}}` placeholders, Reflexion Memory
> (`docs/failure-patterns.md`), CodeGraph (§12), AGENTS.md line gate (≤500 lines).

### Triggers (apply CADL if any is met)

- Multi-step / cross-file task completed
- Cross-skill collaboration (delegation matrix or parallel agent / oracle / explore)
- Review / fix loop (GCL, 2-round self-review, Oracle consultation)
- Discovered a repo defect / pitfall (even if outside this scope)
- Found a pre-existing FAIL during verification and attributed its cause
- User gave a reusable workflow preference (e.g., "dual-write subcommand to bypass CLI bug")

### Loop steps

```
1. Extract   → abstract a reusable pattern (pitfall to avoid / review dimension / collaboration pattern / verification command / helper)
               format: "problem → anti-pattern → correct approach (with code example)"
2. Decide landing → leaving this repo? → ~/.config/opencode/AGENTS.md
                    this repo only? → this project's AGENTS.md
                    failure mode / pitfall? → docs/failure-patterns.md
                    a skill-specific capability? → standalone Skill (via aws-skill-generator)
3. Write     → executable + with example + with boundaries; first grep the target file to confirm uncovered
4. Gate      → wc -l before writing; if this file is ≥500 lines, trim before writing (note: currently ~675 lines; overflow source is §11 GCL's existing bulk + §12/§13 extensions; next optimization can move §11's long tables out)
5. Reuse     → next time a similar task reads the target file and gets the asset → compound interest takes effect
```

### Skill-side hook (give every Skill its own distillation awareness)

- **Source**: `aws-skill-generator`, when generating each skill, must inject one
  line at the end of SKILL.md:
  `> After completing a task, review and distill reusable assets per the root AGENTS.md "Compound-Asset Distillation Loop (CADL)".`
  All future `aws-<svc>-ops` automatically inherit this awareness.
- **Existing skills**: progressively add the same hint line at the end of each
  SKILL.md so any model invoking any skill sees the trigger signal. (Injecting
  the hook into the 34 existing `aws-*-ops` is incremental, not in this CADL
  migration scope; add later as needed.)

### Anti-patterns (violating CADL)

| Anti-pattern | Correct approach |
|---|---|
| Finish a task and stop, no distillation | Complete the CADL loop before delivering |
| Write one-off context into AGENTS.md as an asset | Only distill patterns reusable across tasks |
| Duplicate an existing entry | grep to confirm uncovered before writing |
| Distill only on CodeGraph-related tasks | Reviews/fixes/collaboration/verification all trigger |
| Write pitfall assets into AGENTS.md instead of failure-patterns.md | Pitfalls/failure modes go to `docs/failure-patterns.md`, general patterns go to AGENTS.md |

### Compound asset example: declarative-contract-first (from `skill-as-infrastructure` rollout)

> Reusable pattern (cross-task / cross-enterprise LLM ecosystem general):
> **Problem** → an agent skill system needs composite/copilot skills to be
> machine-recognizable and composable.
> **Anti-pattern** → introduce a private registry / dedicated loader (coupled to
> a specific agent runtime).
> **Correct approach** → add **minimal declarative-contract** fields to the
> existing frontmatter (`metadata.type` / `provides` / `delegate`), enforced by
> the **existing** self-check framework (Charter C7); any agent only needs to
> `glob aws-*-ops/SKILL.md` and read frontmatter to compose — zero private
> loader, runtime-agnostic.
> Generalize: for any need to "make X machine-recognizable / composable", prefer
> adding declarative fields + reusing the existing gate, rather than building
> private infrastructure.

### Compound asset example: contract evolution must grandfather existing (from C7 retro)

> Reusable pattern (cross-task / cross-enterprise LLM ecosystem general):
> **Problem** → when adding a new contract (e.g., `metadata.type: composite`),
> existing skills already using a different value (e.g., `orchestrator-meta`)
> would be misjudged orphan / HALT by the new gate.
> **Anti-pattern** → ignore existing assets after changing the contract, or
> force-edit existing frontmatter to align (expands scope, introduces regressions).
> **Correct approach** → explicitly include the existing equivalent value in the
> contract's allowed-value set (`composite` ≡ `orchestrator-meta`), synchronize
> in three places — template comment / Charter / AGENTS.md — without touching
> the existing skills themselves. Before adding a new contract, first `grep`
> globally to confirm no missing legacy values.

