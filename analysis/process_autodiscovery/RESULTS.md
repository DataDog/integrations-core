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

## Results

### Coverage

| Category | Count |
|---|---|
| Integrations collected | 86 |
| Skipped — fake caddy server | 18 |
| Skipped — env start failed (K8s, Windows, cloud-only) | 39 |
| Skipped — no environments found | 1 |

Integrations skipped due to fake caddy are those where the test environment serves
static fixture files via Caddy instead of running the real service (e.g.,
`kubernetes_cluster_autoscaler`, `silk`, `appgate_sdp`). These are not meaningful
for process tree analysis.

### Algorithm verdicts

Excluding the Datadog agent infra processes (`agent`, `system-probe`,
`security-agent`, `privateactionrunner`) that are present in every environment:

| Verdict | Count |
|---|---|
| **PASS** (1 main per service) | 108 service/integration pairs |
| **WARN (N>1)** | 25 service/integration pairs |
| No service data (disco returned nothing) | 26 integrations |

### PASS cases — algorithm works correctly

Representative examples showing master+worker filtering:

| Integration | Service | Outcome |
|---|---|---|
| nginx | `nginx` | 1 master, 1 worker filtered ✅ |
| postgres | `postgres` | 1 master, workers (checkpointer, walwriter, autovacuum, bgwriter) filtered ✅ |
| airflow | `gunicorn` | 1 master, all workers filtered ✅ |
| haproxy | `haproxy` | 1 main ✅ |
| rabbitmq | `rabbitmq` | 1 main ✅ |
| scylla | `scylla` | 1 main ✅ |
| sonarqube | `sonar-application-*` | 1 main; child JVMs (Elasticsearch, WebServer, CeServer) correctly separate ✅ |
| pulsar | `pulsar` | 1 main ✅ |
| nifi | `nifi` | 1 main, framework subprocess correctly separate ✅ |
| ceph | `ceph-mon`, `ceph-mgr`, `ceph-osd`, `ceph-mds`, `radosgw` | Each daemon correctly 1 main ✅ |
| confluent_platform | `zookeeper`, `kafka.Kafka`, `io.confluent.*` (5 services) | All correctly 1 main each ✅ |

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

#### Category 3: disco false positives (disco issue, not algorithm issue)

| Integration | Service | Details |
|---|---|---|
| squid | `tail` | `tail -F /var/log/squid/access.log` and `tail -F /var/log/squid/cache.log` detected as services. These are log-tailing helper processes, not real services. |
| couchbase | `tmp` | 3 Erlang/OTP beam processes labeled `tmp` — a generic disco name for unrecognized Erlang processes. |

In both cases the actual target service (`squid`, `couchbase`) correctly shows PASS.

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

**The `isMainProcessForService` algorithm is sound for production use.**

Across 86 tested integrations and 108 unique service/integration pairs, the algorithm
produced **zero false master selections** — no case was found where a genuine worker
or sub-process was incorrectly promoted to main.

The master+worker deduplication logic works correctly for all tested patterns:
- C services with pre-fork workers (nginx, haproxy, squid, php-fpm)
- Database servers with background helper processes (postgres, redis single-instance)
- JVM services with forked child JVMs (sonarqube, confluent components)
- Python worker pools (gunicorn, celery)
- Supervised services (scylla, supervisord-managed)

The WARN cases are either multi-node cluster test environments (where N instances
are correct and expected) or minor disco naming issues (unrelated to the algorithm).

**Recommendation:** The algorithm can be shipped as-is. The only follow-up items
are disco-side:
1. Improve naming for Erlang/OTP processes (couchbase `tmp`)
2. Avoid labeling log-tailing helper processes as services (squid `tail`)
3. Extend disco to reach processes inside nested Kubernetes network namespaces

## Files

| File | Description |
|---|---|
| `analysis/scripts/process_analyze.py` | Collection and analysis tool |
| `analysis/process_autodiscovery/data/*.json` | Raw collected process data (86 files) |
| `analysis/process_autodiscovery/data/skipped.json` | Skipped integration log |
| `analysis/process_autodiscovery/results/analysis_2026-05-13T17-29-06.json` | Final analysis output |
| `docs/superpowers/specs/2026-05-13-process-autodiscovery-analysis-design.md` | Design spec |
| `docs/superpowers/plans/2026-05-13-process-autodiscovery-analysis.md` | Implementation plan |
