# Agent Check: Versa

## Overview

The Versa integration lets you monitor your Versa environment within [Network Device Monitoring][1]. Gain comprehensive insights into the performance and health of your SD-WAN infrastructure, including sites, tunnels, and devices.

## Setup

**The Versa NDM integration is in Preview and will not be billed until it is Generally Available.**

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The Versa check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `versa.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your versa performance data. See the [sample versa.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `versa` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Versa integration does not include any events.

### Service Checks

The Versa integration does not include any service checks.

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: /devices
[2]: /account/settings/agent/latest
[3]: https://docs.datadoghq.com/containers/kubernetes/integrations/
[4]: https://github.com/DataDog/datadog-agent/blob/main/cmd/agent/dist/conf.d/versa.d/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/versa/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/versa/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
