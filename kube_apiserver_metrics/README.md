# Agent Check: Kube_apiserver_metrics

## Overview

This check monitors [Kube_apiserver_metrics][1].

## Setup

### Installation

The Kube_apiserver_metrics check is included in the [Datadog Agent][2] package, so you do not
need to install anything else on your server.

### Configuration

1. Edit the `kube_apiserver_metrics.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your kube_apiserver_metrics performance data.
   See the [sample kube_apiserver_metrics.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][3]

### Validation

[Run the Agent's `status` subcommand][4] and look for `kube_apiserver_metrics` under the Checks section.

## Data Collected

### Metrics

Kube_apiserver_metrics does not include any metrics.

### Service Checks

Kube_apiserver_metrics does not include any service checks.

### Events

Kube_apiserver_metrics does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][5].

[1]: **LINK_TO_INTEGERATION_SITE**
[2]: https://github.com/DataDog/integrations-core/blob/master/kube_apiserver_metrics/datadog_checks/kube_apiserver_metrics/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://docs.datadoghq.com/help/
