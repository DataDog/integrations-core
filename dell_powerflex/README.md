# Dell PowerFlex

## Overview

This check monitors [Dell PowerFlex][1] software-defined storage environments through the Datadog Agent. It collects metrics, events, and alerts from the PowerFlex Gateway REST API across the following resource types:

- **Systems**: MDM cluster state, capacity, and I/O statistics
- **Protection Domains**: capacity, rebuild, rebalance, and I/O metrics
- **Storage Pools**: capacity utilization, usage ratios, and throughput
- **Volumes**: per-volume I/O and SDC mappings
- **SDS (Storage Data Servers)**: device counts, capacity, cache, and I/O
- **SDC (Storage Data Clients)**: mapped volumes and user data I/O
- **Devices**: read/write latency, capacity, and I/O bandwidth

## Setup

### Installation

The Dell PowerFlex check is included in the [Datadog Agent][2] package. No additional installation is needed on your server.

### Configuration

1. Edit the `dell_powerflex.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][3] to start collecting your Dell PowerFlex metrics. See the [sample dell_powerflex.d/conf.yaml][4] for all available configuration options.

   ```yaml
   instances:
     - powerflex_gateway_url: https://<GATEWAY_HOST>:443
       powerflex_username: <USERNAME>
       powerflex_password: <PASSWORD>
   ```

2. [Restart the Agent][5].

#### Optional: Event and alert collection

To collect events and alerts from the PowerFlex Gateway, enable them in your configuration:

```yaml
instances:
  - powerflex_gateway_url: https://<GATEWAY_HOST>:443
    powerflex_username: <USERNAME>
    powerflex_password: <PASSWORD>
    collect_events: true
    collect_alerts: true
```

#### Optional: Resource filtering

Use `resource_filters` to control which resources are collected and whether per-resource statistics API calls are made. This is useful for large environments where you want to limit the number of API calls. Exclude filters take precedence over include filters. By default, all resources are collected with statistics enabled, except for devices which have statistics disabled by default.

```yaml
instances:
  - powerflex_gateway_url: https://<GATEWAY_HOST>:443
    powerflex_username: <USERNAME>
    powerflex_password: <PASSWORD>
    resource_filters:
      - resource: storage_pool
        property: name
        patterns:
          - "^prod-"
      - resource: sds
        property: name
        type: exclude
        patterns:
          - "^standby-"
      - resource: device
        property: name
        collect_statistics: false
```

#### Log collection

The Dell PowerFlex integration can collect logs from multiple PowerFlex components. 

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `dell_powerflex.d/conf.yaml` file to start collecting your Dell PowerFlex logs. Adjust the `path` and `service` values to match your environment:

   ```yaml
   logs:
     - type: file
       path: /opt/emc/scaleio/mdm/logs/eventLogger.log
       source: dell_powerflex
       service: <SERVICE>

     - type: file
       path: /opt/emc/scaleio/mdm/logs/trc.0
       source: dell_powerflex
       service: <SERVICE>

     - type: file
       path: /opt/emc/scaleio/sds/logs/trc.0
       source: dell_powerflex
       service: <SERVICE>

     - type: file
       path: /opt/emc/scaleio/lia/logs/trc.0
       source: dell_powerflex
       service: <SERVICE>

     - type: file
       path: /opt/emc/scaleio/activemq/data/activemq.log
       source: dell_powerflex
       service: <SERVICE>
   ```

   See the [sample dell_powerflex.d/conf.yaml][4] for all available configuration options.

3. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `dell_powerflex` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this check.

### Events

When `collect_events` is enabled, the Dell PowerFlex integration collects CRITICAL and MAJOR severity events from the PowerFlex Gateway. When `collect_alerts` is enabled, it collects alerts. Both are forwarded as Datadog events.

### Service Checks

The Dell PowerFlex integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][8].

[1]: https://www.dell.com/en-us/dt/storage/powerflex.htm
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/dell_powerflex/datadog_checks/dell_powerflex/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/dell_powerflex/metadata.csv
[8]: https://docs.datadoghq.com/help/
