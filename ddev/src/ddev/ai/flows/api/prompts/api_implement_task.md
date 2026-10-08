---
type: prompt
name: api_implement_task
---
Implement the validated API collection for **${integration}**.

## PRD

${prd}

## Design handoff

${api_design_memory}

This task starts with fresh context. Read the complete handoff and current scaffold before editing.
If the design is BLOCKED or the target is not the designed scaffold, stop without making changes.

Implement the focused custom client, check orchestration, metric submissions, metadata.csv, and any
designed API-log collection according to your standing builder contract. Remove scaffold examples.
Declare each product option the code reads in spec.yaml with its type, `default`, and constraints
from the design handoff, then run ddev_validate config and models with sync=true so
`self.config.<option>` is typed. Read options without fallback defaults or range checks, and keep
internal bounds as module constants. The next task completes shared templates, logs, the manifest,
and final validation. It starts from a compacted summary of this conversation, so record decisions
it must honor in files and state deviations and known limitations in your final response.

Finish with:

- an endpoint-to-client-method-to-collector mapping;
- implemented metrics and their semantic decisions;
- implemented log streams, cursor/commit/restart behavior, and bounded polling/backfill behavior;
- changed paths and required configuration fields;
- departures from design, unsupported requirements, known limitations, and unresolved problems.

Do not claim configuration generation, validation, or tests that did not run.
