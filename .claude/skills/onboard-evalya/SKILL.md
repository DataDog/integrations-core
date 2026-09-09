---
name: onboard-evalya
description: Use when the user asks to onboard, add, or set up an integration for evalya, create an evalya.yaml or evalya fixture, or build a full metric-coverage E2E fixture for a Datadog Agent integration in integrations-core. Drives a guided workflow that extracts the integration's OOTB dashboard metrics as the coverage target, authors a `<integration>-full` evalya task (reusing existing tests/compose files) with a seed + continuous activity-gen workload, then iterates a coverage loop until the running check emits every target metric. Triggers on "onboard <x> to evalya", "add an evalya fixture", "evalya.yaml for <x>", "full-coverage fixture". Do NOT use for writing ordinary pytest E2E tests or ddev env configs unrelated to evalya.
---

# Onboard an integration to evalya

Build a `<integration>-full` evalya fixture that spins up a live instance plus a workload that
drives the integration's check to emit **100% of the metrics used in its OOTB dashboards**. The
canonical exemplar is `redisdb/tests/` (`evalya.yaml`, `compose/full-coverage.compose`,
`activity-gen.sh`, `proxy/`). Read `references/redis-exemplar.md` before authoring; it is the
pattern this skill reproduces.

The target integration is given as the argument (`/onboard-evalya <integration>`). If absent, ask.

## Non-negotiables

- **Worktree first.** If in a git worktree, run `ddev config override` before anything else and
  confirm with `ddev config show` (see repo `AGENTS.md`). Every coverage measurement is wrong
  otherwise.
- **Reuse before authoring.** Prefer the integration's existing `tests/compose/*` and pytest
  fixtures over new files. Author new topology only when a target metric group demands state the
  existing environment cannot produce.
- **Scaffold + iterate, pause for bespoke work.** Generate the fixture and drive the loop
  autonomously, but when a target metric needs data the OSS service cannot emit (fields injected by
  a managed service, a proxy, etc.), stop and surface it — do not silently invent a Go proxy.
- **Never edit `config_models/*.py` or `metadata.csv` to chase coverage.** The fixture makes the
  check *emit* metrics; it does not redefine them.

## Workflow

### 1. Establish the coverage target

Run the extractor (policy: **all** dashboard metrics):

```shell
python3 .claude/skills/onboard-evalya/scripts/dashboard_metrics.py <integration>
```

It prints `target` (every metric referenced in `assets/dashboards/*.json`), `in_metadata` (with
type), and `missing_from_metadata`. Triage `missing_from_metadata`:

- **Cross-integration metrics** (e.g. `system.*`, `docker.*`) — the check under test does not emit
  these. Exclude them from the achievable target and record why.
- **Typos / renamed / genuinely this integration's** — a real gap; keep in the target and expect
  the check to produce them, or flag to the user if it cannot.

The achievable target = `in_metadata` plus any kept `missing_from_metadata` entries. Write it down;
it is the loop's exit condition.

### 2. Map metrics to the state that produces them

**First, pin down which backend/config emits the dashboard's metric names.** Some checks emit
different metric name sets depending on configuration — OpenMetrics vs a legacy API (e.g. rabbitmq's
prometheus plugin emits `rabbitmq.erlang.*`/`*.count` names the management API never produces), or a
DBM/extended-metrics mode. Grep the check's metric maps under `<integration>/datadog_checks/` for a
few distinctive target names to determine which mode produces them, and configure the fixture's
check instance for that mode. Getting this wrong makes coverage unreachable no matter the workload.

For each target metric, read `metadata.csv` (type/unit) and the check source under
`<integration>/datadog_checks/` to learn what must be true for the check to emit it. When targets
span multiple topologies (e.g. mongo needs both a replica set for `oplog.*`/`replset.*` and sharding
for `chunks.*`), the single `<integration>-full` fixture must use the richest topology that covers
their union. Group them:

- **Always emitted** on a healthy idle instance (most gauges).
- **State-dependent** — need seeding (replication configured, a database/collection present, a
  slow query logged, an eviction, a connected client). These drive the one-shot `seed`.
- **Rate/counter** — zero on an idle instance; need *continuous* traffic. These drive `activity-gen`.
- **Un-emittable by OSS** — need an injection layer. Pause and consult the user (see exemplar's
  `proxy/`); do not build one unprompted.

### 3. Inventory existing fixtures

Read `<integration>/tests/`: compose files, `conftest.py`, `common.py`, config under
`tests/config` or `tests/compose`, and how the pytest suite starts the service. Decide what to
reuse. Check for an existing `tests/evalya.yaml` — extend it rather than overwrite.

### 4. Author the fixture

Follow `references/redis-exemplar.md`. Produce, under `<integration>/tests/`:

1. A **full-coverage compose** (reuse/extend an existing one where possible) with:
   - the live service (add replica/secondary topology only if a target metric needs it),
   - a one-shot `seed` service for state-dependent metrics (`restart: "no"`,
     `condition: service_completed_successfully`),
   - a continuous `activity-gen` service running `../activity-gen.sh`, `restart: unless-stopped`,
     gated by an `ACTIVITY_GEN=0` escape hatch and `depends_on` the seed,
   - the entrypoint service gated (`depends_on` … `service_healthy` / `service_completed_successfully`)
     so one dependency pulls up the whole environment.
2. An **`activity-gen.sh`** that loops the rate/counter workload, consumes the connection details
   from the `provides.*` env, supports `ACTIVITY_GEN=0` (idle but alive) and a duration cap, and
   logs progress. Keep it POSIX `sh`.
3. **`tests/evalya.yaml`** with a `<integration>-full` task referencing the compose entrypoint
   service (`./compose/<file>.compose@<service>`), with:
   - `labels`: `evalya.io/publish: "true"` and `evalya.io/provides.<VAR>` for host/port/credentials
     (`{{ .hostname }}` for the host),
   - `env` for any secrets the healthcheck/consumers need,
   - a `healthcheck` that returns ready only when the service can actually serve the check.

   Keep any existing lightweight task (e.g. `<integration>-standalone`) alongside it.

### 5. Close the coverage loop

Mechanism and exact commands: `references/coverage-loop.md`. In short:

1. Stand up the fixture and point the Agent at it.
2. Run the check and capture emitted metric names:
   `ddev env agent <integration> <env> check <integration> --json` (verify the JSON shape at
   runtime; fall back to `references/coverage-loop.md`'s alternatives if the flag differs).
3. Diff emitted names against the achievable target. For each uncovered metric, extend `seed`
   (state) or `activity-gen` (traffic) and re-run.
4. Repeat until the gap is empty or every remaining metric is documented as unreachable (with the
   reason). Do not claim 100% without the diff showing it — back the claim with the command output.

### 6. Document and finish

- Add/extend `<integration>/tests/README.md`: what `<integration>-full` is, the services, the
  `ACTIVITY_GEN` switch, and any documented-unreachable metrics.
- Lint touched Python (the workload is usually `sh`, but the extractor and any helper are Python):
  `ddev test -fs <integration>` where applicable.
- Changelog: **open the PR first**, then add `<integration>/changelog.d/<PR>.added` by hand (see
  `AGENTS.md`; do not use `ddev release changelog new`). Test/fixture-only changes still touch files
  shipped with the Agent only if they live under `datadog_checks/` — a `tests/` fixture usually does
  not require an entry; confirm against `AGENTS.md` before deciding.
- Open the PR as a **draft** using `.github/PULL_REQUEST_TEMPLATE.md`, set a `qa/*` label, and leave
  it in draft. Do not mark ready for review.

## Guardrails

- State each uncovered metric and the concrete workload change that will cover it before editing —
  no speculative traffic.
- If coverage stalls because a metric needs un-emittable data, stop and present options; a bespoke
  proxy is a deliberate, user-approved step, not a default.
- Keep the diff focused on the fixture. Do not refactor the check or unrelated tests.
