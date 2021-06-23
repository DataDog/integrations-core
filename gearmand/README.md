# Gearman Integration

## Overview

Collect Gearman metrics to:

- Visualize Gearman performance.
- Know how many tasks are queued or running.
- Correlate Gearman performance with the rest of your applications.

## Setup

### Installation

The Gearman check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your Gearman job servers.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

1. Edit the `gearmand.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3] to start collecting your Gearman performance data. See the [sample gearmand.d/conf.yaml][4] for all available configuration options.

   ```yaml
   init_config:

   instances:
     - server: localhost
       port: 4730
   ```

2. [Restart the Agent][5]

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][1] for guidance on applying the parameters below.

| Parameter            | Value                                  |
| -------------------- | -------------------------------------- |
| `<INTEGRATION_NAME>` | `gearmand`                             |
| `<INIT_CONFIG>`      | blank or `{}`                          |
| `<INSTANCE_CONFIG>`  | `{"server":"%%host%%", "port":"4730"}` |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

#### Log collection

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

    ```yaml
    logs_enabled: true
    ```

2. Add this configuration block to your `gearmand.d/conf.yaml` file to start collecting your Gearman logs:

    ```yaml
    logs:
      - type: file
        path: /var/log/gearmand.log
        source: gearman
    ```

    Change the `path` parameter value based on your environment. See the [sample gearmand.d/conf.yaml][4] for all available configuration options.

3. [Restart the Agent][5].

See [Datadog's documentation][9] for additional information on how to configure the Agent for log collection in Kubernetes environments.

### Validation

[Run the Agent's `status` subcommand][6] and look for `gearmand` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Gearmand check does not include any events.

### Service Checks

**gearman.can_connect**:<br>
Returns `CRITICAL` if the Agent cannot connect to Gearman to collect metrics.

## Troubleshooting

Need help? Contact [Datadog support][8].

[1]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/gearmand/datadog_checks/gearmand/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/gearmand/metadata.csv
[8]: https://docs.datadoghq.com/help/
[9]: https://docs.datadoghq.com/agent/kubernetes/log/
