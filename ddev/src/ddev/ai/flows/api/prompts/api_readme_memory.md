---
type: memory_prompt
name: api_readme_memory
---
Write the final human-review handoff from file reads, command results, and repairs already in
this conversation. Only this memory step is tool-free; earlier task/reviewer tools were available.
Do not request tools or claim fresh inspection. The response is saved verbatim.

Aim for about 600 words, expanding only to preserve a material unresolved issue. Use material file,
source, and run-log locations instead of restating the PRD, earlier handoffs, README, or catalogs.
Use these sections, without an additional recap:

1. **Delivered scope** — integration identity, README and material paths, implemented scope, and
   incomplete or divergent requirements. Summarize README changes and customer-visible limitations,
   including log enablement and delivery risks where relevant; omit internal cursor mechanics.
2. **Corrections and evidence** — final decisions that supersede earlier claims, with supporting
   file/source locations and any unresolved official references. Include material tester or reviewer
   repairs, but do not repeat resolved findings as current defects.
3. **Validation results** — exact command/tool selections and final applicable unit, Docker
   integration, Agent E2E, validation, and lint outcomes with available counts. Attribute results
   inherited from earlier phases and cite run-log locations when available. Consolidate repeated
   passes and repaired failures; keep failed, skipped, stale, unavailable, and unrun work explicit.
   Briefly distinguish vendor captures from synthetic coverage by location.
4. **Human follow-up** — unresolved source/config/manifest defects, assumptions, missing evidence,
   and focused next steps with their consequences. Do not infer release readiness from a generated
   draft or passing subset.
