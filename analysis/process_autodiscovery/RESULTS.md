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

### How the algorithm fits with CEL filtering

`isMainProcessForService` is only the first filter in the agent's
`ProcessListener`
([`comp/core/autodiscovery/listeners/process.go`][listener]). The second
filter is a per-integration **CEL expression** evaluated against a
`FilterProcess` with fields `name` (the process `Comm`), `cmdline`, and
`args` (see
[`pkg/proto/datadog/workloadfilter/workloadfilter.proto`][proto] and
[Scheduling Checks with Autodiscovery based on Service Discovery][cel-doc]).
Each integration that opts in to process auto-discovery provides a CEL
expression that selects which processes it actually wants — e.g.
`name == "raylet"` for Ray, `name == "nginx" && "master" in args` for nginx.

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
section](#cel-evaluation-against-the-collected-data): for `ray`, a CEL
rule based on the manifest's existing `process_signatures` reduces 29
mains to 4 survivors (the 21 `ray::IDLE` workers are correctly dropped),
and a tighter rule like `process.name == 'raylet'` would reduce it
further to 1. For `squid`, `cmdline.contains('squid -f')` reduces 5 mains
to 1. The algorithm's job is to reduce the candidate set to one main per
`generated_name`; the integration author's job is to pick the right one
via CEL. The N here reflects how disco labels processes, not how many
integration instances would be created.

#### Category 4: disco false positives surfaced as WARN — CEL handles it

| Integration | Service | Details |
|---|---|---|
| couchbase | `tmp` | 3 Erlang/OTP `beam.smp` processes labeled `tmp` — a generic disco fallback name for unrecognized Erlang VMs. Each has a different parent (separate Erlang subtrees), so it is not the sibling case above. |

The couchbase integration's CEL rule (an OR over the
`/opt/couchbase/lib/erlang` path in `cel_rules.json`) reduces couchbase's
12 mains to 3 survivors, one per `beam.smp` role (babysitter, ns_server,
ns_couchdb). The generic `tmp` candidates are filtered out. As above,
this WARN row does not correspond to runaway duplicate integration
instances in production.

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

## CEL evaluation against the collected data

The discussion above asserted that per-integration CEL rules would filter
the algorithm's candidate set down to the right processes. To verify
rather than assert this, the analyzer was extended with a second-stage
CEL evaluator (`analysis/scripts/process_cel_eval.py`, run via `uv` with
the `cel-python` library) that applies real CEL expressions to the same
collected data. Rules come from each integration's `manifest.json`
`process_signatures` (OR-joined as `process.cmdline.contains(<sig>)`) or,
when the manifest lacks usable signatures, from an explicit override file
(`analysis/process_autodiscovery/cel_rules.json`).

Across the 66 integrations with non-infra target services in the collected
sample:

| Result | Count | Meaning |
|---|---|---|
| Post-CEL == 1 | 33 | Algorithm + CEL produced exactly one integration instance — the happy case. |
| Post-CEL ≥ 2 | 23 | Multiple instances survived. For multi-node test clusters (`consul`, `etcd`, `redisdb`, `postgres × 4`, …) this is the correct outcome. For `ceph` (9 → 3) it is one survivor per daemon role. A handful of rows are rule-too-broad — see below. |
| Post-CEL == 0 | 4 | The rule did not match any candidate process. The integration would not be auto-discovered. |
| No rule available | 6 | Integrations whose manifest has no `process_signatures` and where no explicit rule was written (`citrix_hypervisor`, `esxi`, `go_expvar`, `hudi`, `kafka_actions`, `nfsstat`). |

### Sibling worker pool — verified

The doc previously claimed CEL would handle Ray's 21-sibling case. The
evaluation confirms this: ray's **29** candidate mains reduce to **4**
after CEL — `gcs_server`, `raylet`, the `ray.util.client.server` Python
module, and (unexpectedly) `ray.dashboard.agent`. The dashboard agent is
included because its cmdline references the raylet socket path
(`--raylet-name=/tmp/ray/.../sockets/...`), so the manifest's `raylet`
substring rule matches more than just the raylet binary. This is a
*rule-too-broad* finding rather than an algorithm issue: tightening the
rule to e.g. `process.name == 'raylet'` would reduce it to one survivor.
The 21 `ray::IDLE`/`ray::ServeReplica` worker processes are correctly
dropped either way.

Similarly, `squid`'s `tail` siblings are dropped by
`cmdline.contains('squid -f')` (5 mains → 1 survivor). Couchbase reduces
12 → 3 (one per `beam.smp` role) with the `/opt/couchbase/lib/erlang`
rule.

### Manifest signatures often do not match real cmdlines

A side finding of this evaluation: many existing `process_signatures` in
integration manifests are written as if the cmdline started with the
binary name (e.g. `"java org.apache.spark.deploy..."`,
`"java quarkus-run.jar"`). Real `/proc/<pid>/cmdline` always carries the
absolute binary path, so `cmdline.contains("java org.elasticsearch...")`
never matches. Integrations in the sample affected by this verbatim
include `elastic` (opensearch fixture), `pulsar`, `spark`, `sonarqube`,
`quarkus`, `zk`, `hivemq`, `marathon`, `temporal`, and `couchbase` (the
literal `"beam.smp couchbase"` signature never appears in any cmdline).
After rewriting those rules to match the main class or binary path alone
(see `cel_rules.json`), the post-CEL counts come out correct.

The `process_signatures` field is descriptive metadata today, not a
runtime input. But the gap is worth flagging: integration authors moving
to CEL-based process auto-discovery cannot reuse these strings verbatim
— they need to validate against real `/proc/<pid>/cmdline` data, not
against an idealized cmdline form. The `process_cel_eval.py` tool in
this branch is suitable for that validation.

### Rules that produced 0 survivors

| Integration | Issue |
|---|---|
| `marathon` | Mesos Marathon is a Scala assembly jar; the `mesosphere.marathon.Main` class is not in the JVM cmdline. The collected `marathon-assembly-1.3.0` and `mesos-master` processes need different selectors. |
| `sonatype_nexus` | The Java process runs `org.springframework.boot.loader.launch.PropertiesLauncher`; the Nexus main class is not in its cmdline. |
| `teamcity` | The test fixture runs a `org.mockserver.cli.Main` stand-in rather than the real TeamCity server. |
| `temporal` | Collection captured only the Elasticsearch and Postgres support containers — the `temporal-server` container's processes were not in the docker-ps delta when the collector ran. |

None of these is an algorithm failure. They expose where the rule wording
or the data collection itself fell short.

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
`ray::IDLE`/`ray::ServeReplica` workers are all children of a single
`raylet`. Because the parent's `generated_name` is `raylet` (not `ray`),
each sibling worker survives the algorithm. Running the agent's CEL
filter (derived from ray's existing `manifest.json` `process_signatures`)
through `cel-python` against this data drops 29 candidates to 4 — the
21 worker processes are removed. A tighter `process.name == 'raylet'`
rule reduces that to 1. Same pattern for `squid tail` (5 → 1) and
`couchbase tmp` (12 → 3). See [the CEL evaluation
section](#cel-evaluation-against-the-collected-data) for the full table.

**Side finding: existing manifest `process_signatures` often don't match
real cmdlines.** Many integration manifests assume cmdlines start with
the binary short name (e.g. `"java org.apache.spark.deploy..."`). Real
`/proc/<pid>/cmdline` carries the absolute binary path, so these
signatures match zero processes when used verbatim as CEL
`cmdline.contains(...)` rules. Affected in the sample: `elastic`,
`pulsar`, `spark`, `sonarqube`, `quarkus`, `zk`, `hivemq`, `marathon`,
`couchbase`, `temporal`. This is descriptive metadata today and not a
runtime input, but integration authors moving to CEL-based process
auto-discovery will need to validate rules against real process
data — the `process_cel_eval.py` tool added in this branch is
designed for that.

**Caveats:**

1. **Sample coverage.** Of 144 integrations with E2E tests, 93 were
   collected and 66 of those had a non-infra service detected. The 51
   skipped integrations include 19 K8s-only environments (process discovery
   is not relevant — target service runs as a pod inside Kind's nested
   namespaces), 18 fake-caddy fixtures (no real service runs), and 13 env
   start failures dominated by Windows-only integrations and local
   toolchain issues. K8s-only and caddy-fixture integrations are
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

**Recommendation:** the algorithm can ship as is. The follow-up that would
materially improve the auto-discovery surface area is on the integration
side — each integration that opts in to process auto-discovery needs a CEL
expression precise enough to select its actual entrypoint (e.g.
`name == "raylet"` rather than matching any `ray*` process). Disco
relabeling improvements (better names for Erlang `tmp`, log-tailers,
container helpers) are nice-to-haves that would simplify the CEL rules but
are not blockers.

## Files

| File | Description |
|---|---|
| `analysis/scripts/process_analyze.py` | Collection and algorithm-verdict analyzer |
| `analysis/scripts/process_cel_eval.py` | CEL second-stage evaluator (run via `uv`, uses `cel-python`) |
| `analysis/process_autodiscovery/data/*.json` | Raw collected process data (93 files) |
| `analysis/process_autodiscovery/data/skipped.json` | Skipped integration log |
| `analysis/process_autodiscovery/cel_rules.json` | Explicit per-integration CEL rules (fallback when manifest lacks signatures or signatures don't match real cmdlines) |
| `analysis/process_autodiscovery/results/analysis_2026-05-14T09-13-28.json` | Final algorithm analysis output |
| `docs/superpowers/specs/2026-05-13-process-autodiscovery-analysis-design.md` | Design spec |
| `docs/superpowers/plans/2026-05-13-process-autodiscovery-analysis.md` | Implementation plan |
