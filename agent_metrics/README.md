# Agent_metrics Integration

## Overview

Get metrics from agent_metrics service in real time to:

* Visualize and monitor agent_metrics states
* Be notified about agent_metrics failovers and events.

## Setup
### Installation

The Agent Metrics check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your servers.

### Configuration

Edit the `agent_metrics.yaml` file to point to your server and port, set the masters to monitor. See the [sample agent_metrics.yaml](https://github.com/DataDog/integrations-core/blob/master/agent_metrics/conf.yaml.default) for all available configuration options.

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information) and look for `agent_metrics` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/agent_metrics/metadata.csv) for a list of metrics provided by this integration.

### Events
The Agent_metrics check does not include any event at this time.

### Service Checks
The Agent_metrics check does not include any service check at this time.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)
