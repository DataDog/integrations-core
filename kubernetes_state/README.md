# Kubernetes_state Integration

## Overview

Get metrics from kubernetes_state service in real time to:

- Visualize and monitor kubernetes_state states
- Be notified about kubernetes_state failovers and events.

## Setup

### Installation

The Kubernetes-State check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your Kubernetes servers.

### Configuration

Edit the `kubernetes_state.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample kubernetes_state.d/conf.yaml][3] for all available configuration options.

### Validation

Run the [Agent's status subcommand][4] and look for `kubernetes_state` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][5] for a list of metrics provided by this integration.

### Events

The Kubernetes-state check does not include any events.

### Service Checks

See [../kubernetes/assets/service_checks.json][6] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][7].


[1]: https://app.datadoghq.com/account/settings/agent/latest
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/kubernetes_state/datadog_checks/kubernetes_state/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/kubernetes_state/metadata.csv
[6]: https://github.com/DataDog/integrations-core/blob/master/kubernetes/assets/service_checks.json
[7]: https://docs.datadoghq.com/help/
