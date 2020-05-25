# Agent Metrics Integration

## Overview

Get metrics from the Agent Metrics service in real time to:

- Visualize and monitor `agent_metrics` states.
- Be notified about `agent_metrics` failovers and events.

**NOTE**: The Agent Metrics check has been rewritten in Go for Agent v6 to take advantage of the new internal architecture. Hence it is still maintained but **only works with Agents prior to major version 6**.

To collect Agent metrics for Agent v6+, use the [Go-expvar check][1] with [the `agent_stats.yaml` configuration file][2] packaged with the Agent.

## Setup

### Installation

The Agent Metrics check is included in the [Datadog Agent][3] package, so you don't need to install anything else on your servers.

### Configuration

1. Edit the `agent_metrics.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][4], to point to your server and port, set the masters to monitor. See the [sample agent_metrics.d/conf.yaml][5] for all available configuration options.

2. [Restart the Agent][6].

#### Metrics collection

The Agent Metrics integration can potentially emit [custom metrics][7], which may impact your [billing][8].

### Validation

[Run the Agent's status subcommand][9] and look for `agent_metrics` under the Checks section.

## Data Collected

All data collected are only available for Agent v5.

### Metrics

See [metadata.csv][10] for a list of metrics provided by this integration.

### Events

The Agent Metrics check does not include any events.

### Service Checks

The Agent Metrics check does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][11].

[1]: https://docs.datadoghq.com/integrations/go_expvar/
[2]: https://github.com/DataDog/datadog-agent/blob/master/cmd/agent/dist/conf.d/go_expvar.d/agent_stats.yaml.example
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/agent-v5/agent_metrics/datadog_checks/agent_metrics/data/conf.yaml.default
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/developers/metrics/custom_metrics/
[8]: https://docs.datadoghq.com/account_management/billing/custom_metrics/
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[10]: https://github.com/DataDog/integrations-core/blob/master/agent_metrics/metadata.csv
[11]: https://docs.datadoghq.com/help/
