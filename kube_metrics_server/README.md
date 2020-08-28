# Agent Check: Kube_metrics_server

## Overview

This check monitors [Kube_metrics_server][1] v0.3.0+, a component used by the Kubernetes control plane.

## Setup

### Installation

The Kube_metrics_server check is included in the [Datadog Agent][2] package. No additional installation is needed on your server.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

1. Edit the `kube_metrics_server.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your kube_metrics_server performance data. See the [sample kube_metrics_server.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][3].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Kubernetes Autodiscovery Integration Templates][4] for guidance on applying the parameters below.

| Parameter            | Value                                                |
| -------------------- | ---------------------------------------------------- |
| `<INTEGRATION_NAME>` | `kube_metrics_server `                                         |
| `<INIT_CONFIG>`      | blank or `{}`                                        |
| `<INSTANCE_CONFIG>`  | `{"prometheus_url": "https://%%host%%:443/metrics"}` |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

#### SSL

If your endpoint is secured, additional configuration is required:

1. Identify the certificate used for securing the metric endpoint.

2. Mount the related certificate file in the Agent pod.

3. Apply your SSL configuration. Refer to the [default configuration file][5] for more information.

### Validation

[Run the Agent's status subcommand][6] and look for `kube_metrics_server` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Service Checks

`kube_metrics_server.prometheus.health`:

Returns CRITICAL if the Agent cannot reach the metrics endpoints.

### Events

kube_metrics_server does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][8].

[1]: https://github.com/kubernetes-incubator/metrics-server
[2]: https://github.com/DataDog/integrations-core/blob/master/kube_metrics_server/datadog_checks/kube_metrics_server/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#restart-the-agent
[4]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[5]: https://github.com/DataDog/integrations-core/blob/master/openmetrics/datadog_checks/openmetrics/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/kube_metrics_server/metadata.csv
[8]: https://docs.datadoghq.com/help/
