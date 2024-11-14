# Agent Check: Milvus

## Overview

This check monitors [Milvus][1] through the Datadog Agent. 

Include a high level overview of what this integration does:
- What does your product do (in 1-2 sentences)?
- What value will customers get from this integration, and why is it valuable to them?
- What specific data will your integration monitor, and what's the value of that data?

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The Milvus check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `milvus.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your milvus performance data. See the [sample milvus.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `milvus` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Milvus integration does not include any events.

### Service Checks

The Milvus integration does not include any service checks.

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: **LINK_TO_INTEGRATION_SITE**
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/milvus/datadog_checks/milvus/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/milvus/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/milvus/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
