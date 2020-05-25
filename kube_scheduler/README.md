# Agent Check: Kubernetes Scheduler

## Overview

This check monitors [Kubernetes Scheduler][1], part of the Kubernetes control plane.

## Setup

### Installation

The Kubernetes Scheduler check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

See the [Autodiscovery Integration Templates][9] for guidance on applying the parameters below.

#### Metric collection

1. Edit the `kube_scheduler.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your kube_scheduler performance data. See the [sample kube_scheduler.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][3].

#### Log collection

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes log collection documentation][10].

| Parameter      | Value                                     |
|----------------|-------------------------------------------|
| `<LOG_CONFIG>` | `{"source": "kube_scheduler", "service": "<SERVICE_NAME>"}` |

### Validation

[Run the Agent's status subcommand][6] and look for `kube_scheduler` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Service Checks

**kube_scheduler.prometheus.health**:<br>
Returns `CRITICAL` if the Agent cannot reach the metrics endpoints, otherwise returns `OK`.

### Events

Kube Scheduler does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][8].

[1]: https://kubernetes.io/docs/reference/command-line-tools-reference/kube-scheduler
[2]: https://github.com/DataDog/integrations-core/blob/master/kube_scheduler/datadog_checks/kube_scheduler/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#restart-the-agent
[4]: https://docs.datadoghq.com/agent/kubernetes/daemonset_setup/#log-collection
[5]: https://docs.datadoghq.com/agent/kubernetes/daemonset_setup/#create-manifest
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/kube_scheduler/metadata.csv
[8]: https://docs.datadoghq.com/help/
[9]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[10]: https://docs.datadoghq.com/agent/kubernetes/log/
