# Agent Check: Kubernetes Controller Manager

## Overview

This check monitors [Kube_controller_manager][1].

## Setup

### Installation

The Kube_controller_manager check is included in the [Datadog Agent][2] package, so you do not
need to install anything else on your server.

### Configuration

1. Edit the `kube_controller_manager.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your kube_controller_manager performance data.
   See the [sample kube_controller_manager.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][3]

### Validation

[Run the Agent's `status` subcommand][4] and look for `kube_controller_manager` under the Checks section.

## Data Collected

### Metrics

Kube_controller_manager does not include any metrics.

### Service Checks

Kube_controller_manager does not include any service checks.

### Events

Kube_controller_manager does not include any events.

## Troubleshooting

Need help? Contact [Datadog Support][5].

[1]: **LINK_TO_INTEGERATION_SITE**
[2]: https://github.com/DataDog/integrations-core/blob/master/kube_controller_manager/datadog_checks/kube_controller_manager/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://docs.datadoghq.com/help/
