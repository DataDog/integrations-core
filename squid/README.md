# Squid Integration

## Overview

This check monitors [Squid][9] metrics from the Cache Manager through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check on the host Agent. For containerized environments, see the [Autodiscovery Integration Templates][1] for guidance on applying these instructions.

### Installation

The Agent's Squid check is included in the [Datadog Agent][2] package. No additional installation is needed on your Squid server.

### Configuration

1. Edit the `squid.d/conf.yaml`, in the `conf.d/` folder at the root of your [Agent's configuration directory][3]. See the [sample squid.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `squid` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this check.

### Events

The Squid check does not include any events.

### Service Checks

**squid.can_connect**:<br>
Returns `CRITICAL` if the Agent cannot connect to Squid to collect metrics, otherwise returns `OK`.

## Troubleshooting
Need help? Contact [Datadog support][8].


[1]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/squid/datadog_checks/squid/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/squid/metadata.csv
[8]: https://docs.datadoghq.com/help
[9]: http://www.squid-cache.org/
