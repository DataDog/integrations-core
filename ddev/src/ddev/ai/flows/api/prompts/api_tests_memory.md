---
type: memory_prompt
name: api_tests_memory
---
Write the documentation-author handoff from file evidence, command results, and repairs already
in this conversation. Only this memory step is tool-free; earlier task/reviewer inspection remains
evidence. Do not request tools or claim fresh inspection. The response is saved verbatim.

Aim for about 600 words, expanding only for a material gap or correction. The documenter receives
the PRD and earlier handoffs and can read current files. Preserve customer-visible findings and
validation limits instead of repeating contracts, assertions, or fixture/metric catalogs.
Use these sections, without an additional recap:

1. **Customer-visible findings** — behavior and limitations relevant to README claims, with the
   supporting test tier or source location. Tested versions and validation status are handoff
   evidence, not instructions to put them in the README; the documenter selects user-facing content.
2. **Corrections and repairs** — changed paths, final behavior, evidence, and the earlier claim
   each correction supersedes. Retain only still-open assumptions; do not repeat resolved unknowns.
3. **Verification evidence** — exact command/tool arguments and environment/selection, final
   applicable results and counts for unit, Docker integration, Agent E2E, validation, and lint.
   Cite run-log locations when available and label inherited evidence. Collapse repeated passes
   and repaired failures into the final result plus a brief repair note. Distinguish passes,
   skips, failures, stale evidence, and unavailable/unrun work. Name capture and synthetic-fixture
   locations once; include probe details only when they change a customer claim.
4. **Remaining gaps** — coverage and compatibility limits, unverified log behavior, design/build
   defects, and required human follow-up. State missing evidence and its consequence. A reachable
   service or a skipped/unrun tier is never evidence of a passing test.
