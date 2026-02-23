# Agent Check: n8n

## Overview

This check monitors [n8n][1] through the Datadog Agent. 

Collect n8n metrics including:
- Cache metrics: Hit and miss statistics.
- Message event bus metrics: Event-related metrics.
- Workflow metrics: Can include workflow ID labels.
- Node metrics: Can include node type labels.
- Credential metrics: Can include credential type labels.
- Queue metrics


## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The n8n check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

#### Enable the n8n metrics endpoint

The `/metrics` endpoint is disabled by default and must be enabled in your n8n configuration. Note that the `/metrics` endpoint is only available for self-hosted instances and is not available on n8n Cloud.

Set the following environment variables to enable metrics:

```bash
# Required: Enable the metrics endpoint
N8N_METRICS=true

# Optional: Include additional metric categories
N8N_METRICS_INCLUDE_DEFAULT_METRICS=true
N8N_METRICS_INCLUDE_CACHE_METRICS=true
N8N_METRICS_INCLUDE_MESSAGE_EVENT_BUS_METRICS=true
N8N_METRICS_INCLUDE_WORKFLOW_ID_LABEL=true
N8N_METRICS_INCLUDE_API_ENDPOINTS=true

# Optional: Customize the metric prefix (default is 'n8n_')
N8N_METRICS_PREFIX=n8n_
```

For more details, see the n8n documentation on [enabling Prometheus metrics][10].

#### Configure the Datadog Agent

1. Edit the `n8n.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your n8n performance data. See the [sample n8n.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Log collection

_Available for Agent versions >6.0_

#### Enable n8n logging

Configure n8n to output logs by setting the following environment variables:

```bash
# Set the log level (error, warn, info, debug)
N8N_LOG_LEVEL=info

# Output logs to console (for containerized environments) or file
N8N_LOG_OUTPUT=console

# If using file output, specify the log file location
N8N_LOG_FILE_LOCATION=/var/log/n8n/n8n.log
```

#### Configure the Datadog Agent to collect logs

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `n8n.d/conf.yaml` file to start collecting your n8n logs:

   ```yaml
   logs:
     - type: file
       path: /var/log/n8n/*.log
       source: n8n
       service: n8n
   ```

   For containerized environments using Docker, use the following configuration instead:

   ```yaml
   logs:
     - type: docker
       source: n8n
       service: n8n
   ```

3. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `n8n` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The n8n integration does not include any events.

### Service Checks

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
