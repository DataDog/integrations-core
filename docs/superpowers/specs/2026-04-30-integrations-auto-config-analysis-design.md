# Integrations Advanced Auto-Config Exploration — Analysis Design

**Date:** 2026-04-30
**Author:** Vincent Whitchurch (with Claude Code)
**Source ticket:** [Confluence: Integrations advanced auto config exploration](https://datadoghq.atlassian.net/wiki/spaces/DSCVR/pages/6650004331/Integrations+advanced+auto+config+exploration) (page id `6650004331`, space `DSCVR`)

## 1. Goal

Classify every Agent integration in `integrations-core` by whether its required configuration fields could be discovered automatically, and fill in the "Analysis" section of the source Confluence page with three tables:

1. **Generic auto-config possible** — host + well-known port (or one well-known URL) is enough; a generic "scan ports until one looks like OpenMetrics / responds to a known protocol banner" mechanism would work.
2. **Custom auto-config possible** — integration-specific probing logic is required (e.g. nginx variants, multi-endpoint, parsing the server's own config file).
3. **Auto-config impossible** — needs credentials, tenant IDs, API keys, or other state not derivable from the host.

The artifact populating the Confluence page is a markdown summary rendered from per-integration JSON files. The procedure is documented so that sub-agents can be dispatched to handle the bulk of the work.

## 2. Inputs

- `~/agent_integrations_by_org_count_2026-04-30T10_07_38.868252573Z.csv` — 405 integration names, ranked by distinct org count. Drives prioritization (most-used first).
- `integrations-core` working tree — contains 411 integration directories, ~260 of which carry an `assets/configuration/spec.yaml`. Only those with a `spec.yaml` are in scope; others are noted in `analysis/skipped.md`.
- The Confluence page itself (page id `6650004331`) — only its "Analysis" section is touched.

## 3. Output artifacts (under `analysis/` at repo root, **tracked in git**)

| Path | Purpose |
|------|---------|
| `analysis/procedure.md` | The rubric every sub-agent and the main session follows. |
| `analysis/schema.json` | JSON schema used to validate per-integration outputs. |
| `analysis/queue.txt` | Ordered list of integrations to process (CSV order ∩ has `spec.yaml`). |
| `analysis/skipped.md` | Integrations from the CSV that have no `spec.yaml`, with one-line reasons. |
| `analysis/state.json` | Orchestrator state: `done`, `failed`, `retried`, `in_flight`, `wave`. |
| `analysis/integrations/<name>.json` | Per-integration analysis result (canonical data). |
| `analysis/integrations/<name>.md` | Optional human-readable rendering (generated). |
| `analysis/summary.md` | Three rendered tables — the canonical Confluence body. |
| `analysis/scripts/build_queue.py` | Builds `queue.txt` and `skipped.md` from CSV + repo state. |
| `analysis/scripts/render_summary.py` | Renders `summary.md` from all `integrations/*.json`. |

A working branch `analysis/auto-config-exploration` (off `master`) holds all of the above so it can be shared with others.

## 4. Per-integration JSON schema

```json
{
  "name": "redisdb",
  "display_name": "Redis",
  "spec_path": "redisdb/assets/configuration/spec.yaml",
  "required_fields": ["host", "port"],
  "all_relevant_fields": [
    {"name": "host", "required": true, "default": "localhost"},
    {"name": "port", "required": true, "default": 6379},
    {"name": "password", "required": false, "default": null}
  ],
  "classification": "generic | custom | impossible",
  "auto_config_method": "openmetrics-port-scan | tcp-banner-probe | http-path-probe | config-file-parse | credentials-required | other",
  "has_existing_auto_conf": true,
  "auto_conf_path": "redisdb/datadog_checks/redisdb/data/auto_conf.yaml",
  "explanation": "Short prose, one or two sentences when not generic.",
  "references": [
    {"kind": "spec",     "path": "redisdb/assets/configuration/spec.yaml"},
    {"kind": "check",    "path": "redisdb/datadog_checks/redisdb/redisdb.py"},
    {"kind": "auto_conf","path": "redisdb/datadog_checks/redisdb/data/auto_conf.yaml"},
    {"kind": "upstream", "url":  "https://redis.io/docs/..."}
  ],
  "confidence": "high | medium | low",
  "needs_human_review": false,
  "notes": "Free-form, used for caveats."
}
```

Validation: `analysis/schema.json` enforces required keys, allowed enum values, and that `references` paths exist or are URLs.

## 5. Procedure spec (`analysis/procedure.md`) — what each analysis must do

For every integration in its assigned list:

1. **Read** `<name>/assets/configuration/spec.yaml`. Extract the `instances`-level options. A field is required if it has no default value and is not gated by another option. Record every option in `all_relevant_fields`.
2. **Check** `<name>/datadog_checks/<name>/data/auto_conf.yaml` — its presence proves the integration already supports basic Autodiscovery templating; its content reveals the assumed defaults.
3. **Read** the check implementation (`<name>/datadog_checks/<name>/<name>.py` or equivalent) to confirm what each field actually does — TCP probe, HTTP probe, file parse, credential bind?
4. **Skim** `<name>/README.md` for a sanity check on the upstream system and its default ports/endpoints.
5. **WebFetch** upstream documentation only when the spec is ambiguous about defaults. Cite the URL in `references`.
6. **Classify**:
   - **generic** — only host + a well-known port (or single well-known URL) is needed; everything else has defaults or is easily probable from the wire. Methods: `openmetrics-port-scan`, `tcp-banner-probe`, `http-path-probe` against a single canonical path.
   - **custom** — host + something integration-specific (multiple plausible URL paths, parsing the server's config file, multi-endpoint discovery).
   - **impossible** — needs credentials, API keys, tenant/account IDs, OAuth tokens, certificates, region+account combinations, or any other state not present on the wire.
7. **Emit** JSON conforming to the schema; write to `analysis/integrations/<name>.json`.

Confidence guidelines:
- **high** — spec is clear, check code matches, and either an `auto_conf.yaml` exists or the upstream port is universally known.
- **medium** — minor ambiguity (e.g. one optional field that *might* be required in some deployments).
- **low** / `needs_human_review: true` — spec is unusual or the integration's behavior couldn't be confirmed from the code/docs.

## 6. Phases

### Phase 0 — Scaffolding (main session)

- Create branch `analysis/auto-config-exploration`.
- Write `analysis/procedure.md`, `analysis/schema.json`, scripts.
- Run `build_queue.py`. Produce `queue.txt` (~260 names) and `skipped.md`.
- Initialize empty `state.json`.

### Phase 1 — Bootstrap, ~15 manual analyses (main session)

Top-of-CSV integrations that have a `spec.yaml`. Likely list (subject to filtering):
`redisdb, postgres, nginx, coredns, apache, mysql, haproxy, elasticsearch, containerd, iis, mongo, rabbitmq, sqlserver, kafka_consumer, snmp`.

Each bootstrap analysis follows the procedure. Patterns observed (recurring required fields, common methods) feed back into `procedure.md` so sub-agents learn from them. The bootstrap output also serves as canonical examples of the JSON format.

### Phase 2 — Adaptive waves (main session orchestrates, sub-agents do the work)

Each wave:

1. Pull next 50 names from `queue.txt` (skipping anything already in `state.json:done`).
2. Dispatch **10 parallel sub-agents** (`general-purpose`), each handling 5 integrations.
3. As each sub-agent returns, validate every JSON it produced against `schema.json`. On validation failure, retry that batch once with a stricter prompt. On second failure, the main session does that batch inline.
4. Regenerate `analysis/summary.md` from all `integrations/*.json`.
5. Push `summary.md` to the Confluence page (replacing the body of the "Analysis" section).
6. Commit progress to the working branch.
7. If the wave revealed a recurring new pattern (≥3 integrations sharing it) that the procedure doesn't address, append a section to `procedure.md` for the next wave.

Five waves cover the ~245 remaining integrations.

### Phase 3 — Final sweep

- Re-render `summary.md` once everything is processed.
- Diff against the previously pushed Confluence body; push final version.
- Print a stats report (counts per classification, count of `needs_human_review`).
- Commit the final state and leave the branch ready to push.

## 7. Sub-agent prompt template

```
You are analyzing 5 Agent integrations from integrations-core for auto-config feasibility.

Working directory: /home/bits/go/src/github.com/DataDog/integrations-core2
Procedure: read analysis/procedure.md and follow every step.
JSON schema: analysis/schema.json
Bootstrap examples: analysis/integrations/redisdb.json, analysis/integrations/nginx.json
Integrations to analyze: [<5 names>]

Tasks:
1. Run the procedure for each integration, in order.
2. Write one JSON file per integration to analysis/integrations/<name>.json.
3. Do NOT modify any file outside analysis/integrations/.
4. Do NOT push to Confluence or update the queue/state.
5. After each integration, print a one-line status: "<name>: <classification> (<confidence>)".

Time budget: aim for 5 minutes per integration. If an integration's spec is unusually
complex, set "needs_human_review": true and move on rather than getting stuck.

Constraints:
- Use Read, Bash (rg/find/ls), and WebFetch only when needed.
- Cite every source in `references` (file path or URL).
- Output JSON must validate against the schema; the orchestrator will reject otherwise.
```

## 8. Confluence rendering

Body posted under the existing `## Analysis` heading. Structure:

```
## Analysis

_Generated <date>. <N total>: <X> generic / <Y> custom / <Z> impossible / <W> needs review._

### Generic auto-config possible
| Integration | Required fields | Method / detail | References |
| ...         | ...             | ...             | ...        |

### Custom auto-config possible
...

### Auto-config impossible
...

### Skipped (no spec.yaml)
...
```

The "Detailed explanation" cell is left empty (or set to a short phrase like "OpenMetrics endpoint") for routine generic cases, per the source ticket. For custom and impossible classifications it's a one-or-two-sentence justification with inline reference links.

The push uses the Atlassian MCP `updateConfluencePage` tool with `contentFormat: "html"`. The renderer emits HTML directly to avoid markdown→ADF conversion ambiguity.

## 9. Failure handling

| Failure | Behavior |
|---------|----------|
| Sub-agent returns invalid JSON | Retry that batch once with a stricter prompt naming the schema violation. |
| Sub-agent fails twice | Main session re-does that batch inline. |
| Integration analysis genuinely uncertain | Marked `needs_human_review: true`, included in the appropriate table with a footnote. |
| Confluence push fails | Retry once; on second failure, log the summary path and continue (waves don't depend on Confluence). |
| Schema gap discovered mid-run | Update `schema.json` and `procedure.md` between waves; previously-validated JSONs stay valid by additive-only schema changes. |

## 10. Non-goals

- No changes to integration code, specs, or auto_conf.yaml files.
- No proposal of which generic auto-config mechanism the Agent should *implement* — only which integrations could benefit. Implementation design is a follow-up.
- No analysis of marketplace/SaaS-only integrations (they have no Agent check to auto-configure).

## 11. Open assumptions worth flagging

- `auto_conf.yaml` presence is treated as evidence of templating support but not as a final answer; some `auto_conf.yaml` files are stale or container-specific and may not match what a generic discovery layer would produce.
- "Required" is determined from `spec.yaml` semantics (`required: true`, no default, not nested under an optional). Edge cases where a field is technically optional but practically required are flagged as `medium` confidence.
- The CSV's organisation-count signal is used only for ordering; an integration's popularity does not affect its classification.
