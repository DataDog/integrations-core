# Agent Check: cert_manager

## Overview

This check collects metrics from [cert-manager][1].

![Cert-Manager Overview Dashboard][2]

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The cert_manager check is included in the [Datadog Agent][3] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `cert_manager.d/conf.yaml` file in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your cert_manager performance data. See the [sample cert_manager.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `cert_manager` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this check.

### Events

The cert_manager integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].

[1]: https://github.com/jetstack/cert-manager
[2]: https://raw.githubusercontent.com/DataDog/integrations-core/master/cert_manager/images/overview_dashboard.png
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://github.com/DataDog/integrations-core/blob/master/cert_manager/datadog_checks/cert_manager/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/cert_manager/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/cert_manager/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/