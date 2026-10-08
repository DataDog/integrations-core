# Agent Check: Kata Containers

## Overview

This check collects metrics from [Kata Containers][1], a secure container runtime that runs each workload inside a lightweight virtual machine (VM) for hardware-enforced isolation.

The check is a long-running Go corecheck built into the Datadog Agent. It automatically discovers running Kata sandboxes by scanning the sandbox storage paths for shim Unix sockets, scrapes Prometheus metrics from each shim directly, and enriches the resulting metrics with Kubernetes orchestrator tags from the Datadog tagger.

With the Datadog Kata Containers integration, you can:

- Track the CPU and memory overhead introduced by the Kata VM infrastructure per sandbox.
- Monitor the health and resource usage of the containerd shim v2 (`containerd-shim-kata-v2`) for each running sandbox.
- Observe guest OS metrics (CPU, memory, disk, network) from inside each VM.
- Monitor hypervisor resource usage per sandbox.
- Alert on anomalous goroutine growth, high agent RPC latency, and elevated file descriptor counts.

**Minimum Agent version:** 7.79.0

## Setup

### Installation

The Kata Containers check is built into the [Datadog Agent][2]. No additional installation is required on your server.

### Prerequisites

Kata Containers must be installed and running on the host. The check discovers sandboxes by looking for `shim-monitor.sock` files under the configured `sandbox_storage_paths` (default: `/run/vc/sbs` and `/run/kata`).

### Configuration

The check runs automatically with default settings. No configuration is required unless you need to override the default sandbox storage paths or customize label handling.

To configure the check, create or edit `kata_containers.d/conf.yaml` in the `conf.d/` folder at the root of your Agent's configuration directory:

```yaml
instances:
  - sandbox_storage_paths:
      - /host/run/vc/sbs
      - /host/run/kata
    # rename_labels:
    #   version: go_version
    # exclude_labels: []
    # tags: []
```

**Note:** On Kubernetes, the Agent requires access to the host paths where Kata stores its sandbox sockets. Mount the relevant host directories into the Agent pod:

```yaml
volumeMounts:
  - name: kata-run
    mountPath: /host/run/vc
    readOnly: true
  - name: kata-run-alt
    mountPath: /host/run/kata
    readOnly: true
volumes:
  - name: kata-run
    hostPath:
      path: /run/vc
  - name: kata-run-alt
    hostPath:
      path: /run/kata
```

### Tag enrichment

For each sandbox, the check resolves the associated container IDs from the Datadog workloadmeta store and queries the Datadog tagger at `OrchestratorCardinality` to retrieve Kubernetes orchestrator tags. This means all per-sandbox metrics are automatically tagged with `kube_namespace`, `pod_name`, `cluster_name`, and other orchestrator-level tags alongside `sandbox_id`.

### Validation

[Run the Agent's `status` subcommand][3] and look for `kata_containers` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][4] for a list of metrics provided by this check. Metrics are grouped as follows:

| Group | Description |
|---|---|
| `kata.shim.*` | Shim process metrics scraped from each sandbox socket (`containerd-shim-kata-v2`) |
| `kata.go.*` | Go runtime metrics exposed by the shim (goroutines, GC, memory) |
| `kata.guest.*` | Guest OS metrics proxied by the shim (CPU, memory, disk, network) |
| `kata.hypervisor.*` | Hypervisor process resource usage per sandbox |
| `kata.agent.*` | Kata agent metrics proxied by the shim from inside the VM |
| `kata.firecracker.*` | Firecracker VMM-specific metrics (only when using the Firecracker hypervisor) |

`kata.running_shim_count` is emitted once per check run and reflects the total number of discovered sandboxes on the node.

All per-sandbox metrics carry a `sandbox_id` tag. Prometheus labels from the shim metrics (such as `item`, `cpu`, `disk`, `interface`, `action`) are mapped directly to Datadog tags. The `version` label is renamed to `go_version` by default.

### Events

The Kata Containers integration does not emit any events.

### Service Checks

See [service_checks.json][5] for a list of service checks provided by this integration.

**`kata_containers.openmetrics.health`**: Returns `CRITICAL` if the Agent fails to connect to or parse metrics from a sandbox shim socket, otherwise returns `OK`. Grouped by `sandbox_id`.

## Troubleshooting

### No sandboxes discovered

The check scans `sandbox_storage_paths` for directories containing a `shim-monitor.sock` file. If no sandboxes are found:

- Verify that Kata Containers sandboxes are running: `ls /run/vc/sbs/` or `ls /run/kata/`
- On Kubernetes, ensure the host paths are mounted into the Agent pod.
- Check that the Agent process has read access to the socket files.

### Metrics missing Kubernetes tags

Tag enrichment requires the Datadog workloadmeta store to have resolved the container-to-sandbox mapping. This mapping is updated on container lifecycle events from the container runtime. If tags are missing, verify that the Agent has access to the container runtime socket (containerd or CRI-O).

Need help? Contact [Datadog support][6].

## Further Reading

- [Kata Containers official documentation][1]
- [Kata 2.0 Metrics design document][7]
- [Kata Containers architecture][8]

[1]: https://katacontainers.io/
[2]: /account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[4]: https://github.com/DataDog/integrations-core/blob/master/kata_containers/metadata.csv
[5]: https://github.com/DataDog/integrations-core/blob/master/kata_containers/assets/service_checks.json
[6]: https://docs.datadoghq.com/help/
[7]: https://github.com/kata-containers/kata-containers/blob/main/docs/design/kata-2-0-metrics.md
[8]: https://github.com/kata-containers/kata-containers/blob/main/docs/design/architecture/README.md
