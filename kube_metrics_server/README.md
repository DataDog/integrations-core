# Agent Check: Kube_metrics_server

## Overview

This check monitors [Kube_metrics_server][1] v0.3.0+, a component used by the Kubernetes control plane.

## Setup

### Installation

The Kube_metrics_server check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `kube_metrics_server.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your kube_metrics_server performance data. See the [sample kube_metrics_server.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][3].

### Validation

[Run the Agent's status subcommand][4] and look for `kube_metrics_server` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][5] for a list of metrics provided by this integration.

### Service Checks

`kube_metrics_server.prometheus.health`:

Returns CRITICAL if the Agent cannot reach the metrics endpoints.

### Events

kube_metrics_server does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][6].

[1]: https://github.com/kubernetes-incubator/metrics-server
[2]: https://github.com/DataDog/integrations-core/blob/master/kube_metrics_server/datadog_checks/kube_metrics_server/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#restart-the-agent
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/kube_metrics_server/metadata.csv
[6]: https://docs.datadoghq.com/help
