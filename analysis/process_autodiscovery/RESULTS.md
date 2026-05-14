# Process Auto-Discovery Algorithm Analysis

**Date:** 2026-05-14  
**Branch:** vitkyrka/process-analyze  
**Tools:** `analysis/scripts/process_analyze.py`, `analysis/scripts/process_cel_eval.py`

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

### How the algorithm fits with CEL filtering

`isMainProcessForService` is only the first filter in the agent's
`ProcessListener`
([`comp/core/autodiscovery/listeners/process.go`][listener]). The second
filter is a per-integration **CEL expression** evaluated against a
`FilterProcess` with fields `name` (the process `Comm`, populated from
`/proc/<pid>/status` Name — note the 15-character kernel limit),
`cmdline` (joined cmdline), and `args` (cmdline list) — see
[`pkg/proto/datadog/workloadfilter/workloadfilter.proto`][proto] and
[Scheduling Checks with Autodiscovery based on Service Discovery][cel-doc].
Each integration that opts in to process auto-discovery provides a CEL
expression that selects which processes it actually wants — e.g.
`process.name == 'raylet'` for the Ray raylet binary,
`process.name == 'java' && 'kafka.Kafka' in process.args` for a Kafka
broker JVM.

CEL changes how the algorithm's results should be interpreted. The
algorithm's job is *not* to identify "the right process for integration X."
It only has to reduce the candidate set to one main per `generated_name`
within a process tree. Selecting the right candidate among the surviving
mains is the integration author's job via CEL.

**Note on test methodology.** Every process in this analysis is running
inside a docker container (the test environments use `docker-compose` for
practical reasons — running 100+ services bare-metal in CI is not
tractable). The container packaging is a test convenience: the *topologies*
(master/worker, sibling pools, multi-instance clusters) are the same ones
that would appear with host-resident services in production. The
production goal is to support process auto-discovery for processes running
*outside* containers, and this is the scenario the algorithm's correctness
matters for.

[listener]: https://github.com/DataDog/datadog-agent/blob/main/comp/core/autodiscovery/listeners/process.go
[proto]: https://github.com/DataDog/datadog-agent/blob/main/pkg/proto/datadog/workloadfilter/workloadfilter.proto
[cel-doc]: https://datadoghq.atlassian.net/wiki/spaces/CONTP/pages/5389616306/Scheduling+Checks+with+Autodiscovery+based+on+Service+Discovery

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

- **192** integrations have e2e tests in this repository. The collector
  picks them up by two conventions: a dedicated `tests/test_e2e.py`
  file (newer integrations) or `@pytest.mark.e2e` markers inside other
  test files like `tests/test_<integration>.py` (older integrations
  including apache, mysql, cassandra, kafka, gunicorn, presto, etc.).
- **132** were successfully collected
- **60** were skipped (see breakdown below)

Of the 132 collected, **98** had at least one non-infra service
detected by `disco`. The remaining 34 produced process trees in which
the only services labeled by `disco` were Datadog Agent components
(`agent`, `system-probe`, `security-agent`, `privateactionrunner`).
The effective target-service sample is therefore 98 integrations.

## Results

### Coverage

| Category | Count |
|---|---|
| Integrations collected | 132 |
| Skipped — kubernetes-only environment (target service runs as a pod) | 20 |
| Skipped — fake caddy server | 18 |
| Skipped — env start failed | 20 |
| Skipped — no environments found | 2 |

The 20 "env start failed" skips break down (by inspecting `details` in
`data/skipped.json`) as:

| Sub-reason | Count |
|---|---|
| Unsupported platform (Windows-only integrations) | 7 |
| `ddev env start` timed out after 300 s (operational) | 3 |
| Docker pull / registry rate-limit / build failure | 5 |
| Dependency build failure (missing native headers, local toolchain) | 2 |
| Incompatible Python (e.g. py2.7 required, unavailable) | 1 |
| Other (mid-pull failure, env-specific tracebacks) | 2 |

These are dominated by Windows-only integrations and local toolchain
issues that re-runs will not fix on this host. The skipped set is
non-random and should not be used to generalize about the unsampled
population.

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
| **PASS** (1 main for that generated_name in this env) | 161 service/integration pairs |
| **WARN (N>1)** | 36 service/integration pairs |
| No non-infra service data (disco returned nothing useful) | 34 integrations |

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

#### Category 3: Sibling worker pool — algorithm doesn't dedupe, CEL does

These are cases where many *sibling* processes share a `generated_name` and
their common parent has a *different* `generated_name` (or no service data).
The algorithm only filters parent-child duplicates, so each sibling
becomes its own "main."

| Integration | Service | N | Parent process | Details |
|---|---|---|---|---|
| ray | `ray` | 21 | `raylet` (gn=`raylet`) | 21 `ray::IDLE`/`ray::ServeController`/`ray::ServeReplica` worker processes are all children of a single `raylet`. Disco labels each as `ray` while the parent is `raylet`, so no parent-child dedup happens. |
| squid | `tail` | 2 | `entrypoint.sh` (gn=`None`) | `tail -F .../access.log` and `tail -F .../cache.log` — two sibling log-tailers under the squid container entrypoint. |

This is verified in [the CEL evaluation
section](#cel-evaluation-against-the-collected-data): for `ray`,
`process.name == 'raylet' || process.name == 'gcs_server' || (process.name == 'python' && 'ray.util.client.server' in process.args)`
reduces 29 mains to 3 survivors (the 21 `ray::IDLE` workers are correctly
dropped, along with the dashboard, log monitor, and other auxiliary
python processes). For `squid`, `process.name == 'squid'` reduces 5 mains
to 1. The algorithm's job is to reduce the candidate set to one main per
`generated_name`; the integration author's job is to pick the right one
via CEL. The N here reflects how disco labels processes, not how many
integration instances would be created.

#### Category 4: disco false positives surfaced as WARN — CEL handles it

| Integration | Service | Details |
|---|---|---|
| couchbase | `tmp` | 3 Erlang/OTP `beam.smp` processes labeled `tmp` — a generic disco fallback name for unrecognized Erlang VMs. Each has a different parent (separate Erlang subtrees), so it is not the sibling case above. |

The couchbase integration's CEL rule
(`process.name == 'beam.smp' && process.args.exists(a, a.startsWith('/opt/couchbase'))`)
reduces couchbase's 12 mains to 3 survivors, one per `beam.smp` role
(babysitter, ns_server, ns_couchdb). The generic `tmp` candidates that
sit outside the `/opt/couchbase` install prefix are filtered out. As
above, this WARN row does not correspond to runaway duplicate
integration instances in production.

### disco false positives surfaced as PASS

There is a related class of false positives that does *not* appear in the
WARN table because each occurs as a single instance: the algorithm emits
PASS, but the `generated_name` is not the integration's target service.
Examples in the sample:

| Integration | generated_name | What it actually is |
|---|---|---|
| nifi | `tail` | `tail -F --pid=79 /opt/nifi/nifi-current/logs/nifi-app.log` — log tailer |
| riak | `tail` | log tailer |
| scylla | `supervisord` | container init / process supervisor |
| scylla | `rsyslogd` | container syslog daemon |
| scylla | `node_exporter` | Prometheus node-exporter bundled in the Scylla image |
| elastic | `sh` | shell wrapper |
| silverstripe_cms | `sh` | shell wrapper |

These rows are produced by disco labeling helper processes as named
services. They show that the *raw candidate set* after the algorithm
contains noise, but per-integration CEL rules filter them out before any
check instance is scheduled: the nifi integration's CEL targets the nifi
JVM, not `tail`; scylla's CEL targets `scylla`, not the bundled
`rsyslogd`/`node_exporter`. `supervisord` is also a legitimate target of
the dedicated `supervisord` integration, so context matters per row.

In short: the algorithm's job is to produce one main per `generated_name`,
and these rows are the algorithm doing that correctly. CEL is the layer
that turns this candidate set into integration instances.

### Integrations with no service data detected

26 integrations produced process trees but `disco` labeled only Datadog
Agent components (no target service). Inspecting each test setup shows
this is almost entirely about the *test environment*, not about disco
failing to recognize a service that was present.

**A. No external service to discover (11).** The check operates on
files, `/proc` entries, or network probes — there is no daemon for
process auto-discovery to find, in test or in production.

| Integration | Why |
|---|---|
| `directory` | walks a filesystem path |
| `dns_check` | sends DNS queries to a configured server |
| `duckdb` | embeds the DuckDB engine in-process |
| `lustre` | parses `/proc/fs/lustre/*` |
| `network` | parses `/proc/net/*` |
| `postfix` | reads mail queue files on disk |
| `ssh_check` | probes SSH (active probe, not a daemon to discover) |
| `system_core` | parses `/proc/stat` |
| `system_swap` | parses `/proc/meminfo` and friends |
| `tcp_check` | probes a TCP port |
| `mapr` | uses the MapR client library; no daemon on the same host |

**B. Test exercises the "no backend present" failure path (14).** The
e2e test config points at a localhost endpoint that no test container
provides, and the assertion is that the check reports `CRITICAL` or
`UNKNOWN`. In production the integration would be aimed at a running
endpoint, but the test environment intentionally does not bring one
up — so there is no service process to collect.

Test-fixture style is one of:
- Python `MockResponse` / mocked HTTP API (e.g. `ecs_fargate`,
  `proxmox`, `vsphere`).
- Config pointing at `https://localhost:443/metrics` (or similar)
  with no listener (`kube_apiserver_metrics`,
  `kube_controller_manager`, `kube_dns`, `kube_metrics_server`,
  `kube_proxy`, `kube_scheduler`, `kubernetes_state`,
  `nginx_ingress_controller` — these don't use the
  `datadog_checks.dev.kind` helper so they aren't covered by the
  Kubernetes-only pre-flight; they just point at a nonexistent local
  Prometheus endpoint).
- Specialized hardware/cloud systems with no usable local mock
  (`ibm_i`, `teradata`, `openstack`).

For process auto-discovery purposes these integrations cannot be
evaluated from this sample — but the gap is in the test fixture, not
in the agent's discovery pipeline.

**C. Container startup race not fully covered (1).**

| Integration | Detail |
|---|---|
| `arangodb` | The arangodb container's entrypoint runs `arango-init-database` first and only then exec's `arangod`. `wait_for_containers_started` returns once the container's docker state leaves `Created`/`restarting`, but the application is still in its init phase at that moment. The collector captures `entrypoint.sh` and `arango-init-database` but not the eventual `arangod` process. Extending the collector to wait for application readiness (rather than just docker container state) would close this gap. Documented rather than fixed here. |

The collector waits for new containers to leave `Created`/`restarting`
state before sampling PIDs (`wait_for_containers_started` in
`process_analyze.py`) so that JVM containers with slow startup
(notably `tomcat` and `temporal`) are sampled after their main process
is running.

## CEL evaluation against the collected data

The discussion above asserted that per-integration CEL rules would filter
the algorithm's candidate set down to the right processes. The analyzer
includes a second-stage CEL evaluator
(`analysis/scripts/process_cel_eval.py`, run via `uv` with the
`cel-python` library) that applies real CEL expressions to the collected
data. Rules live in `analysis/process_autodiscovery/cel_rules.json`,
one per integration.

### Rule style

The rules use `process.name` (kernel `comm`, 15-char-truncated) when
that uniquely identifies the binary, and combine name with
`process.args` matching otherwise. `args` matching uses two patterns:

- `'X' in process.args` — exact match against an individual argv
  element. Use this for things like JVM main classes
  (`'kafka.Kafka' in process.args`) and python module names
  (`'ray.util.client.server' in process.args`).
- `process.args.exists(a, predicate)` — true if any argv element
  satisfies the predicate. Use this with `.startsWith`, `.endsWith`,
  `.contains`, etc. for things like classpath JARs or install-prefix
  checks.

Cmdline substring matching (`process.cmdline.contains(...)`) is reserved
for the handful of processes that rewrite argv[0] to include spaces
(`nginx`, `php-fpm`, postgres role workers) — there the space-split
`args` view loses the original argv boundaries, so the substring is the
only reliable signal. Broad cmdline substring matching like
`process.cmdline.contains('raylet')` is avoided because it matches any
process that incidentally references the raylet socket path in its
arguments, not just the raylet binary itself.

Combining name with args is also a performance hint: the cheap `name`
check short-circuits before the args scan.

### Results

Across the 98 integrations with non-infra target services in the
collected sample:

| Result | Count | Meaning |
|---|---|---|
| Post-CEL == 1 | 63 | Algorithm + CEL produced exactly one integration instance. |
| Post-CEL ≥ 2 | 31 | Multiple instances survived. Every case is either a multi-node test cluster (`consul`, `etcd`, `redisdb`, `postgres × 4`, `clickhouse × 6`, `cassandra × 2`, `kafka × 2`, `presto × 2`, `yarn × 2`, …), a multi-component service (`ceph` 9 → 5 daemon roles, `confluent_platform`, `mapreduce`, `hive`, `sonarqube`, `impala`), an aggregator/leaf pair (`vault`, `singlestore`, `prefect server` + `prefect worker`), or a legitimately co-monitored daemon pair (`mysql + percona-telemetry-agent`). |
| Post-CEL == 0 | 4 | The rule did not match any candidate process — all four are test-fixture artifacts: `http_check` (active HTTP probe, no host-process target), `mesos_slave` (the slave didn't appear in the fixture, only zookeeper), `nagios` (fixture runs `apache2` + `nsca`, not `nagios`), `teamcity` (fixture runs `org.mockserver.cli.Main`). |
| No rule available | 0 | Every integration with non-infra target data has an explicit CEL rule in `cel_rules.json`. |

The sibling worker pool case from the WARN classification verifies
empirically:

- `ray`: 29 candidate mains → 3 survivors (`raylet`, `gcs_server`,
  `ray.util.client.server`). The 21 `ray::IDLE`/`ray::ServeReplica`
  workers, the dashboard agent, the autoscaler monitor, and the log
  monitor are all dropped.
- `squid`: 5 candidates → 1 (`squid` daemon; the two `tail` siblings
  are dropped).
- `couchbase`: 12 candidates → 3 (one per `beam.smp` role —
  babysitter, ns_server, ns_couchdb — distinguished from
  rabbitmq/riak beam.smp by the `/opt/couchbase` install path in
  args).

### Could dedup be detrimental? — looking for "per-worker should be N" cases

The algorithm is built on a structural assumption: when a parent and
child share a `generated_name`, the child is a worker that the master
aggregates over, and only the master should become an integration
instance. It is worth checking whether any integration in the sample
violates this assumption — i.e. where the integration would *want*
each worker as its own instance.

The 16 cases in the data where the algorithm actually filtered
children break down as:

| Integration / Service | Kept | Dropped | Pattern |
|---|---|---|---|
| `airflow` / `airflow-webserver` (gunicorn) | 1 master | 4 workers | gunicorn master serves `/metrics`; workers aggregate into it |
| `airflow` / `gunicorn` | 1 master | 2 workers | same |
| `apache` / `httpd` | 1 master | 3 workers | Apache prefork — canonical pre-fork worker pool case |
| `gunicorn` / `dd-test-gunicorn` | 1 master | 4 workers | gunicorn standalone test fixture; same pattern as airflow above |
| `http_check` / `httpbin` | 1 master | 1 worker | httpbin fixture runs as gunicorn — same pattern |
| `kong` / `nginx` | 1 master | 16 workers | Kong is OpenResty/nginx; nginx pre-fork worker pool |
| `nagios` / `apache2` | 1 master | 5 workers | Apache prefork |
| `nginx` / `nginx` | 1 master | 1 worker | nginx master exposes stub_status; workers aggregate |
| `php_fpm` / `php-fpm` | 1 master | 2 pool workers | master exposes `/status`; workers aggregate |
| `php_fpm` / `nginx` | 1 master | 16 workers | nginx in front of php-fpm; same nginx pattern |
| `rethinkdb` / `rethinkdb` | 4 cluster nodes | 1 fork-duplicate | the dropped pid has the same `--server-name` and cmdline as one of the kept; it's an internal re-exec, not a separate instance |
| `silverstripe_cms` / `apache2` | 1 master | 5 workers | Apache prefork |
| `singlestore` / `memsqld` | 2 (aggregator + leaf) | 2 fork-duplicates | the dropped pids duplicate the aggregator/leaf cmdlines exactly; supervisor/forked-daemon pair |
| `spark` / `spark` | 4 daemons | 1 executor JVM | Spark executor forked from a worker; metrics are surfaced at the Spark UI/master, not per-executor |
| `tls` / `nginx` | 3 masters | 48 workers | three independent nginx instances for three TLS configs; each filters its own workers |
| `varnish` / `varnishd` | 1 manager | 1 `cache-main` child | Varnish's manager process supervises a `cache-main` child that actually handles caching; the integration uses `varnishstat` which reads shared memory by name and aggregates both |

Every dropped row is one of three patterns:
- **Pre-fork worker pool aggregated at the master** (nginx, apache,
  php-fpm, gunicorn). The master exposes the metrics endpoint;
  monitoring each worker would either produce duplicate counters or
  partial visibility.
- **Internal re-exec / supervisor pair** (varnish manager+cache-main,
  rethinkdb server0+fork, singlestore master+aggregator duplicate).
  The "child" is the same logical service from the integration's
  perspective.
- **Spark executor forked from worker**. Per-executor metrics are
  surfaced via the Spark driver UI, not by attaching the Spark
  integration to each executor process.

In every case the dedup is structurally appropriate. No integration in
the sample would lose useful coverage by it.

**What a counterexample would look like.** If some service forked
children that each exposed an independent metrics endpoint (a distinct
port, a per-worker shared-memory key, a per-tenant socket) and the
integration was designed to scrape each one, the algorithm would
collapse them to a single instance and the integration would lose
per-worker visibility. No such service appears in this sample.

**Note on the "multiple instances per host" config pattern.** Several
integrations document configuring more than one integration instance
against the same host. Two distinct families show up.

*Family 1 — one process, multiple logical endpoints.* The user
configures N entries in `instances:` against a single host process,
each pointing at a different database / pool / replica set / URL:

| Integration | Multi-instance config | Process topology |
|---|---|---|
| `sqlserver` | "When setting up multiple instances for different **databases** on the same host these metrics will be duplicated unless this option [`instance_metrics.enabled`] is turned off." | One `sqlservr` serving many databases. |
| `mongo` | Multiple instances each targeting a different mongo cluster/replica set. | Different remote `hosts:` — typically not local. |
| `php_fpm` | Multiple pools on one master, each with its own status URL. | One `php-fpm: master process` forks workers (already dedup'd correctly). |
| `openmetrics` / `prometheus` | Multiple `prometheus_url`s. | Different remote endpoints. |
| `elastic` | "If each machine only runs a single Elasticsearch node per cluster…" | Each ES node has `ppid == 1`; algorithm already gives N mains. |

For Family 1 the multiplication is along a different axis than processes
(logical entities inside the service vs. worker processes the algorithm
collapses). Autodiscovery handles the two orthogonally: when a process
matches the integration's CEL rule, every entry in the integration's
`auto_conf.yaml` `instances:` list is instantiated for that match.

*Family 2 — one logical deployment, multiple JVMs each monitored as a
distinct instance.* The integration explicitly targets several JVMs
that together make up one logical service:

| Integration | Multi-instance shape | Topology in collected data |
|---|---|---|
| `sonarqube` | Manifest signatures: `java org.sonar.server.app.WebServer` and `java org.sonar.ce.app.CeServer` — 2 instances per SonarQube install. | One `sonar-application` launcher JVM forks three child JVMs: WebServer, CeServer, and embedded Elasticsearch. All three have *different* `generated_name`s from each other and from the launcher. The dedup never fires; CEL selects WebServer + CeServer → 2 survivors. |
| `hive` | `conf.yaml.example` documents "HiveServer2 or Hive Metastore JMX host" — typically 2 instances. | Disco labels both HiveServer2 and Metastore JVMs with the *same* generated_name (`hadoop`). They share a name but not a parent — each is forked from its own `run.sh`/`startup.sh` shell with no service data — so the algorithm still produces independent mains. CEL disambiguates via `-Dproc_metastore` / `-Dproc_hiveserver2` JVM args → 2 survivors. |
| `hazelcast` | One instance per cluster node. | Each node is its own JVM in its own container, each with a distinct parent. Algorithm gives N mains directly; no dedup interaction. Test fixture has a 3-node cluster → 3 survivors. |
| `torchserve` | Single `process_signatures: ["torchserve"]`; single OpenMetrics endpoint at `:8082/metrics`. | One frontend process; backend Python workers per model are managed by the frontend and not separately monitored. (Collection failed in this run on a port conflict — see manifest and integration docs.) |

For Family 2 the dedup is again irrelevant: the multi-instance shape
either comes from JVMs with distinct `generated_name`s (SonarQube), or
from sibling JVMs whose common parent has no service data (Hive), or
from independent processes in separate containers (Hazelcast).

In every multi-instance-documenting integration surveyed, the
parent/child dedup either doesn't fire (because parent and child have
different `generated_name`s) or fires correctly (because workers
aggregate into the master). The contrived case where the dedup would
collide with a multi-instance expectation — a service that forks
workers, gives each worker its own metrics endpoint, and expects each
to be monitored separately — does not appear in any integration in
the sample.

### Existing manifest signatures don't translate to CEL verbatim

Many integrations have `process_signatures` in their `manifest.json`
written as if the cmdline started with the binary name (e.g.
`"java org.apache.spark.deploy..."`, `"java quarkus-run.jar"`). Real
`/proc/<pid>/cmdline` always carries the absolute binary path, so
`process.cmdline.contains("java org.apache.spark...")` never matches.
Integrations affected in the sample include `elastic`, `pulsar`,
`spark`, `sonarqube`, `quarkus`, `zk`, `hivemq`, `marathon`, `tomcat`,
and `couchbase` (where the literal `"beam.smp couchbase"` signature
never appears in any cmdline). The rules in `cel_rules.json` target
the main class or binary path directly via `args` matching, which
matches correctly.

The `process_signatures` field is descriptive metadata today, not a
runtime input. The gap is worth flagging: integration authors moving
to CEL-based process auto-discovery cannot reuse these strings
verbatim — they need to validate against real `/proc/<pid>/cmdline`
data. `process_cel_eval.py` is suitable for that validation.

## Conclusion

**The `isMainProcessForService` algorithm holds up against the collected
sample.** In every case where `disco` labeled both a parent and one or more
of its descendants with the same `generated_name`, the algorithm selected
exactly one main process and filtered the rest. No genuine worker was
incorrectly promoted to main in this sample.

This holds across the parent/child deduplication patterns the sample
exercised:
- C servers with pre-fork workers labeled with the same name as the master
  (e.g. `nginx`)
- Python pre-fork pools (`gunicorn`)
- JVM services with forked child JVMs that get distinct names
  (`sonar-application-*` vs. its Elasticsearch / WebServer / CeServer
  children — children correctly become their own services)

**Sibling worker pools are handled by CEL, not by the algorithm — verified
empirically.** The most notable case is **ray**, where 21
`ray::IDLE`/`ray::ServeReplica` workers are children of a single
`raylet`. Because the parent's `generated_name` is `raylet` (not `ray`),
each sibling worker survives the algorithm. Running the CEL rule
`process.name == 'raylet' || process.name == 'gcs_server' || (process.name == 'python' && 'ray.util.client.server' in process.args)`
through `cel-python` against this data drops 29 candidates to 3
survivors — the 21 worker processes plus all auxiliary python helpers
are removed. Same pattern for `squid tail` (5 → 1) and `couchbase tmp`
(12 → 3). See [the CEL evaluation
section](#cel-evaluation-against-the-collected-data) for the full
table.

**Existing manifest `process_signatures` don't translate to CEL
verbatim.** Many integration manifests assume cmdlines start with the
binary short name (e.g. `"java org.apache.spark.deploy..."`). Real
`/proc/<pid>/cmdline` carries the absolute binary path, so these
signatures match zero processes when used verbatim as CEL
`cmdline.contains(...)` rules. Affected in the sample: `elastic`,
`pulsar`, `spark`, `sonarqube`, `quarkus`, `zk`, `hivemq`, `marathon`,
`tomcat`, `couchbase`. This is descriptive metadata today and not a
runtime input, but integration authors moving to CEL-based process
auto-discovery will need to validate rules against real process
data — `process_cel_eval.py` is designed for that.

**Caveats:**

1. **Sample coverage.** Of 192 integrations with e2e tests, 132 were
   collected and 98 of those had a non-infra service detected. The 60
   skipped integrations include 20 K8s-only environments (process
   discovery is not relevant — target service runs as a pod inside
   Kind's nested namespaces), 18 fake-caddy fixtures (no real service
   runs), and 20 env-start failures dominated by Windows-only
   integrations, docker pull / build issues, and local toolchain
   incompatibilities. K8s-only and caddy-fixture integrations are
   structurally out of scope rather than gaps in coverage.
2. **Some integrations did not exercise the algorithm at all.** For example,
   the postgres background workers (`checkpointer`, `bgwriter`, `walwriter`,
   `autovacuum`, io workers) had `has_service_data: false`. They were
   excluded from the analyzer's input by the `has_service_data` filter, not
   by the algorithm. The algorithm's behavior on those workers is therefore
   unknown from this data. Production-truthful coverage of that branch
   would require extending the analyzer to also consider processes with
   `has_service_data: false` whose parent does have service data.
3. **Container detection differs from the design spec.** The spec describes
   filtering containers by ddev name/prefix; the implementation instead
   computes the delta of `docker ps` before and after `ddev env start`. This
   is the basis for the "soft warning" path: when start exits non-zero
   but the delta has new containers, collection still proceeds. Files
   written under this path have a `start_warning` key under `disco_raw` for
   traceability.

**Recommendation:** the algorithm can ship as is. The follow-up that
would materially improve the auto-discovery surface area is on the
integration side — each integration that opts in to process
auto-discovery needs a CEL expression precise enough to select its
actual entrypoint. The rules in `cel_rules.json` demonstrate the
required precision: `process.name == 'raylet'` over a cmdline substring
match on `'raylet'`, `'kafka.Kafka' in process.args` over a
`cmdline.contains('java kafka.Kafka')` that doesn't match real
cmdlines. Disco relabeling improvements (better names for Erlang `tmp`,
log-tailers, container helpers) are nice-to-haves that would simplify
the rules but are not blockers.

## Files

| File | Description |
|---|---|
| `analysis/scripts/process_analyze.py` | Collection and algorithm-verdict analyzer |
| `analysis/scripts/process_cel_eval.py` | CEL second-stage evaluator (run via `uv`, uses `cel-python`) |
| `analysis/process_autodiscovery/data/*.json` | Raw collected process data (132 files) |
| `analysis/process_autodiscovery/data/skipped.json` | Skipped integration log |
| `analysis/process_autodiscovery/cel_rules.json` | Explicit per-integration CEL rules (fallback when manifest lacks signatures or signatures don't match real cmdlines) |
| `analysis/process_autodiscovery/results/analysis_2026-05-14T13-20-23.json` | Final algorithm analysis output |
| `analysis/process_autodiscovery/results/cel_eval_2026-05-14.json` | Final CEL evaluation output |
| `docs/superpowers/specs/2026-05-13-process-autodiscovery-analysis-design.md` | Design spec |
| `docs/superpowers/plans/2026-05-13-process-autodiscovery-analysis.md` | Implementation plan |
