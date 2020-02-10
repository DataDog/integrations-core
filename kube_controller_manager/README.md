# Agent Check: Kubernetes Controller Manager

## Overview

This check monitors the [Kubernetes Controller Manager][1], part of the Kubernetes control plane.

## Setup

### Installation

The Kube_controller_manager check is included in the [Datadog Agent][2] package, so you do not
need to install anything else on your server.

### Configuration

This integration requires access to the controller manager's metric endpoint. It is usually not
exposed in Container-as-a-Service clusters.

1. Edit the `kube_controller_manager.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your kube_controller_manager performance data. See the [sample kube_controller_manager.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][3]

### Validation

[Run the Agent's `status` subcommand][4] and look for `kube_controller_manager` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][5] for a list of metrics provided by this integration.

### Service Checks

`kube_controller_manager.prometheus.health`:

Returns CRITICAL if the Agent cannot reach the metrics endpoints.

### Events

Kube_controller_manager does not include any events.

## Troubleshooting

Need help? Contact [Datadog Support][6].

[1]: https://kubernetes.io/docs/reference/command-line-tools-reference/kube-controller-manager
[2]: https://github.com/DataDog/integrations-core/blob/master/kube_controller_manager/datadog_checks/kube_controller_manager/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/kube_controller_manager/metadata.csv
[6]: https://docs.datadoghq.com/help
