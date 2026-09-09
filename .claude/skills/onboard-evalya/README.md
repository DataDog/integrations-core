# onboard-evalya

Onboard a Datadog integration to evalya: build a `<integration>-full` fixture that spins up a
live instance plus a workload that drives the check to emit 100% of the metrics used in the
integration's OOTB dashboards. Modeled on the `redisdb/tests/` exemplar.

Invoke with `/onboard-evalya <integration>` (or ask to "onboard <x> to evalya").

## Layout

| Path | Role |
|---|---|
| `SKILL.md` | The agent-facing workflow (what the model executes). |
| `references/redis-exemplar.md` | Annotated walkthrough of the redisdb fixture. |
| `references/coverage-loop.md` | The emitted-vs-target diff mechanism, the `-t 2` rule, multi-instance handling. |
| `scripts/dashboard_metrics.py` | Deterministic extractor: dashboard metrics joined to `metadata.csv`. |

## Workflow

The only cycle is step 5 (the coverage loop); everything else is linear.

```
              /onboard-evalya <integration>
                         │
              ┌──────────▼───────────┐
              │  GUARDRAILS (gate)   │  ddev config override (worktree)
              │                      │  reuse compose · no metadata edits
              └──────────┬───────────┘
                         │
   ┌─────────────────────▼─────────────────────┐
   │ 1. TARGET                                  │  dashboard_metrics.py
   │    dashboards/*.json  ──►  metric set      │  join metadata.csv
   │    triage "missing": drop system.*,        │  = coverage exit condition
   │    keep real gaps                          │
   └─────────────────────┬─────────────────────┘
                         │
   ┌─────────────────────▼─────────────────────┐
   │ 2. MAP metric ──► required state           │  which BACKEND emits the names?
   │    • always-emitted                        │  (rabbitmq dual-backend trap)
   │    • state-dependent  ─► seed              │  richest topology if targets
   │    • rate/counter     ─► activity-gen      │  span roles (mongo)
   │    • OSS can't emit   ─► pause, ask human   │
   └─────────────────────┬─────────────────────┘
                         │
   ┌─────────────────────▼─────────────────────┐
   │ 3. INVENTORY tests/                        │  compose · conftest · config
   │    reuse > author · extend existing yaml   │
   └─────────────────────┬─────────────────────┘
                         │
   ┌─────────────────────▼─────────────────────┐
   │ 4. AUTHOR fixture                          │
   │    full-coverage.compose:                  │
   │       live svc + seed + activity-gen       │
   │       (+ ACTIVITY_GEN=0 escape)            │
   │    activity-gen.sh  ·  evalya.yaml         │
   │       publish + provides.* + healthcheck   │
   └─────────────────────┬─────────────────────┘
                         │
   ┌─────────────────────▼─────────────────────┐
   │ 5. COVERAGE LOOP                           │
   │                                            │
   │   stand up fixture                         │
   │        │                                   │
   │        ▼                                   │
   │   run check ──► emitted set                │  ddev env agent … check -t 2 --json
   │        │        (multi-instance:           │  (-t 2 MANDATORY: OpenMetrics
   │        │         one per role/endpoint)    │   counters need 2 scrapes)
   │        ▼                                   │
   │   diff  uncovered = target − emitted       │
   │        │                                   │
   │        ├─ empty? ──────────── yes ─────────┼──►┐
   │        │                                   │   │
   │        └─ no: extend seed OR activity-gen  │   │
   │              (one change) ──┐              │   │
   │                             │              │   │
   │        ▲────────────────────┘  re-run      │   │
   │        (or: metric unreachable → document) │   │
   └────────────────────────────────────────────┘   │
                                                     │
   ┌─────────────────────────────────────────────◄──┘
   │ 6. DOCUMENT + FINISH                        │
   │    tests/README.md · lint                  │
   │    open PR (draft) ──► add changelog        │
   └────────────────────────────────────────────┘
```

## Worked example: rabbitmq

The coverage loop, traced against a real run:

| Coverage | What moved it |
|---|---|
| 21/56 | baseline (aggregated endpoint, no traffic) |
| 34/56 | add a second check instance for the management backend |
| 39/56 | point the management instance at the active queues (`queues_regexes: ['.*']`) |
| 54/56 | run the check twice (`-t 2`) so OpenMetrics counters appear |
| 54/56 | stop: `process.max_tcp_sockets`/`open_tcp_sockets` are 3.x-only, unreachable on 4.x |

Two findings this surfaced, now baked into the skill: a dashboard can mix check backends (needs
one instance per backend), and a single `agent check` scrape emits zero OpenMetrics counters.
