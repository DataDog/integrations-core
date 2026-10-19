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
If the target is not the designed scaffold, call `stop_flow` before editing.

Implement the focused custom client, check orchestration, metric submissions, metadata.csv, and any
designed API-log collection according to your standing builder contract. Remove scaffold examples.
Declare each product option the code reads in spec.yaml, then run ddev_validate config and models
with sync=true so `self.config.<option>` is typed. The next task completes shared templates, logs,
the manifest, and final validation from a compacted conversation; preserve decisions in files.

## Direct API log collection

When the design includes remote API logs, implement them as logs, not events. Guard all expensive
list/export/poll/download work with `self.logs_enabled`. Normalize each record into a safe send_log
payload with a string message, seconds-since-epoch timestamp when available, stable source/service
and tags, and only approved structured fields. Remove secrets and sensitive raw content identified
by the design.

Use `get_log_cursor(stream)` and `send_log(data, cursor=next_cursor, stream=stream)` as the durable
delivery boundary. Choose deterministic stream names from stable vendor identities; do not use
mutable display names, timestamps, raw URLs, or secrets. The cursor must contain every field needed
to resume without gaps, including timestamp tie-breaker, page/file/job identity, and record offset
where applicable. send_log already persists `log_cursor_<stream>` after submission, so never write
a duplicate manual watermark for the same position.

Normalize or hash stream identity into a bounded cache-key-safe value. Never include credentials,
query strings, path separators, mutable labels, or unbounded arbitrary response text. Ensure a
record-level cursor can resume within a multi-record page; a next-page token alone is not a valid
cursor until the entire current page is committed.

Advance a cursor only through the last contiguous successfully parsed and submitted record. For an
archive or export, mark the artifact complete only on its final record. A page, poll, download,
parse, or submission failure must leave later work uncommitted so restart favors bounded duplicates
over loss. Manual persistent cache may hold distinct recoverable job-discovery state only when the
design requires it; it must be reconstructible and must never outrun the log cursor.

Apply the design's explicit poison-record policy for permanently invalid records. Transient fetch,
download, and parse failures retain the prior cursor. A non-retriable record may advance only when
the validated policy records a safe identifier and intentional drop; never silently skip it.

Bound polling attempts/deadlines, backfill windows, pages, files, records, and state size with
code constants. A work-budget boundary preserves the next unprocessed position, even within an
artifact; later runs and restarts must deliver the remainder before marking it complete. A warning
does not justify truncating the source at that budget. Handle documented terminal export states
and expiration. Do not sleep forever in a check. Preserve the
design's first-run and cache-corruption policy and its honest at-least-once/restart guarantees.
Use LogCrawlerCheck/LogStream only when the design selected it; a combined metrics-and-logs check
may keep AgentCheck and use a focused log collector instead.

Finish with changed paths, observed command outcomes, and consequential implementation decisions
or departures from the design, including log delivery/resumption behavior and required configuration.
Name unsupported requirements and unresolved problems. Point to code and metadata for mappings and
catalogs instead of repeating them. Do not claim generation, validation, or tests that did not run.
