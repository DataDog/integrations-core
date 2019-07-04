# Squid Integration

## Overview

This integration lets you monitor your Squid metrics from the Cache Manager directly in Datadog.

## Setup

Find below instructions to install and configure the check when running the Agent on a host. See the [Autodiscovery Integration Templates documentation](https://docs.datadoghq.com/agent/autodiscovery/integrations/) to learn how to transpose those instructions in a containerized environment.

### Installation

The Agent's Squid check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your Squid server.

### Configuration

1. Edit the `squid.d/conf.yaml`, in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample squid.d/conf.yaml][3] for all available configuration options:

```
    init_config:

    instances:
        # A list of squid instances identified by their name

        - name: my_squid
        #   host: localhost  # The hostname or ip address of the squid server. Default to 'localhost'
        #   port: 3128  # The port where the squid server is listening. Default to 3128
        #   tags: ['custom:tag']  # A list of tags that you wish to send with your squid metrics
```

2. [Restart the Agent][4] to start sending metrics and service checks to Datadog.

### Validation

[Run the Agent's status subcommand][5] and look for `squid` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6]

### Events

The Squid check does not include any events at this time

### Service Checks

**squid.can_connect**:
Returns CRITICAL if the Agent cannot connect to Squid to collect metrics, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog support][7].


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/?tab=agentv6#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/squid/datadog_checks/squid/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/squid/metadata.csv
[7]: https://docs.datadoghq.com/help
