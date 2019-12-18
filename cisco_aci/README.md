# CiscoACI Integration

## Overview

The Cisco ACI Integration lets you:

* Track the state and health of your network
* Track the capacity of your ACI
* Monitor the switches and controllers themselves

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][1] for guidance on applying these instructions.

### Installation

The Cisco ACI check is packaged with the Agent, so simply [install the Agent][2] on a server within your network.

### Configuration

1. Edit the `cisco_aci.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3].
    See the [sample cisco_aci.d/conf.yaml][4] for all available configuration options:

    ```yaml
      init_config:
          # This check makes a lot of API calls
          # it could sometimes help to add a minimum collection interval
          # min_collection_interval: 180
      instances:
          - aci_url: localhost # the url of the aci controller
            username: datadog
            pwd: datadog
            timeout: 15
            # if it's an ssl endpoint that doesn't have a certificate, use this to ensure it can still connect
            ssl_verify: True
            tenant:
              - WebApp
              - Database
              - Datadog
    ```

2. [Restart the Agent][5] to begin sending Cisco ACI metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][6] and look for `cisco_aci` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][7] for a list of metrics provided by this integration.

### Events
The Cisco ACI check sends tenant faults as events.

### Service Checks

`cisco_aci.can_connect`:

Returns CRITICAL if the Agent cannot connect to the Cisco ACI API to collect metrics, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog support][8].

[1]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/cisco_aci/datadog_checks/cisco_aci/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/cisco_aci/metadata.csv
[8]: https://docs.datadoghq.com/help
