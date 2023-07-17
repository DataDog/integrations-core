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

1. Edit the `kube_metrics_server.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your kube_metrics_server performance data. See the [sample kube_metrics_server.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Kubernetes Autodiscovery Integration Templates][5] for guidance on applying the parameters below.

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

3. Apply your SSL configuration. See the [default configuration file][6] for more information.

### Validation

[Run the Agent's status subcommand][7] and look for `kube_metrics_server` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this integration.

### Events

kube_metrics_server does not include any events.

### Service Checks

See [service_checks.json][9] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][10].


[1]: https://github.com/kubernetes-incubator/metrics-server
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://github.com/DataDog/integrations-core/blob/master/kube_metrics_server/datadog_checks/kube_metrics_server/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#restart-the-agent
[5]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[6]: https://github.com/DataDog/integrations-core/blob/master/openmetrics/datadog_checks/openmetrics/data/conf.yaml.example
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/kube_metrics_server/metadata.csv
[9]: https://github.com/DataDog/integrations-core/blob/master/kube_metrics_server/assets/service_checks.json
[10]: https://docs.datadoghq.com/help/
