# onboard-evalya

Onboard a Datadog integration to evalya: build a `<integration>-full` fixture that spins up a
live instance plus a workload that drives the check to emit 100% of the metrics used in the
integration's OOTB dashboards and recommended monitors. Modeled on the `redisdb/tests/` exemplar.

Invoke with `/onboard-evalya <integration>` (or ask to "onboard <x> to evalya").

## Layout

| Path | Role |
|---|---|
| `SKILL.md` | The agent-facing workflow (what the model executes). |
| `references/redis-exemplar.md` | Annotated walkthrough of the redisdb fixture. |
| `references/coverage-loop.md` | The emitted-vs-target diff mechanism, the `-t 2` rule, multi-instance handling. |
| `scripts/asset_metrics.py` | Deterministic extractor: dashboard + monitor metrics joined to `metadata.csv`. |

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
   │ 1. TARGET                                  │  asset_metrics.py
   │    dashboards/*.json + monitors/*.json     │  join metadata.csv
   │        ──►  metric set (union)             │  = coverage exit condition
   │    triage "missing": drop system.*,        │
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
   │        ├─ empty? ─────────────── yes ──────┼──►┐
   │        │                                   │   │
   │        └─ no, escalate per metric:         │   │
   │             1. live: seed OR activity-gen  │   │
   │             2. can't emit live? serve      │   │   reuse tests/fixtures/
   │                tests/fixtures/ via          │   │   (frozen values,
   │                proxy/static → fixture-backed│   │    mark as NOT live)
   │             3. neither → unreachable        │   │
   │                     │  (1 or 2) re-run      │   │
   │        ▲────────────┘                      │   │
   └────────────────────────────────────────────┘   │
                                                     │
   ┌─────────────────────────────────────────────◄──┘
   │ 6. DOCUMENT + FINISH                        │
   │    tests/README.md · lint                  │
   │    open PR (draft) ──► add changelog        │
   └────────────────────────────────────────────┘
```

## Worked example: rabbitmq

The coverage loop, traced against a real run over the **dashboard** target (56 metrics):

| Coverage | What moved it |
|---|---|
| 21/56 | baseline (aggregated endpoint, no traffic) |
| 34/56 | add a second check instance for the management backend |
| 39/56 | point the management instance at the active queues (`queues_regexes: ['.*']`) |
| 54/56 | run the check twice (`-t 2`) so OpenMetrics counters appear |
| 54/56 | stop: `process.max_tcp_sockets`/`open_tcp_sockets` are 3.x-only, unreachable on 4.x |

This run predates adding monitors to the target. The recommended monitors contribute two more
rabbitmq metrics not on any dashboard (`rabbitmq.alarms.free_disk_space.watermark`,
`rabbitmq.queue.messages_unacknowledged.rate`), which a fresh run would need to verify and, if
absent, drive from the workload. That is exactly why monitors are part of the target.

Two findings this surfaced, now baked into the skill: a dashboard (or monitor set) can mix check
backends (needs one instance per backend), and a single `agent check` scrape emits zero
OpenMetrics counters.
