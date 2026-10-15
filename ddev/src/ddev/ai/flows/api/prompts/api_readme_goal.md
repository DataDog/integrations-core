---
type: goal
name: api_readme_goal
---
Read the README against the current client, check, metadata, spec/generated example, tests, and
phase handoffs. The goal is met only when customer-facing claims match implemented behavior and
official evidence.

Confirm that the README:

- preserves the standard structure and contains no scaffold instructions or invented/dangling links;
- documents the real endpoint, auth/permissions, API limitations, filters, and generated options
  without secrets, tested versions, or unsupported compatibility claims;
- links to metadata.csv instead of duplicating it;
- distinguishes metrics, events, logs, and service checks and states that no service checks exist;
- documents API-forwarded logs with `logs_enabled` plus `type: integration`, or documents the actual
  local file/journald mechanism, without conflating them;
- states only limitations a user must act on or would otherwise misread, briefly, without
  internal mechanics, cache keys, exactly-once claims, test results, or validation status;
- does not claim release availability, live compatibility, or E2E success beyond actual evidence;
- is comparable in length and depth to two or three named sibling integration READMEs (state their
  approximate word counts); flag it when it is substantially longer.

The handoff must preserve known command failures, skipped/unrun test tiers, assumptions, incomplete
PRD requirements, and targeted human follow-up. Missing official URLs may use plain product text;
they must not be fabricated. Return concrete corrections for any mismatch.
