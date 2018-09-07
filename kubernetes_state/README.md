# Kubernetes_state Integration

## Overview

Get metrics from kubernetes_state service in real time to:

* Visualize and monitor kubernetes_state states
* Be notified about kubernetes_state failovers and events.

## Setup
### Installation

The Kubernetes-State check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your Kubernetes servers.

### Configuration

Edit the `kubernetes_state.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][6], to point to your server and port, set the masters to monitor. See the [sample kubernetes_state.d/conf.yaml][2] for all available configuration options.

### Validation

[Run the Agent's `status` subcommand][3] and look for `kubernetes_state` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][4] for a list of metrics provided by this integration.

### Events
The Kubernetes-state check does not include any events at this time.

### Service Checks
**kubernetes_state.node.ready**

Returns `CRITICAL` if a cluster node is not ready.
Returns `OK` otherwise.

**kubernetes_state.node.out_of_disk**

Returns `CRITICAL` if a cluster node is out of disk space.
Returns `OK` otherwise.

**kubernetes_state.node.disk_pressure**

Returns `CRITICAL` if a cluster node is in a disk pressure state.
Returns `OK` otherwise.

**kubernetes_state.node.memory_pressure**

Returns `CRITICAL` if a cluster node is in a memory pressure state.
Returns `OK` otherwise.

**kubernetes_state.node.network_unavailable**

Returns `CRITICAL` if a cluster node is in a network unavailable state.
Returns `OK` otherwise.

**kubernetes_state.pod.phase**

Returns `CRITICAL` if the pod is in phase `Failed`, `WARNING` if it is `Pending`, `UNKNOWN` if it is `Unknown` or `OK` otherwise.

## Troubleshooting
Need help? Contact [Datadog Support][5].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/kubernetes_state/datadog_checks/kubernetes_state/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[4]: https://github.com/DataDog/integrations-core/blob/master/kubernetes_state/metadata.csv
[5]: https://docs.datadoghq.com/help/
[6]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
