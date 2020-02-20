## Overview

This integration monitors [Tenable Nessus][1] logs through the Datadog Agent.

## Setup

Follow the instructions below configure this integration for an Agent running on a host.

### Installation

To install the Tenable integration configuration on your Agent:

**Note**: This step will not be necessary in the next Agent version

1. [Install][13] the 1.0 release (`tenable==1.0.0`).

### Configuration

1. Edit the `tenable.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your Tenable nessus logs. See the [sample tenable.d/conf.yaml][3] for available configuration options.

2. [Restart the Agent][4].

## Data Collected

### Logs

The agent tails the Tenable nessus `webserver` and `backend` logs to collect data on nessus scans

### Metrics

This integration does not include any metrics.

### Events

This integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][5].

[1]: https://www.tenable.com/products/nessus
[2]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[3]: https://github.com/DataDog/integrations-core/blob/master/nessus/datadog_checks/tenable/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/help
