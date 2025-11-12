# Agent Check: n8n

## Overview

This check monitors [n8n][1] through the Datadog Agent. 

Collect n8n metrics including:
- Cache metrics: Hit and miss statistics.
- Message event bus metrics: Event-related metrics.
- Workflow metrics: Can include workflow ID labels.
- Node metrics: Can include node type labels.
- Credential metrics: Can include credential type labels.
- Queue Metrics


## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The n8n check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

The `/metrics` endpoint is disabled by default and must be enabled by setting `N8N_METRICS`=`true`. You can also customize the metric prefix using `N8N_METRICS_PREFIX` (default is `n8n_`).

Note that the `/metrics` endpoint is only available for self-hosted instances and is not available on n8n Cloud.

For the datadog agent to collect metrics, you will need to follow the instructions provided [here][10].

1. Edit the `n8n.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your n8n performance data. See the [sample n8n.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `n8n` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The n8n integration does not include any events.

### Service Checks

The n8n integration does not include any service checks.

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://n8n.io/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/containers/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/n8n/datadog_checks/n8n/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/n8n/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/n8n/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://docs.n8n.io/hosting/configuration/configuration-examples/prometheus/
