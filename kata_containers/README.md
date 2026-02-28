# Agent Check: Kata Containers

## Overview

This check monitors [Kata Containers][1] through the Datadog Agent.

Kata Containers is an open source container runtime that provides strong workload isolation by running containers in lightweight virtual machines. This integration collects performance metrics from Kata sandboxes by connecting directly to shim monitoring sockets.

The integration provides visibility into:
- Sandbox resource usage (CPU, memory, file descriptors, threads)
- Hypervisor performance metrics
- Guest VM statistics
- Shim and virtiofsd process metrics
- Agent metrics from inside the guest VM

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The Kata Containers check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `kata_containers.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your kata_containers performance data. See the [sample kata_containers.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `kata_containers` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Kata Containers integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

**kata.can_connect**:
Returns `CRITICAL` if the Agent cannot connect to a Kata sandbox socket, otherwise returns `OK`.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://katacontainers.io/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/containers/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/kata_containers/datadog_checks/kata_containers/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/kata_containers/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/kata_containers/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
