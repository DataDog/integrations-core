# Togo flows

This is the only file that knows about Togo. It maps each integration type to the Togo flow that
builds it, and says what that flow takes as inputs, what it cannot honor, and how to hand off. Both
flows are unmerged and live on branches of `integrations-core`; when a flow changes, update this
file.

## Running a flow

- `ddev meta ai` opens the Togo interface, where the caller picks the flow and fills in its inputs.
- The flows come from the installed `ddev`. To use an unmerged flow, install `ddev` from a checkout
  of the flow's branch with its `ai` extra, which the flows need:
  `pipx install --force -e "<checkout>/ddev[ai]"` (based on the `integrations-core` developer setup
  docs; add `--python` with a Python 3.13 interpreter if pipx's default is older). This replaces the
  caller's global `ddev`, which then follows that checkout's branch; the caller runs it, not you,
  and can go back with `pipx install --force ddev`.
- The flow writes into the repository `ddev` works on. Run `ddev -x meta ai` from the root of the
  `integrations-core` checkout checked in step 2 of the workflow, so the flow builds where the skill
  checked the directory, and give the PRD as an absolute path.
- A flow agent cannot open a URL it composes itself: it opens links from the PRD or from its own
  search results, so the PRD's documentation links matter.
- The flows do not build the lab. A person prepares the Docker lab the flow uses for live design
  checks and for integration and end-to-end tests; the hand-off tells them what it must exercise.

Every flow takes these built-in inputs, besides its own:

- **Product requirements file** (`prd`, required): the PRD path. The flow reads the file and passes
  its text to the phases that receive the PRD.
- **Max timeout** (`max_timeout`, optional): a time limit for the run, in seconds; empty means no
  limit.

## HTTP API: the `api` flow

Branch `loa/api-flow`. Inputs:

- **Integration display name** (`integration`, required): the display name from the PRD title.
  `ddev` derives the directory from it with the rule in step 2 of the workflow.
- **Prepared Docker assets** (`docker_path`, optional): the directory with the lab's Compose file.
  When it is given, the lab must be running and reachable when the flow starts; otherwise the design
  phase stops and asks the caller to start it. Without it, the design phase uses a running local
  service if it finds one, and the tests stay fixture-based: live tests need the prepared assets,
  or a lab already under the integration's `tests/`.

What the caller should know:

- The design, build, test, and README phases all receive the PRD. The design phase checks every PRD
  item against official docs and live responses, and stops with the blockers it finds (for example
  an endpoint or field that does not exist, or permissions the API cannot grant).
- The flow has no credential input: when the API needs auth, the lab must hold a lab-only credential
  the flow can find in the assets.
- The test phase may copy the assets into the integration's `tests/`, and starts and stops the
  Compose project itself: the assets must hold only lab-only values and no data (no database files
  or volume contents; the Compose file may still declare volumes), and the caller's own lab must not
  hold the same host ports or container names.
- The flow chooses the metric namespace and metric names, and keeps a namespace or metric names the
  PRD states.
- If the directory exists, the flow skips scaffolding and edits the existing files, keeping prior
  work.
- It cannot honor: integration service checks (it never adds them). Auth that needs a client
  certificate, a signature per request, or an interactive login may keep the design phase from
  calling the API.

## OpenMetrics: the `openmetrics` flow

Branch `loa/openmetrics-ai-gen` (use `origin/loa/openmetrics-ai-gen`; a local branch may be behind).
Inputs:

- **Endpoints** (`endpoints`, required, one or more): each has a **name** and a **URL**.
  - The name is normalized to snake case, must then start with a letter and be unique. With more
    than one endpoint, it names that endpoint's metric mapping and test fixture.
  - The URL must start with `http://` or `https://` and answer a plain GET with HTTP 200, without
    auth or custom headers, with default TLS verification (redirects are followed), within 10
    seconds, with a body of at most 10 MB in Prometheus or OpenMetrics text format that holds at
    least one metric family.
  - Every endpoint must be live when the flow starts: the first phase reads them all, and the run
    fails if any one fails.
  - The first endpoint's URL becomes the configuration example, with only its host replaced: use the
    product's default port and path for it.
- **Integration name** (`integration`, required): used as given for the display name in the
  configuration spec and for creating the package. The directory and the metric namespace are both
  this name lowercased, with each run of characters other than letters and digits replaced by `_`.
- **Docker folder** (`docker_source_path`, optional): a folder with a Compose file that runs the
  product and serves the endpoints. The flow copies the whole folder, unchanged, into the
  integration's `tests/docker/`, so it must hold only lab-only values and no data (no database
  files or volume contents; the Compose file may still declare volumes). When the input is empty, a
  Compose file must already exist under the integration's `tests/`; otherwise the run fails. The
  tests start it and pass it every variable it references.
- **Metric fan-out threshold** (`fanout_threshold`, optional, default 100): with one endpoint, how
  many metric families one agent maps before the work is split among parallel agents (several
  endpoints are always split by endpoint). It is a cost and speed setting, not a product decision.

What the caller should know:

- Only the code and test phases receive the PRD. Endpoint inspection, metric naming and metadata,
  and the README never see it. The code phase applies the PRD after the fact, as changes: drop a
  metric, rename a metric or label (exact pairs), exclude or copy labels, force a configuration
  default or option, or a custom scraper for per-sample changes. The PRD states intent; the code
  phase must turn each item into one of these "common shapes" (its prompt's words) and applies only
  the changes the PRD calls for. It edits the metadata only for dropped and renamed metrics. Metric
  names come from the naming phase, which never sees the PRD: a metric name the PRD gives survives
  only if the code phase applies it as a rename, so list PRD metric names as a risk. The test phase
  must pin every observable requirement with an assertion.
- The first phase captures each endpoint once, and the unit tests use that capture. The lab must
  already produce its workload when the run starts (so gated, traffic-driven, and event-driven
  families and labels are in the capture), and again during the tests.
- The test phase starts the copied Compose project itself and must finish with a passing end-to-end
  run, or the run stops before the README. Docker must stay available, the images pullable, and the
  caller's own lab must not hold the same host ports or container names (stop it after the run
  starts, or use variable host ports).
- Without requirements, the flow maps every family on the endpoints plus the ones the official docs
  or source document, keeps histograms as bucket, count, and sum counts, renames reserved and
  generic labels and excludes unbounded ones, and adds no service checks.
- An area users can turn off (an optional metric group) must be built from configuration: the code
  goal accepts no conditional or extra mapping file. List it as a risk in the hand-off.
- Copying a label onto metrics that already carry a label with the same name replaces its value;
  keeping both needs custom code. List it as a risk.
- If the directory exists, the flow adopts it and replaces its check, configuration spec and its
  generated files, metric mappings, metadata, tests, and README.
- It cannot honor:
  - logs: the configuration spec has no logs section;
  - metrics the endpoints do not serve during the run, beyond what the official docs or source
    document (the lab must make them emit instead);
  - a general naming policy (only exact rename pairs);
  - latency percentiles across hosts (histograms as distributions): the metadata, written before
    the PRD is applied, keeps bucket, count, and sum counts, so the tests cannot pass reliably;
  - metadata wording (units, descriptions) and README content;
  - endpoints that need auth, custom headers, or a certificate the default TLS verification rejects,
    during the run (the lab must serve them without);
  - a namespace different from the integration name (to get another namespace, choose another
    integration name);
  - service checks.

## Hand-off

Give it in the chat, in this order. Do not propose values for inputs the PRD does not settle.

1. **Flow**: the flow name and its branch, how to install `ddev` from it, and the command to run
   from the checkout root (`ddev -x meta ai`), from Running a flow above.
2. **Inputs**: each of the flow's inputs, with its value when the PRD settles it (the absolute PRD
   path, the display name or integration name, one endpoint per component the PRD scrapes, named
   after the component, with the path and port from the PRD's setup) and otherwise what it means
   and what it requires, from the flow's section above.
3. **Lab**: the PRD has no test environment section; this item is the input for whoever prepares
   the lab. From the adapter's lab needs, as short bullets:
   - the product version (an image tag) and edition, and the customer setup from the PRD;
   - what the lab must exercise for the in-scope signals: the workload, failures, in-flight or stuck
     work, each state and dimension in scope, several nodes, instances, or parents where the PRD
     needs them, a trigger for each event category, logs the Agent can read, the optional signals,
     and the settings that make gated families appear;
   - host secrets the product needs, by variable name, never values;
   - the in-scope signals no lab can produce, one line each, so they are covered by unit tests
     instead;
   - what the flow needs from the lab, from the flow's section above: when it must be running, a
     lab-only credential when the API needs auth, only lab-only values and no data in the assets,
     and for the `openmetrics` flow, endpoints live and producing their workload when the run
     starts, and Docker available through the tests.
4. **Requirements the flow cannot honor** that the caller kept, one line each.
5. **Risks**: anything else you noticed, such as an auth scheme the flow may not be able to call,
   an area users can turn off or a copied label from the flow's section above, an existing
   directory the flow would work on, or differences between the evidence and the docs.
