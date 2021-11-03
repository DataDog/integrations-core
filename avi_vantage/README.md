# Agent Check: Avi Vantage

## Overview

This check monitors [Avi Vantage][1] through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The Avi Vantage check is included in the [Datadog Agent][9] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `avi_vantage.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your avi_vantage performance data. See the [sample avi_vantage.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4].

### Validation

[Run the Agent's status subcommand][5] and look for `avi_vantage` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this check.

### Service Checks

See [service_checks.json][7] for a list of service checks provided by this integration.

### Events

Avi Vantage does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][8].

[1]: https://avinetworks.com/why-avi/multi-cloud-load-balancing/
[2]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[3]: https://github.com/DataDog/integrations-core/blob/master/avi_vantage/datadog_checks/avi_vantage/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/avi_vantage/metadata.csv
[7]: https://github.com/DataDog/integrations-core/blob/master/avi_vantage/assets/service_checks.json
[8]: https://docs.datadoghq.com/help/
[9]: https://app.datadoghq.com/account/settings#agent