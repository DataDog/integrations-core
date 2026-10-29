---
type: memory_prompt
name: api_build_memory
---
Write the tester handoff from file evidence, command results, and reviewer repairs already in
this conversation. Only this memory step is tool-free; earlier task/reviewer inspection remains
evidence. The response is saved verbatim.

Aim for about 600 words, expanding only for a test-critical contract or unresolved defect. The
tester receives the PRD and design handoff and can read current files. Report implementation
choices and deviations instead of repeating endpoint, metric, configuration, or file catalogs.
Use these sections, without an additional recap:

1. **Implemented scope and decisions** — identity, material code/metadata/spec/manifest paths,
   implemented collectors, and incomplete requirements. Preserve test-critical semantics not clear
   from the design, especially log cursors, work-budget resumption, and restart behavior.
2. **Corrections to the design** — what earlier claim is superseded, the final behavior, its
   reason, and evidence location. Include reviewer findings and repairs that affect expectations.
   Do not leave a verified correction listed as unverified or copy obsolete guidance forward.
3. **Verification evidence** — exact command/tool arguments, scope, final applicable outcome and
   available counts, with a run-log location when available. Include relevant reviewer evidence;
   identify inherited results as such. Collapse repeated passes and repaired failures into their
   final result plus a brief repair note; retain unresolved failures and results made stale by edits.
   Point to API captures/fixtures once, distinguishing observed from synthetic data.
4. **Testing priorities and gaps** — highest-value client/check/log-resumption cases and why they
   matter, plus assumptions, missing evidence, known bugs, and unrun work. State a gap's consequence
   rather than inferring a pass. Scaffold existence does not prove implementation.
