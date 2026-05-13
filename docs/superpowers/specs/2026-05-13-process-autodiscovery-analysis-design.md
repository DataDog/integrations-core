# Process Auto-Discovery Algorithm Analysis Tool

**Date:** 2026-05-13  
**Author:** vitkyrka  

## Background

The Datadog Agent has a process auto-discovery feature (`ProcessListener` in
`comp/core/autodiscovery/listeners/process.go`) that automatically applies
integration configs to running services. A key concern with extending auto-discovery
to processes is that a service like nginx or Apache spawns multiple sub-processes
(master + workers), and we must not create a separate integration instance for each
one — that would produce duplicate metrics.

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

A process is considered the "main" process unless its parent has the same
`GeneratedName` — in which case the parent is the main process and this one is
a worker/sub-process that should be skipped.

`GeneratedName` is set by the USM (Universal Service Monitoring) service
discovery module and reflects the detected service name (e.g., `"nginx"`,
`"gunicorn"`, `"postgres"`).

## Goal

Systematically test whether `isMainProcessForService` correctly identifies the
main process across all integrations that have E2E test environments in this
repository (144 integrations as of 2026-05-13).

The analysis must be split into two decoupled phases so that the algorithm can
be tweaked and re-evaluated without re-running the expensive environment setup.

## Tool

`analysis/scripts/process_analyze.py` — a CLI tool with two subcommands.

### `collect` — data collection

```bash
# Single integration (latest available environment)
python analysis/scripts/process_analyze.py collect nginx \
    --disco /home/bits/go/src/github.com/DataDog/datadog-agent/target/debug/disco

# All integrations with E2E tests
python analysis/scripts/process_analyze.py collect --all \
    --disco /home/bits/go/src/github.com/DataDog/datadog-agent/target/debug/disco

# Override data output directory
python analysis/scripts/process_analyze.py collect nginx \
    --disco /path/to/disco --data-dir /custom/data
```

**Workflow per integration:**

1. Run `ddev env show <integration>` to list available environments; pick the
   last standard version environment (e.g. `py3.13-1.27` over `py3.13-vts`).
   The `--env` flag overrides this selection.
2. **Pre-flight: detect fake caddy environments.** Locate the integration's
   docker-compose file(s) and check whether any service uses an image matching
   `caddy:*`. If so, record the integration as skipped with reason
   `"fake caddy server"` and stop — do not start the environment.
3. `ddev env start --dev <integration> <env>`. If this fails, record the
   integration as skipped with reason `"env start failed: <error>"` and stop.
4. Identify Docker containers started for this integration using
   `docker ps --format json` filtered by container name prefix (ddev names
   containers `<integration>_<service>_<n>`).
5. For each container, find all host-namespace PIDs that belong to it by
   scanning `/proc/<pid>/cgroup` for the container's ID.
6. Run `disco` on the host: it reads `/proc` and outputs detected services with
   their PIDs and `generated_name` values.
7. For each container PID:
   - Read `/proc/<pid>/status` → `ppid`, `comm`
   - Read `/proc/<pid>/cmdline` → full command line
   - Look up whether `disco` detected a service for this PID
8. Save collected data to `analysis/process_autodiscovery/data/<integration>__<env>.json`.
9. `ddev env stop <integration> <env>`

All skipped integrations are written to
`analysis/process_autodiscovery/data/skipped.json` for manual inspection (see
[Skipped integrations](#skipped-integrations) below).

### `analyze` — algorithm application

```bash
# Analyze all saved data files, print table, write results JSON
python analysis/scripts/process_analyze.py analyze

# Limit to one integration
python analysis/scripts/process_analyze.py analyze --integration nginx

# Custom directories
python analysis/scripts/process_analyze.py analyze \
    --data-dir analysis/process_autodiscovery/data \
    --results-dir analysis/process_autodiscovery/results
```

**Workflow:**

1. Load all `*.json` files from the data directory.
2. For each file, apply the algorithm to every process that has service data
   (`has_service_data: true`).
3. Group selected "main" processes by `generated_name`.
4. Assign a verdict per service:
   - **PASS** — exactly 1 main process (algorithm behaves correctly)
   - **WARN (N>1)** — multiple mains for the same service (would create
     duplicate metric instances — the core concern)
   - **WARN (N=0)** — all processes filtered out (over-aggressive — integration
     would not be discovered)
5. Print a human-readable table to stdout.
6. Save full results to
   `analysis/process_autodiscovery/results/analysis_<timestamp>.json`.

**Example table output:**

```
Integration              Environment     Service    Main PIDs         Verdict
nginx                    py3.13-1.27     nginx      [12345]           PASS
apache                   py3.13-1.23     apache2    [11, 12, 13]      WARN (3 mains)
gunicorn                 py3.13-2.0      python     []                WARN (0 mains)
redis                    py3.13-7.2      redis      [5678]            PASS

Skipped (2):
  kubernetes_cluster_autoscaler  — fake caddy server
  vault                          — env start failed: exit code 1
```

## Data format

`analysis/process_autodiscovery/data/<integration>__<env>.json`:

```json
{
  "integration": "nginx",
  "environment": "py3.13-1.27",
  "collected_at": "2026-05-13T10:00:00Z",
  "processes": [
    {
      "pid": 12345,
      "ppid": 1,
      "comm": "nginx",
      "cmdline": "nginx: master process /usr/sbin/nginx -g daemon off;",
      "generated_name": "nginx",
      "has_service_data": true
    },
    {
      "pid": 12350,
      "ppid": 12345,
      "comm": "nginx",
      "cmdline": "nginx: worker process",
      "generated_name": "nginx",
      "has_service_data": true
    },
    {
      "pid": 12349,
      "ppid": 1,
      "comm": "sh",
      "cmdline": "/bin/sh -c ...",
      "generated_name": null,
      "has_service_data": false
    }
  ],
  "disco_raw": {}
}
```

`has_service_data: false` means `disco` did not detect a service for this
process; the algorithm ignores these processes (same as `process.Service == nil`
in Go).

## Algorithm simulation

Python equivalent of the Go `isMainProcessForService` function:

```python
def is_main_process(pid: int, processes: dict[int, Process]) -> bool:
    p = processes[pid]
    if p.ppid in (0, 1):
        return True
    parent = processes.get(p.ppid)
    if parent is None or not parent.has_service_data:
        return True
    return parent.generated_name != p.generated_name
```

The `processes` dict covers only the processes from the saved JSON for a given
environment. This mirrors the workloadmeta store that the Go function queries.

## Skipped integrations

`analysis/process_autodiscovery/data/skipped.json` accumulates entries across
all `collect` runs. Each run appends (or updates) entries for integrations that
were skipped:

```json
[
  {
    "integration": "kubernetes_cluster_autoscaler",
    "reason": "fake caddy server",
    "skipped_at": "2026-05-13T10:01:00Z",
    "details": "image caddy:2.7 found in tests/docker/docker-compose.yaml"
  },
  {
    "integration": "vault",
    "reason": "env start failed",
    "skipped_at": "2026-05-13T10:05:00Z",
    "details": "ddev env start exited with code 1: ..."
  }
]
```

The `analyze` command reads `skipped.json` and includes the skipped list in both
the terminal output and the results JSON.

Two skip reasons:

| Reason | Description |
|--------|-------------|
| `fake caddy server` | docker-compose uses a `caddy:*` image — no real service runs |
| `env start failed` | `ddev env start` exited non-zero |

## File layout

```
analysis/
  scripts/
    process_analyze.py        ← single CLI tool
  process_autodiscovery/
    data/                     ← raw collected JSON (one file per integration/env)
      skipped.json            ← integrations that were skipped, for manual inspection
    results/                  ← analysis output JSON files
```

## Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `--disco` | (required for collect) | Path to the `disco` binary |
| `--data-dir` | `analysis/process_autodiscovery/data` | Where to read/write collected data |
| `--results-dir` | `analysis/process_autodiscovery/results` | Where to write analysis results |
| `--env` | (auto) | Override environment selection for `collect` |
| `--integration` | (all) | Limit to a single integration |
| `--all` | false | Collect all integrations with E2E tests |

## Known open items

- `disco` output format is unknown at design time; the collect step will adapt
  once its actual output schema is inspected during implementation.
- Container identification relies on ddev naming conventions; these will be
  verified empirically during implementation.
