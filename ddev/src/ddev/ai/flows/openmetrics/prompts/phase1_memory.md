---
type: memory_prompt
name: phase1_memory
---
Summarize this phase for the next phase (which writes `check.py` and tests).
Keep it tight and factual. Include:

- The integration name and the path of the integration directory.
- The **metric prefix** used (the next phase must set `__NAMESPACE__` to exactly this).
- **What the package already contained.** State whether you created it or adopted one that was
  already there, and if it was already there, what it held that later phases will inherit: a test
  environment (give the directory and the compose file you saw), a `check.py` with real content
  beyond the scaffold, any test files (name them), a `hatch.toml`. Say so explicitly when the
  package was created fresh and none of this applies. Report only what you observed — none of it
  is authoritative, and the phases that own those files decide what to do with them.
- Every endpoint name, its mapping YAML path, and how many families that file maps.
- The path to the single integration-wide `metadata.csv`, how many rows it contains, and the
  deduplicated metric-family count across all mappings.
- Every officially sourced family absent from all captured catalogs, including its raw name,
  effective type, official source, and the complete expanded Datadog `metric_name` rows from
  `metadata.csv`. Label these exact names as the fixture-exclusion list for the symmetric unit
  metadata assertion. State explicitly when this list is empty.
- Whether you fanned out to endpoint subagents, and any endpoint assignment that needed repair.
- Any metrics you flagged as ambiguous (naming, type, or description) so they can be
  reviewed later.
