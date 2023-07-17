# CiscoACI Integration

## Overview

The Cisco ACI Integration lets you:

- Track the state and health of your network
- Track the capacity of your ACI
- Monitor the switches and controllers themselves

## Setup

### Installation

The Cisco ACI check is packaged with the Agent, so simply [install the Agent][1] on a server within your network.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

1. Edit the `cisco_aci.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample cisco_aci.d/conf.yaml][3] for all available configuration options:

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

2. [Restart the Agent][4] to begin sending Cisco ACI metrics to Datadog.

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][5] for guidance on applying the parameters below.

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

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

### Missing `cisco_aci.tenant.*` metrics
If you are missing `cisco_aci.tenant.*` metrics, you can run the `test/cisco_aci_query.py` script to manually query the tenant endpoint.

Modify the `apic_url`, `apic_username`, and `apic_password` to your configuration information, and input the tenant URL for the `apic_url`.

Verify that the output you get from cURLing the endpoint matches any of the metrics collected in `datadog_checks/cisco_aci/aci_metrics.py`. If none of the statistics match, this means that the endpoint is not emitting any statistics that the integration can collect.

### Long execution times

Because this check queries all the tenants, apps, and endpoints listed before returning metrics, there may be high execution times coming from this integration.

  ```yaml
    cisco_aci (2.2.0)
  -----------------
    Instance ID: cisco_aci:d3a2958f66f46212 [OK]
    Configuration Source: file:/etc/datadog-agent/conf.d/cisco_aci.d/conf.yaml
    Total Runs: 1
    Metric Samples: Last Run: 678, Total: 678
    Events: Last Run: 0, Total: 0
    Service Checks: Last Run: 1, Total: 1
    Average Execution Time : 28m20.95s
    Last Execution Date : 2023-01-04 15:58:04 CST / 2023-01-04 21:58:04 UTC (1672869484000)
    Last Successful Execution Date : 2023-01-04 15:58:04 CST / 2023-01-04 21:58:04 UTC (1672869484000)
  ```

Need help? Contact [Datadog support][9].

[1]: https://app.datadoghq.com/account/settings/agent/latest
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/cisco_aci/datadog_checks/cisco_aci/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/cisco_aci/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/cisco_aci/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
