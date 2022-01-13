# Agent Check: Kubernetes Scheduler

## Overview

This check monitors [Kubernetes Scheduler][1], part of the Kubernetes control plane.

**Note**: This check does not collect data for Amazon EKS clusters, as those services are not exposed.

## Setup

### Installation

The Kubernetes Scheduler check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

See the [Autodiscovery Integration Templates][3] for guidance on applying the parameters below.

#### Metric collection

1. Edit the `kube_scheduler.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your kube_scheduler performance data. See the [sample kube_scheduler.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

##### Log collection

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][6].

| Parameter      | Value                                     |
|----------------|-------------------------------------------|
| `<LOG_CONFIG>` | `{"source": "kube_scheduler", "service": "<SERVICE_NAME>"}` |

### Validation

[Run the Agent's status subcommand][7] and look for `kube_scheduler` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this integration.

### Events

Kube Scheduler does not include any events.

### Service Checks

See [service_checks.json][9] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][10].


[1]: https://kubernetes.io/docs/reference/command-line-tools-reference/kube-scheduler
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/kube_scheduler/datadog_checks/kube_scheduler/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#restart-the-agent
[6]: https://docs.datadoghq.com/agent/kubernetes/log/
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/kube_scheduler/metadata.csv
[9]: https://github.com/DataDog/integrations-core/blob/master/kube_scheduler/assets/service_checks.json
[10]: https://docs.datadoghq.com/help/
