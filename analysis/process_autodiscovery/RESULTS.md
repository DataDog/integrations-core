# Process Auto-Discovery Algorithm Analysis

**Date:** 2026-05-13  
**Branch:** vitkyrka/process-analyze  
**Tool:** `analysis/scripts/process_analyze.py`

## Background

The Datadog Agent's process auto-discovery feature (`ProcessListener`) can automatically
apply integration configs to running services detected on the host. A key concern is that
services like nginx or Apache spawn multiple sub-processes (master + workers), and creating
a separate integration instance for each would produce duplicate metrics.

The agent addresses this with `isMainProcessForService`:

```go
func isMainProcessForService(process *workloadmeta.Process, wmeta workloadmeta.Component) bool {
    if process.Ppid == 0 || process.Ppid == 1 {
        return true
    }
    parent, err := wmeta.GetProcess(process.Ppid)
    if err != nil {
        return true
    }
    if parent.Service == nil {
        return true
    }
    return parent.Service.GeneratedName != process.Service.GeneratedName
}
```

A process is the "main" process for its service unless its parent is in the process store,
has service data, and shares the same `GeneratedName`. This filters out worker/child processes
whose parent is the same service.

**Question:** Does this algorithm correctly identify exactly one main process per service
across the integrations in this repository?

## Methodology

### Tool design

`analysis/scripts/process_analyze.py` has two decoupled modes:

**`collect`** — for each integration with a `test_e2e.py` file:
1. Pre-flight: skip if the integration uses a fake caddy server (static fixture serving)
2. `ddev env start <integration> <env>` (latest versioned environment)
3. Identify Docker container PIDs on the host by scanning `/proc/*/cgroup`
4. For each PID, run `sudo disco --pid <pid>` to obtain the USM `GeneratedName`
5. Read `/proc/<pid>/status` and `/proc/<pid>/cmdline` for process tree data
6. Save to `data/<integration>__<env>.json`
7. `ddev env stop`

Failed environments and fake-caddy integrations are recorded in `data/skipped.json`.

**`analyze`** — loads saved JSON files and applies a Python translation of
`isMainProcessForService` to every service process. Produces a verdict per service:
- **PASS** — exactly 1 main process selected
- **WARN (N=k)** — k main processes selected (k ≠ 1)

### Key implementation note: `sudo` required for disco

Running `disco` without elevated privileges returns empty service data for container
processes. The USM service discovery module needs access to process namespaces and
network socket information that is restricted to root. Running with `sudo` correctly
returns `GeneratedName` values matching what the agent would compute in production.

### Scope

- **144** integrations have `test_e2e.py` files in this repository
- **86** were successfully collected
- **58** were skipped (see breakdown below)

Of the 86 collected, only **60** had at least one non-infra service detected by
`disco`. The remaining 26 produced process trees in which the only services
labeled by `disco` were Datadog Agent components (`agent`, `system-probe`,
`security-agent`, `privateactionrunner`). The effective target-service sample
is therefore 60 integrations, not 86 or 144.

## Results

### Coverage

| Category | Count |
|---|---|
| Integrations collected | 86 |
| Skipped — fake caddy server | 18 |
| Skipped — env start failed | 39 |
| Skipped — no environments found | 1 |

The 39 "env start failed" skips are not a clean "K8s / Windows / cloud-only"
slice. They break down (by inspecting `details` in `data/skipped.json`) as:

| Sub-reason | Count |
|---|---|
| Environment already running (operational) | 14 |
| Docker pull / registry rate-limit / build copy errors (operational) | 10 |
| `ddev env start` timed out after 300 s (operational) | 6 |
| Unsupported platform (Windows-only integrations) | 5 |
| Dependency build failure (missing native headers, local toolchain) | 3 |
| Kind / Kubernetes cluster setup failed | 1 |

Most of these are environmental, not architectural — the same integrations
might collect cleanly on a different machine or with a warmed Docker cache.
This makes the skipped set non-random, so it should not be used to generalize
about the population of unsampled integrations.

Integrations skipped due to fake caddy are those where the test environment
serves static fixture files via Caddy instead of running the real service
(e.g., `kubernetes_cluster_autoscaler`, `silk`, `appgate_sdp`). These are not
meaningful for process tree analysis.

### Algorithm verdicts

Excluding the Datadog agent infra processes (`agent`, `system-probe`,
`security-agent`, `privateactionrunner`) that are present in every environment.

The analyzer groups processes by `generated_name` within a single collected
environment and runs `isMainProcessForService` against every process that has
`has_service_data: true`. A verdict is emitted per (integration, generated_name)
pair:

- **PASS** = exactly one main process was selected for that `generated_name`
  in this environment.
- **WARN (N=k)** = k main processes were selected (k ≠ 1).

PASS does *not* mean "exactly one main process per service in production." It
means "within this single collected environment, the deduplication produced one
main for this `generated_name`." Multiple legitimate instances (e.g., a 3-node
cluster) correctly produce WARN — that is the expected outcome, not a failure.

| Verdict | Count |
|---|---|
| **PASS** (1 main for that generated_name in this env) | 108 service/integration pairs |
| **WARN (N>1)** | 25 service/integration pairs |
| No non-infra service data (disco returned nothing useful) | 26 integrations |

### PASS cases — algorithm exercised successfully

Representative examples. Two distinct sub-classes are mixed in here:

1. **Algorithm actively deduplicated** — `disco` labeled the workers with the
   same `generated_name` as the master, and `isMainProcessForService`
   correctly filtered them. Example: `nginx`, `airflow / gunicorn`.
2. **Algorithm was not exercised** — `disco` labeled only one process per
   `generated_name` (workers had `has_service_data: false`), so the analyzer
   never had to deduplicate. The PASS verdict in this sub-class is consistent
   with a working algorithm but does *not* constitute evidence that the
   algorithm correctly handles workers in that integration. Example: `postgres`
   — the checkpointer/walwriter/bgwriter workers had no service data and were
   never passed to `is_main_process`.

| Integration | Service | Outcome |
|---|---|---|
| nginx | `nginx` | 1 master + 1 worker, both labeled `nginx`, worker filtered by algorithm ✅ |
| airflow | `gunicorn` | master + workers all labeled `gunicorn`, workers filtered by algorithm ✅ |
| postgres | `postgres` | 1 master; background workers (checkpointer, walwriter, autovacuum, bgwriter) carried `has_service_data: false` and were not passed to the algorithm — algorithm not exercised |
| haproxy | `haproxy` | 1 main (only one labeled process) |
| rabbitmq | `rabbitmq` | 1 main |
| scylla | `scylla` | 1 main (siblings under `supervisord` are separate generated names — see false-positive note below) |
| sonarqube | `sonar-application-*` | 1 main; child JVMs (Elasticsearch, WebServer, CeServer) correctly separate ✅ |
| pulsar | `pulsar` | 1 main |
| nifi | `nifi` | 1 main, framework subprocess correctly separate ✅ |
| ceph | `ceph-mon`, `ceph-mgr`, `ceph-osd`, `ceph-mds`, `radosgw` | Each daemon correctly 1 main ✅ |
| confluent_platform | `zookeeper`, `kafka.Kafka`, `io.confluent.*` (5 services) | All correctly 1 main each ✅ |

The cases where the algorithm was *actively* exercised (master and worker
sharing a `generated_name`) are the ones that exercise the deduplication
path. Among the integrations sampled, the clearest examples are
master/worker C servers (`nginx`) and Python pre-fork pools (`gunicorn`).

### WARN cases — classified

All 25 WARN cases fall into three categories:

#### Category 1: Multi-node cluster test environments (expected, not a problem)

The test environments run multi-node clusters. Each node is an independent service
instance in a separate container and legitimately requires its own integration check.
WARN (N=nodes) is correct behavior here.

| Integration | Service | Nodes | Notes |
|---|---|---|---|
| cassandra_nodetool | `cassandra` | 2 | 2-node cluster |
| clickhouse | `clickhouse-server` | 6 | 6-shard cluster |
| consul | `consul` | 3 | 3-node HA cluster |
| etcd | `etcd` | 3 | 3-node HA cluster |
| glusterfs | `glusterd`, `glusterfsd`, `glusterfs` | 2 each | 2-node cluster |
| hazelcast | `HazelcastServerCommandLine` | 3 | 3-node cluster |
| hdfs_datanode | `hadoop` | 2 | 2-node HDFS |
| hdfs_namenode | `hadoop` | 2 | 2-node HDFS |
| kafka_consumer | `kafka.Kafka` | 2 | 2-broker cluster |
| confluent_platform | `kafka` | 2 | 2-broker cluster |
| mapreduce | `hadoop` | 6 | 6-node cluster |
| rethinkdb | `rethinkdb` | 4 | 4-node cluster |
| spark | `spark`, `app` | 4, 2 | master + workers; each worker independent |
| traefik_mesh | `coredns` | 2 | 2 CoreDNS instances |
| voltdb | `org.voltdb.VoltDB` | 3 | 3-node cluster |
| singlestore | `memsqld` | 2 | aggregator + leaf node |
| citrix_hypervisor | `app` | 6 | 6 mock XenServer API endpoints |
| postgres | `postgres` | 4 | 4 independent DB instances in separate containers |

#### Category 2: Multiple independent instances on different ports (expected, not a problem)

| Integration | Service | Details |
|---|---|---|
| redisdb | `redis-server` | 3 instances on ports 6380, 6381, 6382 — each is a separate Redis instance |
| prefect | `prefect` | `prefect server` + `prefect worker` — two distinct components sharing a generated name |

#### Category 3: disco false positives surfaced as WARN (disco issue, not algorithm issue)

| Integration | Service | Details |
|---|---|---|
| squid | `tail` | `tail -F /var/log/squid/access.log` and `tail -F /var/log/squid/cache.log` detected as services. These are log-tailing helper processes, not real services. |
| couchbase | `tmp` | 3 Erlang/OTP beam processes labeled `tmp` — a generic disco name for unrecognized Erlang processes. |

In both cases the actual target service (`squid`, `couchbase`) correctly shows PASS.

### disco false positives surfaced as PASS

There is a related class of false positives that does *not* appear in the WARN
table because each occurs as a single instance: the algorithm emits PASS, but
the `generated_name` is not the integration's target service. From a
user-facing auto-discovery perspective these would create unwanted integration
instances. Examples in the sample:

| Integration | generated_name | What it actually is |
|---|---|---|
| nifi | `tail` | `tail -F --pid=79 /opt/nifi/nifi-current/logs/nifi-app.log` — log tailer |
| riak | `tail` | log tailer |
| scylla | `supervisord` | container init / process supervisor |
| scylla | `rsyslogd` | container syslog daemon |
| scylla | `node_exporter` | Prometheus node-exporter bundled in the Scylla image |
| elastic | `sh` | shell wrapper |
| silverstripe_cms | `sh` | shell wrapper |

`supervisord` is a legitimate target service of the dedicated `supervisord`
integration, so its PASS row is not always a false positive — context matters.

These rows mean the "108 PASS" headline overstates how often the
auto-discovery surface area would be correct end-to-end. The algorithm itself
is doing what it is asked to do (one main per `generated_name`), but the input
labels are not always the integration's target service.

### Integrations with no service data detected

26 integrations produced process trees but disco detected no services. These are mostly:

- **Kubernetes integrations** where the actual service runs inside a Kind cluster
  with nested network namespaces that disco cannot reach from the host
  (`kube_*`, `kubernetes_state`, `nginx_ingress_controller`, etc.)
- **Agent-only integrations** where no external service runs
  (`dns_check`, `tcp_check`, `ssh_check`, `system_core`, `system_swap`, `network`)
- **Services where disco cannot yet identify the process**
  (`postfix`, `vsphere/vcsim`, `proxmox`, `teradata`, `lustre`)

These integrations are not relevant for process auto-discovery since either
the service does not run as a host process or disco cannot detect it yet.

## Conclusion

**Narrow claim, well supported:** the collected sample did not reveal a
parent/child deduplication failure. In every case where `disco` labeled both a
parent and one or more of its descendants with the same `generated_name`, the
algorithm selected exactly one main process and filtered the rest. No genuine
worker was incorrectly promoted to main in this sample.

This holds across the deduplication patterns that the sample did exercise:
- C servers with pre-fork workers labeled with the same name as the master
  (e.g. `nginx`)
- Python pre-fork pools (`gunicorn`)
- JVM services with forked child JVMs that get distinct names
  (`sonar-application-*` vs. its Elasticsearch / WebServer / CeServer children
  — children correctly become their own services)

**Broader caveats that limit how far this generalizes:**

1. **Sample coverage is limited.** Of 144 integrations with E2E tests, only 86
   were collected and only 60 of those had a non-infra service detected. The
   58 skipped integrations include 14 already-running envs, 10 docker
   pull/registry issues, 6 timeouts, and other operational failures — that
   skip set is non-random, so the unsampled population may behave differently.
2. **The PASS count overstates correctness.** "108 PASS" counts each
   (integration, generated_name) pair, including legitimate multi-instance
   passes and the false-positive helper processes called out above
   (`tail`, `sh`, container-side `supervisord`/`rsyslogd`/`node_exporter`).
3. **Some integrations did not exercise the algorithm at all.** For example,
   the postgres background workers (`checkpointer`, `bgwriter`, `walwriter`,
   `autovacuum`, io workers) had `has_service_data: false`. They were
   excluded from the analyzer's input by the `has_service_data` filter, not
   by the algorithm. The algorithm's behavior on those workers is therefore
   unknown from this data.
4. **Algorithm correctness depends on `disco` correctness.** If `disco`
   labels a child process with a *different* `generated_name` than its
   parent (or labels a non-service process), the algorithm will faithfully
   treat them as independent services — which is correct given its input,
   but may be wrong end-to-end. The `tail` / `sh` / container-helper PASS
   rows are examples.
5. **Container detection differs from the design spec.** The spec describes
   filtering containers by ddev name/prefix; the implementation instead
   computes the delta of `docker ps` before and after `ddev env start`. This
   is why "Environment already running" rows in `skipped.json` produce no
   collected data — the delta is empty.

**Recommendation:** the data supports the narrow claim that no
parent/child deduplication failure was observed in the cases the algorithm was
actually exercised on. The disco-side follow-ups remain:
1. Improve naming for Erlang/OTP processes (couchbase `tmp`)
2. Avoid labeling log-tailing helper processes as services (squid `tail`,
   nifi `tail`, riak `tail`)
3. Avoid labeling generic shell wrappers and container helper daemons as
   services (`sh`, `rsyslogd`, `node_exporter`, container-side
   `supervisord`)
4. Extend disco to reach processes inside nested Kubernetes network namespaces

Closing the remaining algorithm-level gap would require either (a) collecting
data for the currently skipped integrations on a clean machine, or (b)
extending the analyzer to also consider processes with `has_service_data:
false` whose parent does have service data — that is the path the production
algorithm would actually take on those workers.

## Files

| File | Description |
|---|---|
| `analysis/scripts/process_analyze.py` | Collection and analysis tool |
| `analysis/process_autodiscovery/data/*.json` | Raw collected process data (86 files) |
| `analysis/process_autodiscovery/data/skipped.json` | Skipped integration log |
| `analysis/process_autodiscovery/results/analysis_2026-05-13T17-29-06.json` | Final analysis output |
| `docs/superpowers/specs/2026-05-13-process-autodiscovery-analysis-design.md` | Design spec |
| `docs/superpowers/plans/2026-05-13-process-autodiscovery-analysis.md` | Implementation plan |
