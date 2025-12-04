# Cisco ACI Integration

## Overview

The Cisco ACI Integration lets you:

- Track the state and health of your network
- Track the capacity of your ACI
- Monitor the switches and controllers themselves
- The ability to monitor devices with [Network Device Monitoring][11]

**Minimum Agent version:** 6.3.2

## Setup

<div class="alert alert-info">Enabling send_ndm_metadata to send metadata from this integration has potential billing implications. See the <a href="https://www.datadoghq.com/pricing/?product=network-monitoring&tab=ndm#products"> pricing page </a> for more information.</div>

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

        ## @param send_ndm_metadata - boolean - optional - default: false
        ## Set to `true` to enable Network Device Monitoring metadata (for devices, interfaces, topology) to be sent
        ## and to allow Cisco ACI fault collection to be enabled.
        #
        # send_ndm_metadata: false

        #Enable collection of Cisco ACI fault logs (Requires send_ndm_metadata to be enabled).

        ## @param send_faultinst_faults - boolean - optional - default: false
        ## Set to `true` to enable collection of Cisco ACI faultInst faults as logs.
        
        # send_faultinst_faults: false

        ## @param send_faultdelegate_faults - boolean - optional - default: false
        ## Set to `true` to enable collection of Cisco ACI faultDelegate faults as logs.

        # send_faultdelegate_faults: false
          
   ```

2. If you have enabled `send_faultinst_faults` or `send_faultdelegate_faults`, ensure [logging is enabled][17] in your Datadog `.yaml` file:

   ```yaml
   logs_enabled: true
   ```

3. Additionally, to receive [ACI faults](#cisco-aci-faults) as logs, add the following configuration to the logs section of your `cisco_aci.d/conf.yaml` file:

   ```yaml
   logs:
     - type: integration
       source: cisco-aci
       service: cisco-aci
   ```

4. [Restart the Agent][4] to begin sending Cisco ACI metrics and optionally, ACI fault logs to Datadog.

   **Note**: Be sure to specify any tenants for the integration to collect metrics on applications (for example, EPG).

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

## Vendor profiles

Specific supported vendor profiles for this integration can be found on the [network vendors][10] page.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Cisco ACI faults

**Note**: Requires `send_ndm_metadata` to be enabled.

Cisco ACI faults are collected by the Agent and stored in Datadog as logs. They can be viewed from the [Cisco ACI dashboard][15], or by filtering for `source:cisco-aci` in the [Log Explorer][16].

There are two types of Cisco ACI faults: `fault:Inst` and `fault:Delegate`. See [fault objects and records][12] for more information.
 
The Cisco ACI config `.yaml` file can be set up to collect one or both of the following fault types:

| Fault Type          | Description                                                                 |
|---------------------|-----------------------------------------------------------------------------|
| [send_faultinst_faults][13]     | Set to `true` to enable collection of Cisco ACI `faultInst` faults as logs. |
| [send_faultdelegate_faults][14] | Set to `true` to enable collection of Cisco ACI `faultDelegate` faults as logs. |

### Events

The Cisco ACI check sends tenant faults as events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

### Missing `cisco_aci.tenant.*` metrics
If you are missing `cisco_aci.tenant.*` metrics, you can run the `tests/cisco_aci_query.py` [script][18] to manually query the tenant endpoint. 

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

### Help
Contact [Datadog support][9].

[1]: /account/settings/agent/latest
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/cisco_aci/datadog_checks/cisco_aci/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/cisco_aci/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/cisco_aci/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://docs.datadoghq.com/network_monitoring/devices/supported_devices/
[11]: https://www.datadoghq.com/product/network-monitoring/#ndm
[12]: https://www.cisco.com/c/en/us/td/docs/switches/datacenter/aci/apic/sw/all/faults/guide/b_APIC_Faults_Errors/b_IFC_Faults_Errors_chapter_01.html
[13]: https://github.com/DataDog/integrations-core/blob/c5890c7b6946a5e7e9d4c6eda993821eb6b75055/cisco_aci/assets/configuration/spec.yaml#L109-L115
[14]: https://github.com/DataDog/integrations-core/blob/c5890c7b6946a5e7e9d4c6eda993821eb6b75055/cisco_aci/assets/configuration/spec.yaml#L116-L122  
[15]: /dash/integration/242/cisco-aci---overview
[16]: /logs
[17]: https://docs.datadoghq.com/logs/log_collection/?tab=host#setup
[18]: https://github.com/DataDog/integrations-core/blob/master/cisco_aci/tests/cisco_aci_query.py