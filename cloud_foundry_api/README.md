# Agent Check: Cloud Foundry API

## Overview

This check queries the [Cloud Foundry API][1] to collect audit events and send them to Datadog via the agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The Cloud Foundry API check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `cloud_foundry_api.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your Cloud Foundry API data. See the [sample cloud_foundry_api.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4].

### Validation

[Run the Agent's status subcommand][5] and look for `cloud_foundry_api` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this check.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this check.

### Events

The Cloud Foundry API integration collects the configured audit events.

## Troubleshooting

Need help? Contact [Datadog support][7].

[1]: http://v3-apidocs.cloudfoundry.org
[2]: https://docs.datadoghq.com/agent/kubernetes/integrations
[3]: https://github.com/DataDog/integrations-core/blob/master/cloud_foundry_api/datadog_checks/cloud_foundry_api/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/cloud_foundry_api/metadata.csv
[7]: https://docs.datadoghq.com/help
[8]: https://github.com/DataDog/integrations-core/blob/master/cloud_foundry_api/assets/service_checks.json
