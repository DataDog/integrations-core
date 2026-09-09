# The redisdb exemplar

`redisdb/tests/` is the reference implementation. Read the real files; this annotates them and
calls out the transferable decisions. Do not copy redis-specific mechanics blindly — copy the
shape and re-derive the specifics from the target integration.

## Files

| File | Role |
|---|---|
| `redisdb/tests/evalya.yaml` | Declares the `redis-standalone` and `redis-full` tasks. |
| `redisdb/tests/compose/full-coverage.compose` | The `redis-full` environment: master + replica + seed + activity-gen + info-proxy. |
| `redisdb/tests/compose/standalone.compose` | Minimal single-instance fixture reused for `redis-standalone`. |
| `redisdb/tests/activity-gen.sh` | Continuous workload driving rate/counter metrics. |
| `redisdb/tests/proxy/` | Bespoke Go RESP proxy injecting INFO fields OSS Redis can't emit. |
| `redisdb/tests/README.md` | Prose explanation of the fixture. |

## evalya.yaml anatomy

```yaml
version: "1"
tasks:
  - id: redis-full
    task: ./compose/full-coverage.compose@info-proxy   # <compose file>@<entrypoint service>
    labels:
      evalya.io/publish: "true"                         # publish as a reusable federated fixture
      evalya.io/provides.DB_HOST: "{{ .hostname }}"     # consumers read these to reach the service
      evalya.io/provides.DB_PORT: "6379"
      evalya.io/provides.REDIS_PASSWORD: devops-best-friend
    env:
      - name: REDIS_PASSWORD
        value: devops-best-friend
    healthcheck:                                        # ready only when it can serve the check
      test: ["CMD-SHELL", "redis-cli --no-auth-warning -a \"$$REDIS_PASSWORD\" ping"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
```

Transferable rules:

- `task: ./compose/<file>.compose@<service>` — the `@service` is the environment's *entrypoint*.
  Gate it (via `depends_on`) so requesting it pulls up seed, workload, and any topology.
- `evalya.io/provides.<VAR>` is the contract consumers depend on. Name the vars for what the check's
  config needs (host, port, credentials). Use `{{ .hostname }}` for the host.
- The healthcheck must reflect *serving readiness*, not just process liveness.
- Keep a minimal task (`redis-standalone`) next to the full one; not every consumer wants the
  heavy environment.

## full-coverage.compose anatomy

Four service kinds, each mapping to a metric class from SKILL.md step 2:

1. **Live service** (`redis-master`, `redis-replica`). Topology exists only because target metrics
   demanded it: the replica exists so `INFO replication` reports a connected slave. Add a
   secondary/replica **only** when a target metric needs it.
2. **`seed`** — one-shot, `restart: "no"`, others wait on
   `condition: service_completed_successfully`. Primes state-dependent metrics (typed keys, TTLs,
   keyspace hits/misses, an eviction overfill, forced expiry) so naturally-derived counters are
   non-zero before the first scrape.
3. **`activity-gen`** — `restart: unless-stopped`, mounts `../activity-gen.sh`, `depends_on` the
   seed. Continuous traffic so rate/counter metrics stay non-zero across scrapes.
4. **Injection layer** (`info-proxy`) — **redis-specific and bespoke.** Only needed because the
   redis dashboards use fields OSS Redis never emits (managed-service, cluster, sentinel,
   RediSearch). Most integrations need no proxy. If yours does, that is a pause-and-consult point.

Details worth copying: an `ACTIVITY_GEN=0` host-env escape hatch (container stays up, no traffic);
no host port publish on the internal entrypoint (reach it over the compose network via the
`provides` label) to avoid clashing with a local instance.

## activity-gen.sh contract

- POSIX `sh`, `set -eu`.
- Consumes the connection details from the `provides.*` env (`DB_HOST`, `DB_PORT`, credentials).
- `ACTIVITY_GEN=0` → log and `exec sleep infinity` (idle but alive so dependents still start).
- Optional duration cap (`ACTIVITY_DURATION`, `0` = forever) for bounded CI runs.
- Loops the operations that move each rate/counter target metric, with periodic progress logs.
- Ends on a `PASS:` line when a bounded run completes.

The loop body is a checklist of the rate/counter target metrics — each line exists to move a
specific metric. Re-derive it from the target set, do not port redis's operations verbatim.
