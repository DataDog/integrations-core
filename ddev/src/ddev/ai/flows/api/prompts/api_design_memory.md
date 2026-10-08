---
type: memory_prompt
name: api_design_memory
---
Write the implementation handoff directly from the research and tool results already in this
conversation. This memory step has no tools, and the response is saved verbatim; do not announce
future work, request inspection, or claim a fresh read. The preceding READY message is only a
readiness signal. If a required contract remains too uncertain to implement, write a BLOCKED
handoff with the evidence gap and needed correction, even if that message said READY.

Make this an evidence-backed decision guide and source index. Downstream tasks receive the PRD
separately and can inspect current files. Carry forward implementation-critical decisions,
exceptions, exact contracts, and unresolved risks without reproducing the PRD, API schema, metric
catalog, or research transcript. For large sources, cite the relevant URL, path, or section and
state shared rules plus consequential exceptions. Include exact names and fields when needed for
correct implementation. Cite sources per section rather than per fact; mark design decisions and
flag weak or conflicting evidence. Mention a local probe only when it established something the
documentation or source does not, such as a deviation, a data artifact, or an accepted
continuation request; give its request, outcome, and saved response path. List other reusable
saved responses once, under build and validation focus. Paraphrase documentation rather than
pasting fetched excerpts. State each rule once, where it applies. State missing evidence and its
consequence rather than inventing results.

The handoff is context, not authority. Downstream agents should inspect current files and verify
the cited evidence relevant to each contract they implement, test, or document, especially when
evidence is missing or contradictory. They need not re-read every source wholesale.

Use these headings:

1. **Status, scope, and open items** — READY or BLOCKED; identity, compatibility, assumptions,
   and blockers. For BLOCKED, identify the affected requirement, exact stop reason, evidence, and
   needed user action. READY requires a well-supported, implementable contract for every required
   behavior; identify representative live-data gaps as targeted test follow-up.
2. **Collection and telemetry decisions** — group requirements by source or collector. Give the
   evidence location, validated operation/fields, implementation consequence, and consequential
   metric semantics. Name unsupported or partial requirements individually and state the log/event
   decision. Use shared definitions for repeated tags, types, units, aggregation, and missing/zero
   rules; retain exceptions that could change emitted data.
3. **Operational contracts** — only details a builder could otherwise get wrong: auth/versioning,
   pagination, response envelopes, joins, filters, bounds, failure/partial behavior, and log
   cursor/delivery state where applicable.
   List each product option with the user need it serves, its default, bounds, and cross-field
   rules; the implementation task declares them in the spec from this list.
4. **Build and validation focus** — ownership paths only where useful, highest-value client/check/
   cursor/live checks, fixture limits, and a short source index. Do not provide a full file
   inventory or test matrix.

Do not call planned behavior implemented or omit details needed to prevent log loss.
