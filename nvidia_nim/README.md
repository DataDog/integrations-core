# Agent Check: nvidia_nim

## Overview

This check monitors [NVIDIA NIM][1] through the Datadog Agent. 

## Setup

<div class="alert alert-warning">
This integration is currently in Preview. Its availability is subject to change in the future. 
</div>

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

**Requirements**:
- This check requires Agent v7.61.0+
- This check uses [OpenMetrics][10] for metric collection, which requires Python 3.

### Installation

The NVIDIA NIM check is included in the [Datadog Agent][2] package. No additional installation is needed on your server.

### Configuration

NVIDIA NIM provides Prometheus [metrics][1] indicating request statistics. By default, these metrics are available at http://localhost:8000/metrics. The Datadog Agent can collect the exposed metrics using this integration. Follow the instructions below to configure data collection from any or all of the components.

To start collecting your NVIDIA NIM performance data:
1. Edit the `nvidia_nim.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your NVIDIA NIM performance data. See the [sample nvidia_nim.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `nvidia_nim` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The NVIDIA NIM integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://docs.nvidia.com/nim/large-language-models/latest/observability.html
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/nvidia_nim/datadog_checks/nvidia_nim/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/nvidia_nim/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/nvidia_nim/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://docs.datadoghq.com/integrations/openmetrics/