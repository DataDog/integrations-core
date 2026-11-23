# Log pipeline hard checks

Keep in sync with ddoghq/claude-marketplace `agent-integrations/skills/generate-log-pipeline/references/review-sources.md` (the log pipeline generator). Both read the guide live; this file holds only the local overrides and the fallback.

## Local overrides

These win over the guide.

### Service remappers are banned

Page 3622502423 says a service remapper "may be required". That is stale, and it applies to Agent integrations too: no `service-remapper`, and no sub-pipeline filtered on `service:<value>`.

Customers' service remapping takes precedence over what an integration sets, so an integration-level service remapper is dead code, and out-of-the-box dashboards, monitors or saved views that filter on the value it would set stop matching. The `service` tag belongs to the operator. To tell record kinds apart, put an identifier in a custom attribute such as `@event_type` and filter sub-pipelines on that.

### OCSF is out of scope

Don't review `schema-processor` blocks or ask for them.

## Fallback hard checks

Use these when the live guide can't be read. They are a summary, not a replacement: say so in the closing note.

| Check | Bypassable? | Bypass annotation |
|---|---|---|
| A date remapper covers the pipeline and every sub-pipeline | Yes, with justification | `# bypass-global-missing-date-remapper-checks` |
| A status remapper exists where a level or severity field exists | No | |
| `preserveSource` is `false` in a new integration's pipeline, `true` for remappers added to an existing integration's | No | |
| No facet with a new custom path that duplicates a standard attribute; a facet on the standard path is the right form | No | |
| Custom facet paths are namespaced (`amazon.s3.file`, not `file`) | Yes, with justification | `# bypass-global-facets-path-checks` |
| A facet path resolves to a single attribute, not an object | Yes, with justification | `# bypass-global-facets-path-checks` |
| No duplication between grok rules; shared parts go in `supportRules` | Yes, with justification | `# bypass-global-grok-parser-rules-checks` |
| Minimal `%{data:}` and wildcards in `matchRules` | Yes, with justification | `# bypass-global-grok-parser-rules-checks` |
| A sample for every sub-pipeline and every `matchRule` | No | |

Bypass annotations go at the top of the pipeline file and need a written justification. The reviewers assess each one; not every rule has a bypass, and other annotations exist beyond these three (page 2405999869 lists them).

Since August 2025 the linter also fails a missing date remapper, non-namespaced or object facet paths, and grok static analysis (nested repetition, `%{data:}` overuse), unless the matching annotation is present. The date remapper exception is JSON logs whose timestamp is already in an attribute Datadog reads as the date.
