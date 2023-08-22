# Agent Check: Kubernetes Controller Manager

![Kube Controller Manager dashboard][1]

## Overview

This check monitors the [Kubernetes Controller Manager][2], part of the Kubernetes control plane.

**Note**: This check does not collect data for Amazon EKS clusters, as those services are not exposed.

## Setup

### Installation

The Kubernetes Controller Manager check is included in the [Datadog Agent][3] package, so you do not
need to install anything else on your server.

### Configuration

1. Edit the `kube_controller_manager.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your kube_controller_manager performance data. See the [sample kube_controller_manager.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5]

This integration requires access to the controller manager's metric endpoint. To have access to the metric endpoint you should:

* have access to the IP/Port of the controller-manager process
* have `get` RBAC permissions to the /metrics endpoint (the default Datadog Helm chart already adds the right RBAC roles and bindings for this)

### Validation

[Run the Agent's `status` subcommand][6] and look for `kube_controller_manager` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Kubernetes Controller Manager check does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog Support][9].

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/kube_controller_manager/images/screenshot.png
[2]: https://kubernetes.io/docs/reference/command-line-tools-reference/kube-controller-manager
[3]: https://app.datadoghq.com/account/settings/agent/latest
[4]: https://github.com/DataDog/integrations-core/blob/master/kube_controller_manager/datadog_checks/kube_controller_manager/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/kube_controller_manager/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/kube_controller_manager/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
