---
type: memory_prompt
name: phase1_memory
---
Summarize this phase for the next phase (which writes `check.py` and tests).
Keep it tight and factual. Include:

- The integration name and the path of the scaffolded integration directory.
- The **metric prefix** used (the next phase must set `__NAMESPACE__` to exactly this).
- Every endpoint name, its mapping YAML path, and how many families that file maps.
- The path to the single integration-wide `metadata.csv`, how many rows it contains, and the
  deduplicated metric-family count across all mappings.
- Whether you fanned out to endpoint subagents, and any endpoint assignment that needed repair.
- Any metrics you flagged as ambiguous (naming, type, or description) so they can be
  reviewed later.
