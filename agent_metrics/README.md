# Agent Metrics Integration

## Overview

Get internal metrics from the Datadog Agent to create visualizations and monitors in Datadog.

**Note:** The list of metrics collected by this integration may change between minor Agent versions. Such changes may not be mentioned in the Agent's changelog.

## Setup

### Installation

The Agent Metrics integration, based on the [go_expvar][1] check, is included in the [Datadog Agent][2] package, so you don't need to install anything else on your servers.

### Configuration

1. Rename the [`go_expvar.d/agent_stats.yaml.example`][3] file, in the `conf.d/` folder at the root of your [Agent's configuration directory][4], to `go_expvar.d/agent_stats.yaml`.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `go_expvar` under the Checks section.

## Data Collected

### Metrics

The Agent Metrics integration collects the metrics defined in [`agent_stats.yaml.example`][3].

### Events

The Agent Metrics integration does not include any events.

### Service Checks

The Agent Metrics integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][7].

[1]: https://docs.datadoghq.com/integrations/go_expvar/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://github.com/DataDog/datadog-agent/blob/master/cmd/agent/dist/conf.d/go_expvar.d/agent_stats.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://docs.datadoghq.com/help/
