# Agent_metrics Integration

## Overview

Get metrics from agent_metrics service in real time to:

* Visualize and monitor agent_metrics states
* Be notified about agent_metrics failovers and events.

## Setup
### Installation

The Agent Metrics check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your servers.

### Configuration

1. Edit the `agent_metrics.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's directory, to point to your server and port, set the masters to monitor.  

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

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog][6]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/agent_metrics/conf.yaml.default
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[4]: https://github.com/DataDog/integrations-core/blob/master/agent_metrics/metadata.csv
[5]: http://docs.datadoghq.com/help/
[6]: https://www.datadoghq.com/blog/
[7]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
