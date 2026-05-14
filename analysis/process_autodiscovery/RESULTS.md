# Process Auto-Discovery Algorithm Analysis

**Date:** 2026-05-14 (revised after re-collection)  
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
1. Pre-flight skips:
   - **Fake caddy server** — integrations whose docker-compose only serves
     static fixtures via `caddy:*` images. No real service runs.
   - **Kubernetes-only environment** — integrations whose tests use the
     `datadog_checks.dev.kind` helper. The target service runs as a
     Kubernetes pod inside a Kind cluster's nested namespaces, and is not
     visible to host-level process discovery. Process auto-discovery is not
     relevant for these integrations.
2. `ddev env start <integration> <env>` (latest versioned environment). If
   the env was left up from a prior run, stop it first and retry once. If
   the start exits non-zero but new containers appeared on the host, treat
   it as a soft warning and proceed with collection — the target service is
   often live even when a sibling container's healthcheck failed.
3. Identify Docker container PIDs on the host by scanning `/proc/*/cgroup`
4. For each PID, run `sudo disco --pid <pid>` to obtain the USM `GeneratedName`
5. Read `/proc/<pid>/status` and `/proc/<pid>/cmdline` for process tree data
6. Save to `data/<integration>__<env>.json`
7. `ddev env stop`

Failed environments and pre-flight skips are recorded in `data/skipped.json`.

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
- **93** were successfully collected
- **51** were skipped (see breakdown below)

Of the 93 collected, only **66** had at least one non-infra service detected
by `disco`. The remaining 27 produced process trees in which the only
services labeled by `disco` were Datadog Agent components (`agent`,
`system-probe`, `security-agent`, `privateactionrunner`). The effective
target-service sample is therefore 66 integrations.

## Results

### Coverage

| Category | Count |
|---|---|
| Integrations collected | 93 |
| Skipped — kubernetes-only environment (target service runs as a pod) | 19 |
| Skipped — fake caddy server | 18 |
| Skipped — env start failed | 13 |
| Skipped — no environments found | 1 |

The 13 "env start failed" skips break down (by inspecting `details` in
`data/skipped.json`) as:

| Sub-reason | Count |
|---|---|
| Unsupported platform (Windows-only integrations) | 5 |
| `ddev env start` timed out after 300 s (operational) | 3 |
| Dependency build failure (missing native headers, local toolchain) | 2 |
| Docker pull / containerd mount lock | 1 |
| Other (mid-pull failure, env-specific tracebacks) | 2 |

An earlier run had 39 entries in this bucket; most were re-collected in this
revision. The remaining 13 are dominated by Windows-only integrations and
local toolchain issues that re-runs will not fix on this host. The skipped
set is therefore still non-random — but the operational noise from
already-running envs and transient Docker Hub pull failures has been removed.

Integrations skipped due to fake caddy are those where the test environment
serves static fixture files via Caddy instead of running the real service
(e.g., `kubernetes_cluster_autoscaler`, `silk`, `appgate_sdp`). These are not
meaningful for process tree analysis.

Integrations skipped due to "kubernetes-only environment" are detected by
the presence of `datadog_checks.dev.kind` imports in their test code. Their
target service runs as a Kubernetes pod inside a Kind cluster's nested
network/PID namespaces — `disco` running on the host cannot reach into those
namespaces, so process auto-discovery is not relevant for these integrations
(`argo_*`, `cilium`, `fluxcd`, `istio`, `keda`, `kubevirt_*`, `kuma`,
`kyverno`, `strimzi`, `tekton`, `traefik_mesh`, `velero`, `weaviate`,
`cert_manager`, `calico`).

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
| **PASS** (1 main for that generated_name in this env) | 118 service/integration pairs |
| **WARN (N>1)** | 28 service/integration pairs |
| No non-infra service data (disco returned nothing useful) | 27 integrations |

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

All 28 WARN cases fall into four categories:

#### Category 1: Multi-node cluster test environments (expected, not a problem)

The test environments run multi-node clusters. Each node is an independent service
instance in a separate container and legitimately requires its own integration check.
WARN (N=nodes) is correct behavior here.

| Integration | Service | N | Notes |
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
| voltdb | `org.voltdb.VoltDB` | 3 | 3-node cluster |
| singlestore | `memsqld` | 2 | aggregator + leaf node |
| citrix_hypervisor | `app` | 6 | 6 mock XenServer API endpoints |
| postgres | `postgres` | 4 | 4 independent DB instances in separate containers |
| vault | `vault`, `consul` | 2, 2 | vault leader + replica, consul leader + worker |
| tls | `nginx` | 3 | `nginx-tls1-2`, `nginx-tls1-3`, `nginx-main` — three TLS configurations |

#### Category 2: Multiple independent instances on different ports (expected, not a problem)

| Integration | Service | Details |
|---|---|---|
| redisdb | `redis-server` | 3 instances on ports 6380, 6381, 6382 — each is a separate Redis instance |
| prefect | `prefect` | `prefect server` + `prefect worker` — two distinct components sharing a generated name |

#### Category 3: Sibling worker pool — algorithm does not dedupe siblings

These are cases where many *sibling* processes share a `generated_name` and
their common parent has a *different* `generated_name` (or no service data).
The current algorithm only filters parent-child duplicates, so each sibling
becomes its own "main." In production this would spawn N integration
instances for a single logical service.

| Integration | Service | N | Parent process | Details |
|---|---|---|---|---|
| ray | `ray` | 21 | `raylet` (gn=`raylet`) | 21 `ray::IDLE`/`ray::ServeController`/`ray::ServeReplica` worker processes are all children of a single `raylet`. Disco labels each as `ray` while the parent is `raylet`, so no dedup happens. A real Ray cluster on this host would yield 21 duplicate integration instances. |
| squid | `tail` | 2 | `entrypoint.sh` (gn=`None`) | `tail -F .../access.log` and `tail -F .../cache.log` — two sibling log-tailers under the squid container entrypoint. |

This is a real algorithm limitation, not a disco issue (disco's labels are
correct in the Ray case — the worker processes really are Python processes
named `ray`). Filtering would require sibling-grouping logic: if N siblings
share a `generated_name` and their common parent has a different (or no)
`generated_name`, collapse them. The current algorithm doesn't do this.

#### Category 4: disco false positives surfaced as WARN (disco issue)

| Integration | Service | Details |
|---|---|---|
| couchbase | `tmp` | 3 Erlang/OTP `beam.smp` processes labeled `tmp` — a generic disco fallback name for unrecognized Erlang VMs. Each has a different parent (separate Erlang subtrees), so it is not the sibling case above. |

The actual target services (`squid`, `couchbase`) correctly show PASS in
their respective rows.

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

27 integrations produced process trees but `disco` detected no non-infra
services. These are mostly:

- **Kubernetes integrations** that don't use the ddev kind helper (so the
  pre-flight skip didn't catch them) but where the actual service still
  runs inside a Kubernetes-style container disco cannot reach
  (`kube_*`, `kubernetes_state`, `nginx_ingress_controller`, etc.)
- **Agent-only integrations** where no external service runs
  (`dns_check`, `tcp_check`, `ssh_check`, `system_core`, `system_swap`,
  `network`)
- **Services where disco cannot yet identify the process**
  (`postfix`, `vsphere/vcsim`, `proxmox`, `teradata`, `lustre`)
- **Build/healthcheck races** — e.g. `tomcat` was collected after the
  start-warning fast path, but the JVM container was still in `Created`
  state at probe time, so only an unrelated single process was captured.

These integrations are not relevant for process auto-discovery, or would
need a re-collection with longer warmup to be conclusive.

## Conclusion

**Narrow claim, well supported:** the collected sample did not reveal a
parent/child deduplication failure. In every case where `disco` labeled both
a parent and one or more of its descendants with the same `generated_name`,
the algorithm selected exactly one main process and filtered the rest. No
genuine worker was incorrectly promoted to main in this sample under that
specific topology.

This holds across the parent/child deduplication patterns that the sample
exercised:
- C servers with pre-fork workers labeled with the same name as the master
  (e.g. `nginx`)
- Python pre-fork pools (`gunicorn`)
- JVM services with forked child JVMs that get distinct names
  (`sonar-application-*` vs. its Elasticsearch / WebServer / CeServer
  children — children correctly become their own services)

**Algorithm limitation surfaced by this run:** the algorithm does *not*
dedupe **siblings** with the same `generated_name` whose common parent has a
different `generated_name`. The clearest example is **ray**, where 21
`ray::IDLE` / `ray::ServeReplica` worker processes are all children of a
single `raylet` (gn=`raylet`). Because the parent is `raylet`, not `ray`,
each sibling worker passes the `parent.GeneratedName != process.GeneratedName`
check and becomes its own "main." In production this would create 21
duplicate integration instances for a single Ray cluster node. The same
pattern, less dramatically, shows up in `squid tail` (N=2). See Category 3
above. Fixing this requires sibling-grouping logic in the algorithm — when
N siblings share a `generated_name` and their common parent has a different
(or no) `generated_name`, collapse them.

**Broader caveats that limit how far the narrow claim generalizes:**

1. **Sample coverage is limited.** Of 144 integrations with E2E tests, 93
   were collected and 66 of those had a non-infra service detected. The 51
   skipped integrations include 19 K8s-only environments (process discovery
   is not relevant — target service runs as a pod inside Kind's nested
   namespaces), 18 fake-caddy fixtures (no real service runs), and 13 env
   start failures dominated by Windows-only integrations and local
   toolchain issues. K8s-only and caddy-fixture integrations are
   structurally out of scope rather than gaps in coverage.
2. **The PASS count overstates correctness.** "118 PASS" counts each
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
   is the basis for the "soft warning" path in step 2 of the workflow:
   when start exits non-zero but the delta has new containers, collection
   still proceeds. Files written under this path have a `start_warning` key
   under `disco_raw` for traceability.

**Recommendations:**

- **Algorithm:** add sibling-grouping deduplication for the Ray pattern.
- **Disco follow-ups:**
  1. Improve naming for Erlang/OTP processes (couchbase `tmp`).
  2. Avoid labeling log-tailing helper processes as services
     (squid `tail`, nifi `tail`, riak `tail`).
  3. Avoid labeling generic shell wrappers and container helper daemons as
     services (`sh`, `rsyslogd`, `node_exporter`, container-side
     `supervisord`).

Closing the remaining algorithm-level gap on the *postgres-style untested
workers* would require extending the analyzer to also consider processes
with `has_service_data: false` whose parent does have service data — that is
the path the production algorithm would actually take on those workers.

## Files

| File | Description |
|---|---|
| `analysis/scripts/process_analyze.py` | Collection and analysis tool |
| `analysis/process_autodiscovery/data/*.json` | Raw collected process data (93 files) |
| `analysis/process_autodiscovery/data/skipped.json` | Skipped integration log |
| `analysis/process_autodiscovery/results/analysis_2026-05-14T09-13-28.json` | Final analysis output (revised) |
| `docs/superpowers/specs/2026-05-13-process-autodiscovery-analysis-design.md` | Design spec |
| `docs/superpowers/plans/2026-05-13-process-autodiscovery-analysis.md` | Implementation plan |
