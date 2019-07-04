# Marathon Integration

## Overview

The Agent's Marathon check lets you:

* Track the state and health of every application: see configured memory, disk, cpu, and instances; monitor the number of healthy and unhealthy tasks
* Monitor the number of queued applications and the number of deployments

## Setup

Find below instructions to install and configure the check when running the Agent on a host. See the [Autodiscovery Integration Templates documentation][1] to learn how to transpose those instructions in a containerized environment.

### Installation

The Marathon check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your Marathon master.

### Configuration

1. Edit the `marathon.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3].
    See the [sample marathon.d/conf.yaml][4] for all available configuration options:

    ```yaml
        init_config:

        instances:
          - url: https://<server>:<port> # the API endpoint of your Marathon master; required
        #   acs_url: https://<server>:<port> # if your Marathon master requires ACS auth
            user: <username> # the user for marathon API or ACS token authentication
            password: <password> # the password for marathon API or ACS token authentication
    ```

    The function of `user` and `password` depends on whether or not you configure `acs_url`; If you do, the Agent uses them to request an authentication token from ACS, which it then uses to authenticate to the Marathon API. Otherwise, the Agent uses `user` and `password` to directly authenticate to the Marathon API.

2. [Restart the Agent][5] to begin sending Marathon metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][6] and look for `marathon` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][7] for a list of metrics provided by this integration.

### Events
The Marathon check does not include any events.

### Service Checks

`marathon.can_connect`:

Returns CRITICAL if the Agent cannot connect to the Marathon API to collect metrics, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog support][8].

[1]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/?tab=agentv6#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/marathon/datadog_checks/marathon/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/marathon/metadata.csv
[8]: https://docs.datadoghq.com/help
