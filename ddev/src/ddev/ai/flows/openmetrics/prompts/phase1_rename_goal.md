---
type: goal
name: phase1_rename_goal
---
Verify **metric coverage** of the rename mapping for **${integration}**. Check only
coverage — not naming quality, idiom, or hierarchy.

## Where the source catalog is

${inspect_endpoint_memory}

## What must be true

1. Read every metrics catalog JSONL listed in the inspection summary and collect its
   endpoint name and source family `name` values.
2. Read every rename mapping reported by the worker. A single endpoint uses
   `<integration_name>/datadog_checks/<integration_name>/metrics.yaml`; multiple endpoints
   use one `<integration_name>/datadog_checks/<integration_name>/metrics/<endpoint_name>.yaml`
   per normalized endpoint, where `<integration_name>` is `${integration}` lowercased with
   each run of non-alphanumeric characters replaced by `_`. The mapping-file count must equal
   the endpoint count.
3. For each endpoint, that mapping's YAML **keys** must match that endpoint's catalog names:
   - every catalog family appears as a key in the correct endpoint file (no source metric dropped), and
   - no key exists that is neither a catalog family nor a metric the worker added from an
     **official source** (nothing invented).
   Two exceptions are allowed: a metric the renamer omitted for a valid, stated reason; and
   a key absent from the catalog that the worker's summary records as added from an **official
   source** — the vendor's docs/site, or the project's own repository including its public
   source code (where, for an open-source technology, the metric is defined or emitted).
   Confirm the worker named such a source — and where you can, use `web_search` and `web_fetch`
   against it to confirm the metric is real. Reject an extra key with no official source, or one backed only
   by a blog/forum/third-party page.

4. Across files, a raw family exposed by multiple endpoints must have the same mapped name and
   effective type everywhere. Reject inconsistent cross-endpoint mappings.

Pass (`valid: true`) only if those rules are met. Otherwise fail and list the
specific endpoint, missing and/or unjustified extra names, or inconsistency.
