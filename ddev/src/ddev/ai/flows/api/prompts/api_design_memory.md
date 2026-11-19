---
type: memory_prompt
name: api_design_memory
---
Write the implementation handoff from research and tool results already in this conversation.
Only this memory step is tool-free; use earlier task evidence without claiming fresh inspection.
The response is saved verbatim. The preceding READY message is a readiness signal; if a required
contract is still too uncertain to implement, write BLOCKED with the evidence gap and correction.

Aim for about 1,200 words, expanding only to preserve implementation-critical contracts. The next
agents receive the PRD separately. State each decision once; use shared rules with exceptions,
exact fields/names where needed, and source locations instead of schema excerpts or a research
transcript. Distinguish vendor facts, live observations, design choices, and assumptions. When later
evidence corrects an earlier claim, state the replacement and its evidence; do not retain the old
claim as an open question. Missing evidence remains an explicit gap.

Use these four sections, without an additional recap:

1. **Status, scope, and open items** — READY or BLOCKED; display name, chosen metric namespace, compatibility,
   unsupported or partial requirements, assumptions, and blockers. READY requires an implementable
   contract for every required behavior. Separate representative live-data gaps from facts still
   needed to implement safely; name the affected requirement and follow-up.
2. **Collection decisions** — group by collector: validated operation and fields, source location,
   and metric/log/event semantics. Define common naming, tags, types, units, aggregation, and
   missing/zero behavior once. Preserve consequential exceptions without repeating the PRD or a
   verbose metric catalog.
3. **Operational contracts** — auth/versioning, response envelopes, pagination, joins, filters,
   bounds, failure policy, and log cursor/delivery/restart behavior where applicable. List each
   product option's user need, default, bounds, and cross-field rules once. Preserve details needed
   to prevent data loss; planned behavior is not implemented behavior.
4. **Build and validation focus** — material repository references and the lesson borrowed,
   highest-value unresolved checks, and reusable evidence paths. For a consequential probe, give
   its request, observed outcome, and saved response path. Cite evidence once, prefer the latest
   applicable result, and distinguish unavailable service/data from an unsupported API contract.
