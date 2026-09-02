# Agent Check: PowerHA

## Overview

This check monitors [IBM PowerHA SystemMirror][1] (formerly HACMP) cluster health through the Datadog Agent.

PowerHA keeps critical applications running by failing resources over between AIX nodes when a node, network, or storage path fails. Without this integration, verifying cluster health means logging into a node and running tools like `clRGinfo`, `lssrc -ls clstrmgrES`, or the community `qha` script by hand. This check instead reports cluster manager state, resource group placement, application monitor status, CAA (Cluster Aware AIX) heartbeat/communication health, network adapter status, and shared volume group status as Datadog metrics and service checks, so cluster and failover health can be dashboarded and alerted on like any other infrastructure.

## Setup

### Installation

The PowerHA check is included in the AIX build of the [Datadog Agent][2]. No additional installation is needed.

This check is **AIX-only** and is designed to run locally on each PowerHA cluster node it monitors — it shells out to binaries installed with PowerHA/CAA (`odmget`, `lssrc`, `clRGinfo`/`clfindres`, `lscluster`, `clras`, `lsvg`, `netstat`, `lslpp`) and does not fan out to other nodes over `clrsh`. Peer-node visibility (equivalent to what `qha` obtained via remote `clrsh <node> date`) instead comes from the local CAA view reported by `lscluster -m`. Install the Agent and this check on every cluster node you want visibility into.

Because there is no remote fan-out, the check has no dependency on `/etc/cluster/rhosts` or passwordless `clrsh`/`ssh` trust between nodes.

### Configuration

1. Edit the `powerha.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory, to start collecting PowerHA cluster data. See the [sample powerha.d/conf.yaml][4] for all available configuration options.

2. The `dd-agent` user needs read access to the cluster manager's `hacmp.out` event log to report which event is running while the cluster manager is not in a stable state (the `event` service check tag/message on `powerha.cluster_manager.status`). If `dd-agent` cannot read this file, the check still runs and reports the cluster manager's state — it just omits the current event detail. Grant read access, for example:

   ```text
   chmod o+r /var/hacmp/log/hacmp.out
   ```

   Or set `hacmp_out_path` explicitly in `conf.yaml` if the file lives somewhere non-default, and disable `collect_cluster_events` if you don't want the check to read it at all.

3. [Restart the Agent][5].

#### Mapping from the `qha` script

If you previously used the community `qha` script (or `PowerHA.script.sh`) to poll cluster status interactively, this table maps its command-line flags to the equivalent `conf.yaml` options:

| `qha` flag | Behavior | `powerha` check equivalent |
|---|---|---|
| (none) | Cluster manager, resource group, and node status | Always collected |
| `-n` | Network interface status | `collect_network_interfaces` (default: `true`) |
| `-N` | Network interfaces + non-IP (disk) heartbeat networks | `collect_network_interfaces`; the legacy non-IP heartbeat display is not ported — it predates CAA and the script itself flags it as due for removal. Use `collect_caa_comms` for the CAA disk-based communication path instead |
| `-v` | Shows online volume groups | `collect_volume_groups` (default: `true`) |
| `-l` | Logs raw state-change lines to `/tmp/qha.out` as a crude alert mechanism | Not ported — create a [Datadog monitor][10] on the relevant service check instead (for example `powerha.resource_group.status` or `powerha.cluster_manager.status`) |
| `-e` | Shows the running cluster event | `collect_cluster_events` (default: `true`) |
| `-m` | Shows application monitor status | `collect_app_monitor_status` (default: `false`, since it forks an extra `clRGinfo -m`) |
| `-1` | Single iteration instead of a refresh loop | Not applicable — the Agent scheduler runs the check on `min_collection_interval` instead of looping |
| `-c` | Shows CAA SAN/disk communication status (AIX 7.1 TL3+) | `collect_caa_comms` (default: `true`) |

### Known limitations

- Every command this check shells out to runs without a timeout (a constraint of the Agent's subprocess helper). A hung PowerHA/CAA command (for example during a stuck failover) can make one check run take longer than usual; it does not hang the Agent process itself, but consider this when tuning `min_collection_interval`.
- If a domain's binary or feature isn't present (for example `clras` on a cluster without CAA-based SAN/disk comms, or pre-7.1 clusters), that domain silently submits nothing rather than an error, so as not to generate false alarms on clusters that don't use a given feature.

### Validation

[Run the Agent's status subcommand][6] and look for `powerha` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The PowerHA integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://www.ibm.com/products/powerha
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/powerha/datadog_checks/powerha/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/powerha/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/powerha/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://docs.datadoghq.com/monitors/
