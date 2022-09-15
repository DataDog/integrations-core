# Agent Check: Kubernetes State Core

## Overview

Get Kubernetes metrics from [`kube-state-metrics`][1] in real time to:

- Visualize and monitor Kubernetes states.
- Be notified about Kubernetes failovers and events.

This check supersedes the legacy `kubernetes_state` check.
Unlike the legacy check, it doesn't require any stand-alone `kube-state-metrics` deployment.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The Kubernetes State Core check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `kubernetes_state_core.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your kubernetes_state_core performance data. See the [sample kubernetes_state_core.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `kubernetes_state_core` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Kubernetes State Core integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://github.com/kubernetes/kube-state-metrics
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/kubernetes_state_core/datadog_checks/kubernetes_state_core/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/kubernetes_state_core/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/kubernetes_state_core/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
