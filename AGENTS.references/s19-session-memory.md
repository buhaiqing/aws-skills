> 见 [AGENTS.md §19](../AGENTS.md) 索引

## 19. Cross-Session Memory Protocol (L4 #10)

P2.1-P2.4 in-memory and file-backed signals (failure patterns, golden
baselines, telemetry traces). **§19 (Cross-Session Memory)** is the only
piece that survives an **agent restart** — it persists project-context
into `.omc/conventions.json`, the sidecar that complements
(but does not replace) the auto-scanned `.omc/project-memory.json`.

> **Hard rule**: every new agent session SHOULD call
> `python3 scripts/session_memory.py render --max-chars 2000` at startup
> and prepend the output to its first user-facing message. This loads
> prior learnings without re-derivation.

### Sidecar file

`.omc/conventions.json` is an **agent-managed** JSON file. Schema is **flat**
on purpose — JSON rather than Markdown so any runtime (Python, JS, Shell)
can parse it cheaply.

```json
{
  "version": "1.0.0",
  "updated_at": "2026-07-25T...",
  "records": [
    {
      "id": "mem-001",
      "timestamp": "2026-07-25T...",
      "scope": "convention" | "user-pref" | "repo-fact" | "tool-choice",
      "summary": "≤ 120 char headline",
      "detail": "optional longer form",
      "confidence": 0.0..1.0,
      "source_session": "session-uuid",
      "tags": ["safety", "runtime-hook"]
    }
  ]
}
```

> **NB**: do NOT mix this with `.omc/project-memory.json` (842 lines, auto-
> scanned tech-stack). They serve different purposes; agents should write
> only to `.omc/conventions.json`.

### Scopes (decide which one fits)

| Scope | When to use |
|---|---|
| `user-pref` | user's explicit preference (e.g., "Chinese docs canonical") |
| `repo-fact` | hard fact about the repo ("31 skills, 22 required") |
| `convention` | agreed-upon rule (e.g., "always run ruff before commit") |
| `tool-choice` | technology decision (e.g., "use ruff instead of flake8") |

### CLI reference

```bash
# 1. Record (manual or agent-derived)
python3 scripts/session_memory.py record \
  --scope convention \
  --summary "Always invoke runtime_safety before destructive ops" \
  --detail "§15 hard rule" \
  --confidence 0.95 \
  --source-session $OMC_SESSION_ID \
  --tag safety --tag runtime-hook

# 2. Query (keyword search, top-k)
python3 scripts/session_memory.py query "aws region safety" --top 3

# 3. Render (for system-prompt injection)
python3 scripts/session_memory.py render --max-chars 2000

# 4. List (humans debugging)
python3 scripts/session_memory.py list
```

### Derive-vs-record flow

Heuristic v0 (`derive_candidates(transcript)`) extracts candidate
records with `confidence=0.6`. Agent reviews candidates and only
**explicitly saves** the ones worth keeping. This prevents the
convention file from filling with noise.

```python
from session_memory import (
    MemoryRecord, load_memory, save_memory,
    derive_candidates, add_record,
)

# End of session: derive candidates from transcript, save keepers
transcript = [...]  # [{role, content}, ...]
records = load_memory(Path(".omc/conventions.json"))
for c in derive_candidates(transcript, source_session=SESSION_ID):
    # Agent-judgment filter (user runs review, no auto-save)
    if c.confidence >= 0.8 and len(c.summary) >= 12:
        add_record(records, scope=c.scope, summary=c.summary,
                   detail=c.detail, confidence=c.confidence,
                   source_session=SESSION_ID, tags=c.tags)
save_memory(records, Path(".omc/conventions.json"))
```

### Decision matrix — derive, record, or skip?

| Trigger | Action |
|---|---|
| User says "convention: ..." | derive → record (high conf) |
| User corrects agent behavior | derive → record |
| Agent discovers new repo fact | record manually (skip heuristic) |
| One-off task outcome | skip (use failure-patterns.md instead) |
| Routine Q&A | skip (transient) |

### Pruning (TBD)

Currently no auto-prune. Add `--older-than-days` flag in a future iteration
when records exceed a few hundred.

### Integration with §15 (Runtime Safety Hook)

The runtime hook already records to `docs/failure-patterns.md`. Cross-session
memory is **complementary**: failures stay in `failure-patterns.md`
(canonical, signal-rich), conventions stay in `conventions.json`
(low-volume, preference-bearing).

Spec: [`docs/superpowers/specs/2026-07-25-cross-session-memory-design.md`](docs/superpowers/specs/2026-07-25-cross-session-memory-design.md).
Plan: [`docs/superpowers/plans/2026-07-25-cross-session-memory.md`](docs/superpowers/plans/2026-07-25-cross-session-memory.md).

