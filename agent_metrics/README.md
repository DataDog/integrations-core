# Agent_metrics Integration

## Overview

Get metrics from agent_metrics service in real time to:

* Visualize and monitor agent_metrics states
* Be notified about agent_metrics failovers and events.

**NOTE**: The Agent Metrics check has been rewritten in Go for Agent v6 to take advantage of the new internal architecture. Hence it is still maintained but **only works with Agents prior to major version 6**.

To collect Agent metrics for Agent v6+, use the [Go-expvar check][10] with [the `agent_stats.yaml ` configuration file][9] packaged with the Agent.

## Setup
### Installation

The Agent Metrics check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your servers.

### Configuration

1. Edit the `agent_metrics.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][8], to point to your server and port, set the masters to monitor.

    See the [sample agent_metrics.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][7]

### Validation

[Run the Agent's `status` subcommand][3] and look for `agent_metrics` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][4] for a list of metrics provided by this integration.

### Events
The Agent_metrics check does not include any events at this time.

### Service Checks
The Agent_metrics check does not include any service checks at this time.

## Troubleshooting
Need help? Contact [Datadog Support][5].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/agent_metrics/datadog_checks/agent_metrics/data/conf.yaml.default
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[4]: https://github.com/DataDog/integrations-core/blob/master/agent_metrics/metadata.csv
[5]: https://docs.datadoghq.com/help/
[7]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[8]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
[9]: https://github.com/DataDog/datadog-agent/blob/master/cmd/agent/dist/conf.d/go_expvar.d/agent_stats.yaml.example 
[10]: https://docs.datadoghq.com/integrations/go_expvar/
