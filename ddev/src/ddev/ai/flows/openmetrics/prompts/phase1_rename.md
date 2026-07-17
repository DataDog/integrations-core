---
type: prompt
name: phase1_rename
---
# Task — Scaffold the integration and write the endpoint metrics mappings

You are building the Datadog integration for **${integration}**. In this task you
scaffold the integration and produce one metrics rename mapping per inspected endpoint. You do **not**
write `metadata.csv` here (that is the next task) and you never touch `check.py`.

## Context from the endpoint inspection

${inspect_endpoint_memory}

The summary above lists every inspected endpoint and the path to its **metrics catalog**
(JSONL provenance header followed by one row per metric family: `name`, `type`, `help`,
`unit`, `label_keys`, `sample_count`). Read every catalog in full. Each is authoritative for
what that endpoint **currently exposes**. Map every family in every catalog. The catalogs are
**not** necessarily the complete set of metrics this technology can
emit: the live endpoint may omit metrics that require an optional feature, a connected
backend, a specific version, or particular traffic. Step 2b covers finding those in the
official documentation. Beyond the catalog families and any metric you confirm in an
**official** source per Step 2b, map nothing.

## Step 1 — Scaffold the integration

Create the integration with the scaffolding tool, supplying:

- **integration name** — the name derived by your standing integration-identity rule.
- **display name** — `${integration}`, exactly as given here.
- **metrics prefix** — the derived metric prefix **followed by a dot**.
- **platforms** — `linux`, `windows`, `mac_os` (all three) unless `${integration}`
  clearly cannot run on one of them.

This creates the `<integration_name>/` directory and registers the display name,
metrics prefix, and platforms in `.ddev/config.toml`.

## Step 2 — Read the catalogs and choose the delegation shape

Read every JSONL catalog path from the inspection summary in full.

If there is more than one endpoint, **always fan out by endpoint** with one
`spawn_identical_subagents` call. First create the shared
`<integration_name>/datadog_checks/<integration_name>/metrics/` directory. Then create one
assignment per endpoint. Every child receives this complete system prompt, this complete task
prompt, the endpoint name, the complete catalog path, and the exact output path from Step 3.
State that scaffolding is complete and that the child owns only research, renaming, and
validation for its endpoint. Grant `read_file`, `create_file`, `web_search`, and `web_fetch`.
Each child creates only its assigned file and cannot delegate further. After the parallel
assignments return, perform Step 4 yourself.

If there is exactly one endpoint, count its catalog families:

- At or below `${fanout_threshold}`, write the complete conventional `metrics.yaml` yourself.
- Above `${fanout_threshold}`, create `metrics.yaml`, partition every family into exactly one
  disjoint batch, and use one `spawn_identical_subagents` call with an assignment per batch.
  Give each child this complete system prompt, this complete task prompt, its catalog rows, and
  only `read_file` and `append_file`. Each child appends entries for its batch without a header,
  prose, or Markdown fences and cannot delegate further.

Read every completed file yourself; subagent completion is not acceptance.

## Step 2b — Cross-check the official documentation (`web_search` / `web_fetch`)

The live endpoint often does not expose every metric the technology can emit — some appear
only with an optional feature enabled, a backend connected, a newer version, or live
traffic. Use the `web_search` and `web_fetch` tools to consult the technology's **official documentation** for
its full set of exposed/Prometheus metrics, and add any documented metric that the catalog is
missing.

Follow the source-authority rules in your standing instructions. For open-source technologies,
inspect the official repository locations where metrics are defined, registered, or emitted,
not only the documentation. Add a family only when an authoritative source establishes its
real name and type.

For every officially sourced addition:

- A doc-sourced metric has no catalog row, so give it the **mapping form with an explicit
  `type:`** (`gauge`, `counter`, `histogram`, `summary`) taken from the documentation or code
  — the same form Step 3 describes for `unknown` families. Apply all the Step 3 naming rules.
- **Record every metric you add this way in your final summary** (the raw name, the type, and
  the official source — doc page or source file), so the metadata task and the reviewer know
  it came from an official source rather than the catalog.

If the official docs and code add nothing beyond the catalog, that is a perfectly valid
outcome — say so in your summary and move on.

## Step 3 — Write one mapping file per endpoint

Every output is a **flat YAML mapping**. Use these exact naming rules:

- one endpoint: `<integration_name>/datadog_checks/<integration_name>/metrics.yaml`;
- multiple endpoints: `<integration_name>/datadog_checks/<integration_name>/metrics/<endpoint_name>.yaml`
  for every normalized endpoint name in the inspection output.

The number of mapping YAML files must equal the number of inspected endpoints. Each file
contains only the families belonging to that endpoint's catalog, plus any officially sourced
metric specifically associated with that endpoint. If the same raw family occurs at multiple
endpoints, keep it in each relevant file and map it identically everywhere.

One entry per catalog family **plus** one per metric you added from the official docs in
Step 2b: the **key** is the raw Prometheus family name (the catalog `name`, verbatim, or the
documented name for a doc-sourced metric); the **value** is a short, idiomatic Datadog metric
name.

### Dots vs. underscores (read carefully — this is the part most often gotten wrong)

A dot in a Datadog name introduces a **namespace level** — a grouping shared by many
metrics (a subsystem). An underscore joins the **words of a single name** (a
multi-word measurement, or a name plus its unit). The goal is a shallow, readable
hierarchy — **not** one dotted level per word. Default to **few dots**: most names have
exactly **one** dot, some have two, three is rare.

Build each value like this:

1. **Identify the subsystem** — the leading group the metric belongs to (often the
   first token; sometimes a compound like `db_client` or `cache_layer`). It becomes the
   text **before the first dot**. If the subsystem name is itself multi-word, join those
   words with **underscores**, not dots (`db_client`, not `db.client`).
2. **Optionally add one more dotted level** only when a sub-group is genuinely shared by
   **several** metrics (e.g. many metrics under a `memory` or `pool` sub-namespace). A
   one-off measurement does **not** earn its own dotted level. This includes a shared
   **leading word that several sibling measurements branch off** — for example
   `bytes_read`/`bytes_written` (and a `bytes_*_max`) under one subsystem: promote the
   shared `bytes` to a dotted level so the siblings group under it
   (`http_server.bytes.read`, `http_server.bytes.written`) instead of repeating it on each
   leaf (`http_server.bytes_read`, `http_server.bytes_written`). Do this only when there
   really are multiple siblings; a lone `bytes_read` with no `bytes_*` siblings stays a
   single leaf. This is still **one extra dot**, not a dot per word.
3. **Everything else** — the specific measurement and any unit/qualifier words
   (`_bytes`, `_seconds`, `_duration`, `_size`, `_count`) — stays as a **single
   underscore-joined leaf**.

Worked examples (illustrative — not from any real integration):

```yaml
jvm_gc_pause_seconds: jvm.gc_pause_seconds            # one subsystem (jvm); measurement kept as a leaf
jvm_gc_pause_seconds_max: jvm.gc_pause_seconds.max    # qualifier after the unit -> its own dotted level
jvm_memory_heap_used_bytes: jvm.memory.heap_used_bytes # 'memory' is a shared sub-namespace -> second dot
db_client_query_duration_seconds: db_client.query_duration_seconds  # compound subsystem -> underscore inside it
cache_evictions_total: cache.evictions                # drop _total; single leaf
http_server_bytes_read: http_server.bytes.read         # 'bytes' shared by read/written siblings -> second dot
http_server_bytes_written: http_server.bytes.written   # groups under the same 'bytes' level
```

Contrast — **too many dots, do not do this**: `jvm.gc.pause.seconds`,
`db.client.query.duration.seconds`, `cache.evictions.total`.

**Don't force a dot.** If the leading token is *not* a subsystem shared by other
metrics — e.g. a standalone `*_info`/`*_scope_info` metric, or a one-off top-level
gauge — keep the whole name as a single underscore-joined token (`scope_info`, not
`scope.info`). A dot is only earned by a real grouping.

### Other rules for the value

- **No integration prefix.** The check prepends the prefix at scrape time. If the raw
  name begins with the integration's own name, drop that leading segment (a metric like
  `<intname>_widget_count` becomes `widget_count`).
- **Drop the Prometheus `_total` suffix** from counters. The catalog `name` may or may
  not include it; if it does, strip it. Do **not** add a `.count` suffix here — that
  belongs to `metadata.csv`.
- **Keep unit/qualifier suffixes on the leaf** (`_bytes`, `_seconds`, `_ratio`,
  `_info`), never as their own dotted level.
- **A qualifier after the unit gets a dot.** When a unit word (`seconds`, `bytes`,
  `ratio`, …) is followed by a further aggregation qualifier such as `max` or `min`,
  split that trailing qualifier onto its own dotted level: `..._seconds_max` →
  `..._seconds.max`, `..._bytes_min` → `..._bytes.min`. The unit stays joined to its
  measurement; only the qualifier that comes after it becomes the dot.
- **Idiomatic, not mechanical.** Group by meaning; preserve singular/plural intent.
- Each value must match `^[a-z][a-z0-9_]*(\.[a-z0-9_]+)*$$`, and **values must be
  unique** — no two families may map to the same Datadog name.

### The gauge + counter case (`type: native_dynamic`)

A value is normally just the short Datadog name as a string. There is one exception worth
knowing. A few endpoints expose the **same base metric both as a gauge and as a `_total`
counter**; the scraper strips `_total`, so both collapse onto one Datadog name. By default
the base class locks that family to whichever type it sees first and mishandles the other.
To submit both correctly — the gauge as `<name>` and the counter as `<name>.count` — give
that one entry the **mapping form** with `type: native_dynamic`:

```yaml
go_memstats_alloc_bytes:
  name: go.memstats.alloc_bytes
  type: native_dynamic  # exposed as both a gauge and a _total counter; submit each under its own type
```

This is almost exclusively the Go runtime metric `go_memstats_alloc_bytes` (present whenever
the endpoint exposes Go runtime metrics). Use it **only** when the catalog actually shows the
same base name as both a gauge and a counter; every other family stays a plain string value.
If the catalog lists both `<base>` and `<base>_total` for such a metric, write a **single**
entry keyed by the base name with `native_dynamic` — do not add a second entry for the
`_total` family, since both are the same Datadog metric and a second entry would duplicate
the value.

### Untyped families (`type: unknown`)

Check each family's `type` in the catalog. A family whose catalog `type` is **`unknown`**
(the parser could not determine a Prometheus type — common for some exporters' orphan
summary children, e.g. Micrometer's `*_seconds_active_count` / `*_seconds_duration_sum`)
will be **silently dropped at scrape time**: the base class's native transformer skips any
metric it sees as `unknown`. A plain string value for such a family therefore produces a
metric that is declared in `metadata.csv` but never emitted, which later breaks the test
suite's symmetric metadata check. Handle every `unknown`-typed family one of two ways:

- **Give it the mapping form with an explicit `type:`** you can confidently infer from its
  name and meaning — e.g. a `*_count` that counts observations → `type: gauge` (or
  `counter` if it is a monotonic total), a `*_sum` / `*_duration_sum` running total →
  `type: gauge`. The explicit type forces a real transformer instead of the skip:

  ```yaml
  http_server_connections_seconds_active_count:
    name: http_server.connections.active
    type: gauge  # parser reports this as unknown; set a type so it is not skipped
  ```

- **Omit it entirely** (write no key for it) when you cannot confidently type it. If you
  omit a family here, it must **also** be left out of `metadata.csv` in the next task, so
  the two files stay consistent — note any family you drop in your final summary.

A family the catalog already types as `gauge`, `counter`, `histogram`, or `summary` needs
none of this; only `unknown` families do.

### Comments in mapping YAMLs

Keep the file clean. Allowed comments:

- **Structural section headers** that group related entries and aid reading, e.g.
  `# HTTP server metrics (inbound requests)`.
- **A single one-line comment on a `native_dynamic` entry**, noting it is exposed as both a
  gauge and a counter (as in the example above). Keep it to one line — the downstream phases
  read the mapping files, and this is the one rename decision worth explaining inline.

Do **not** add:

- per-entry or explanatory comments justifying a rename decision (e.g. "dropped the
  integration's own prefix"), or
- notes about ambiguities or duplicate families.

Anything you would explain in a comment about *why* you renamed something, or any
ambiguity you hit, goes in your **final summary**, not in the file.

## Step 4 — Self-check per-endpoint and combined coverage

Before finishing, read every output file and confirm: the number of files equals the number
of endpoints; every catalog family appears **exactly once in its endpoint's file**; every
value is valid; and the only keys absent from that endpoint's catalog are
metrics you added from an **official** source in Step 2b (each recorded in your summary with
its source). Two further exceptions are allowed: a gauge + counter pair collapsed into a
single `native_dynamic` entry (where the `<base>_total` family has no key of its own), and an
`unknown`-typed family you deliberately omitted because it could not be confidently typed
(record any such omission in your summary so the metadata task drops it too).

Enforce the standing cross-artifact invariants over the complete union. Report every mapping
path and its endpoint/family count in your final summary. An independent reviewer verifies this
coverage after you finish, so make it correct now.
