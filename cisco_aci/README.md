# CiscoACI Integration

## Overview

The Cisco ACI Integration lets you:

- Track the state and health of your network
- Track the capacity of your ACI
- Monitor the switches and controllers themselves

## Setup

### Installation

The Cisco ACI check is packaged with the Agent, so simply [install the Agent][2] on a server within your network.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

1. Edit the `cisco_aci.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3]. See the [sample cisco_aci.d/conf.yaml][4] for all available configuration options:

   ```yaml
   init_config:

   instances:
        ## @param aci_url - string - required
        ## URL to query to gather metrics.
        #
      - aci_url: http://localhost
    
        ## @param username - string - required
        ## Authentication can use either a user auth or a certificate.
        ## If using the user auth, enter the `username` and `pwd` configuration.
        #
        username: datadog
    
        ## @param pwd - string - required
        ## Authentication can use either a user auth or a certificate.
        ## If using the user auth, enter the `username` and `pwd` configuration.
        #
        pwd: <PWD>
    
        ## @param tenant - list of strings - optional
        ## List of tenants to collect metrics data from.
        #
        # tenant:
        #   - <TENANT_1>
        #   - <TENANT_2>
   ```
   
   *NOTE*: Be sure to specify any tenants for the integration to collect metrics on applications, EPG, etc.

2. [Restart the Agent][5] to begin sending Cisco ACI metrics to Datadog.

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][1] for guidance on applying the parameters below.

| Parameter            | Value                                                                  |
| -------------------- | ---------------------------------------------------------------------- |
| `<INTEGRATION_NAME>` | `cisco_aci`                                                            |
| `<INIT_CONFIG>`      | blank or `{}`                                                          |
| `<INSTANCE_CONFIG>`  | `{"aci_url":"%%host%%", "username":"<USERNAME>", "pwd": "<PASSWORD>"}` |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's `status` subcommand][6] and look for `cisco_aci` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Cisco ACI check sends tenant faults as events.

### Service Checks

**cisco_aci.can_connect**:<br>
Returns `CRITICAL` if the Agent cannot connect to the Cisco ACI API to collect metrics, otherwise `OK`.

## Troubleshooting

Need help? Contact [Datadog support][8].

[1]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/cisco_aci/datadog_checks/cisco_aci/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/cisco_aci/metadata.csv
[8]: https://docs.datadoghq.com/help/
