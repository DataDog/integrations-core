# Agent Check: Kubernetes Controller Manager

## Overview

This check monitors the [Kubernetes Controller Manager][1], part of the Kubernetes control plane.

**Note**: This check does not collect data for Amazon EKS clusters, as those services are not exposed.

## Setup

### Installation

The Kubernetes Controller Manager check is included in the [Datadog Agent][2] package, so you do not
need to install anything else on your server.

### Configuration

This integration requires access to the controller manager's metric endpoint. It is usually not
exposed in container-as-a-service clusters.

1. Edit the `kube_controller_manager.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your kube_controller_manager performance data. See the [sample kube_controller_manager.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4]

### Validation

[Run the Agent's `status` subcommand][5] and look for `kube_controller_manager` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this integration.

### Events

The Kubernetes Controller Manager check does not include any events.

### Service Checks

See [service_checks.json][7] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog Support][8].


[1]: https://kubernetes.io/docs/reference/command-line-tools-reference/kube-controller-manager
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://github.com/DataDog/integrations-core/blob/master/kube_controller_manager/datadog_checks/kube_controller_manager/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/kube_controller_manager/metadata.csv
[7]: https://github.com/DataDog/integrations-core/blob/master/kube_controller_manager/assets/service_checks.json
[8]: https://docs.datadoghq.com/help/
