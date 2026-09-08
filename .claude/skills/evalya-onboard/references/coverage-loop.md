# Closing the coverage loop

Goal: prove the running check emits every metric in the achievable target set (SKILL.md step 1),
and drive the workload until it does. Coverage is a **diff of two metric-name sets** — emitted vs
target — never a guess.

## The oracle: what the check actually emits

The Datadog Agent's `check` command can dump the metrics a check collected as JSON. In
integrations-core this is reached through `ddev env`, which passes args straight through to
`agent check` and auto-injects the integration name (verified in
`ddev/src/ddev/cli/env/agent.py` and `check.py`):

```shell
ddev env agent <integration> <env> check <integration> --json
```

`<env>` is one of the names from `ddev env show <integration>`. The JSON contains an aggregator
dump; the metric names live under the `aggregator.metrics[].metric` entries (confirm the exact
shape at runtime — it has changed across Agent versions). Extract the distinct metric names and
diff against the target.

**Run OpenMetrics checks at least twice (`-t 2`).** A single `agent check` scrape emits **zero**
monotonic counters — the OpenMetrics v2 base check needs a previous sample to submit a `.count`
metric, so one scrape drops every counter on the endpoint. For any OpenMetrics-based check, always
run `ddev env agent <integration> <env> check <integration> -t 2 --json` (`-t`/`--check-times`).
This is not a workload problem and no amount of traffic fixes it; it cost ~15 percentage points of
apparent coverage in the rabbitmq run (39/56 with one scrape, 54/56 with two) before it was
diagnosed. When a whole class of metrics (everything ending `.count`) is missing while the matching
gauges are present, suspect this before touching the workload.

**Verify the flag at runtime.** If `--json` is not honored by the pinned Agent, fall back to:

- `ddev env agent <integration> <env> check <integration>` and parse the human-readable "Metrics"
  section, or
- the pytest E2E path (`ddev env test --dev <integration> <env>`) with the aggregator stub, which
  records every submitted metric and exposes coverage assertions.

State which oracle you used; do not assert coverage from reasoning alone.

## Two ways to stand up the fixture

### A. ddev env (primary during authoring)

Standard integrations-core E2E path. Requires a `tests/` env config that points the check at the
fixture's `provides.*` connection details.

```shell
ddev env show  <integration>                 # list environments
ddev env start --dev <integration> <env>     # start fixture + Agent
ddev env agent <integration> <env> check <integration> --json   # oracle
ddev env stop  <integration> <env>
```

### B. evalya run (fixture-native, CI-reproducible)

Stands up exactly the published task, no ddev env config needed:

```shell
evalya run --path <integration>/tests/evalya.yaml --task <integration>-full
```

`evalya run` supports `--with <path@task>` (inject a background task) and `--then <path@task>` (run
a task after completion). Once local coverage is closed via path A, the CI-reproducible form is a
small verification task that consumes the fixture's `provides.*` contract, runs the Agent check,
and asserts the emitted set covers the target. Wiring the Agent as an evalya task is a deliberate
addition — only build it if the user wants coverage enforced in CI; the primary loop does not
require it.

## Multi-instance / multi-role checks

Some integrations emit their dashboard metrics from **different node roles that no single endpoint
exposes**. Mongo is the canonical case: `chunks.*` come only from a check instance pointed at
`mongos` (a `MongosDeployment`), while `replset.*`/`oplog.*` come only from an instance pointed at a
shard replica-set member (a `ReplicaSetDeployment`) — one instance opens one connection and adopts
one deployment type, so neither endpoint alone covers both.

When step 2 shows target metrics splitting across roles like this, the fixture publishes the whole
topology (every node reachable on the compose network), and the coverage config runs **multiple
check instances** — one per role/endpoint. The emitted set is the union across instances. Detect
this early: if two target metric groups require mutually exclusive deployment types, a single-endpoint
fixture can never reach 100% no matter the workload.

1. Stand up the fixture (A or B).
2. Run the oracle, extract emitted metric names.
3. `uncovered = achievable_target - emitted`.
4. If empty → done. Otherwise, for each uncovered metric:
   - decide whether it is state-dependent (extend `seed`) or rate/counter (extend `activity-gen`)
     or un-emittable by OSS (pause, consult user);
   - make the one targeted workload change;
   - re-run from step 2.
5. Stop when `uncovered` is empty **or** every remaining metric is documented-unreachable with a
   concrete reason (cross-integration `system.*`, requires a managed-service field, etc.).

Guard against thrash: change one thing per iteration and re-diff, so each workload line is
justified by a metric it actually moved. Give rate/counter metrics one or two scrape intervals of
traffic before concluding they are uncovered.

## Reporting

Report coverage as `<covered>/<achievable>` with the command that produced the emitted set, and
list any documented-unreachable metrics with their reason. Example:
`24/24 target metrics emitted (ddev env agent redisdb <env> check redisdb --json); 0 unreachable.`
