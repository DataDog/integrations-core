# IIS Integration

![IIS Graph][1]

## Overview

Collect IIS metrics aggregated across all of your sites, or on a per-site basis. The IIS Agent check collects metrics for active connections, bytes sent and received, request count by HTTP method, and more. It also sends a service check for each site, letting you know whether it's up or down.

## Setup

### Installation

The IIS check is packaged with the Agent. To start gathering your IIS metrics and logs, [install the Agent][2] on your IIS servers.

<!-- xxx tabs xxx -->	
<!-- xxx tab "Host" xxx -->	

#### Host

To configure this check for an Agent running on a host:

##### Metric collection

1. Edit the `iis.d/conf.yaml` file in the [Agent's `conf.d` directory][3] at the root of your [Agent's configuration directory][4] to start collecting your IIS site data. See the [sample iis.d/conf.yaml][5] for all available configuration options.

2. [Restart the Agent][6] to begin sending IIS metrics to Datadog.

##### Log collection

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `iis.d/conf.yaml` file to start collecting your IIS Logs:

   ```yaml
   logs:
     - type: file
       path: C:\inetpub\logs\LogFiles\W3SVC1\u_ex*
       service: myservice
       source: iis
   ```

    Change the `path` and `service` parameter values and configure them for your environment. See the [sample iis.d/conf.yaml][5] for all available configuration options.

3. [Restart the Agent][6].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][7] for guidance on applying the parameters below.

##### Metric collection

| Parameter            | Value                  |
| -------------------- | ---------------------- |
| `<INTEGRATION_NAME>` | `iis`                  |
| `<INIT_CONFIG>`      | blank or `{}`          |
| `<INSTANCE_CONFIG>`  | `{"host": "%%host%%"}` |

##### Log collection

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes log collection documentation][8].

| Parameter      | Value                                            |
| -------------- | ------------------------------------------------ |
| `<LOG_CONFIG>` | `{"source": "iis", "service": "<SERVICE_NAME>"}` |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][9] and look for `iis` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][10] for a list of metrics provided by this integration.

### Events

The IIS check does not include any events.

### Service Checks

**iis.site_up**:<br>
The Agent submits this service check for each configured site in `iis.yaml`. It returns `CRITICAL` if the site's uptime is zero, otherwise returns `OK`.

## Troubleshooting

Need help? Contact [Datadog support][11].

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/iis/images/iisgraph.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/basic_agent_usage/windows/#agent-check-directory-structure
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/iis/datadog_checks/iis/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[8]: https://docs.datadoghq.com/agent/kubernetes/log/
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[10]: https://github.com/DataDog/integrations-core/blob/master/iis/metadata.csv
[11]: https://docs.datadoghq.com/help/
