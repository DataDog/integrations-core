# Agent Check: Avi Vantage

## Overview

This check monitors [Avi Vantage][1] through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The Avi Vantage check is included in the [Datadog Agent][3] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `avi_vantage.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your avi_vantage performance data. See the [sample avi_vantage.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

**Note**: This check has a limit of 2000 metrics per instance. To see the number of returned metrics, run the Datadog Agent [status command][6]. You can specify the metrics you are interested in by editing the configuration. If you need to monitor more metrics, [contact Datadog support][10].

### Validation

[Run the Agent's status subcommand][7] and look for `avi_vantage` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this check.

### Service Checks

See [service_checks.json][9] for a list of service checks provided by this integration.

### Events

Avi Vantage does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][10].

[1]: https://avinetworks.com/why-avi/multi-cloud-load-balancing/
[2]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://github.com/DataDog/integrations-core/blob/master/avi_vantage/datadog_checks/avi_vantage/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6v7#agent-status-and-information
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/avi_vantage/metadata.csv
[9]: https://github.com/DataDog/integrations-core/blob/master/avi_vantage/assets/service_checks.json
[10]: https://docs.datadoghq.com/help/
