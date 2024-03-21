# Agent Check: Tekton

## Overview

This check monitors [Tekton][1] through the Datadog Agent. Tekton is a powerful and flexible open-source framework for creating CI/CD systems, allowing developers to build, test, and deploy across cloud providers and on-premise systems.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

Starting from Agent release 7.53.0, the Tekton check is included in the [Datadog Agent][2] package. No additional installation is needed on your server.

**WARNING**: This check uses [OpenMetrics](https://docs.datadoghq.com/integrations/openmetrics/) to collect metrics from the OpenMetrics endpoint that Tekton exposes, which requires Python 3.

### Configuration

1. Edit the `tekton.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your tekton performance data. See the [sample tekton.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `tekton` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Tekton integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://tekton.dev/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/tekton/datadog_checks/tekton/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/tekton/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/tekton/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
