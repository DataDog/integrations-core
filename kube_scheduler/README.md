# Agent Check: Kube_scheduler

## Overview

This check monitors [Kube_scheduler][1], part of the Kubernetes control plane.

## Setup

### Installation

The Kube_scheduler check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `kube_scheduler.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your kube_scheduler performance data. See the [sample kube_scheduler.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][3].

### Validation

[Run the Agent's status subcommand][4] and look for `kube_scheduler` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][5] for a list of metrics provided by this integration.

### Service Checks

`kube_scheduler.prometheus.health`:

Returns CRITICAL if the Agent cannot reach the metrics endpoints.

### Events

Kube_scheduler does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][6].

[1]: https://kubernetes.io/docs/reference/command-line-tools-reference/kube-scheduler
[2]: https://github.com/DataDog/integrations-core/blob/master/kube_scheduler/datadog_checks/kube_scheduler/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/kube_scheduler/metadata.csv
[6]: https://docs.datadoghq.com/help
