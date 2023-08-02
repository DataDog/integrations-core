# Gearman Integration

## Overview

Collect Gearman metrics to:

- Visualize Gearman performance.
- Know how many tasks are queued or running.
- Correlate Gearman performance with the rest of your applications.

## Setup

### Installation

The Gearman check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your Gearman job servers.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

1. Edit the `gearmand.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][2] to start collecting your Gearman performance data. See the [sample gearmand.d/conf.yaml][3] for all available configuration options.

   ```yaml
   init_config:

   instances:
     - server: localhost
       port: 4730
   ```

2. [Restart the Agent][4]

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][5] for guidance on applying the parameters below.

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

    Change the `path` parameter value based on your environment. See the [sample gearmand.d/conf.yaml][3] for all available configuration options.

3. [Restart the Agent][4].

See [Kubernetes Log Collection][6] for information on configuring the Agent for log collection in Kubernetes environments.

### Validation

[Run the Agent's `status` subcommand][7] and look for `gearmand` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this integration.

### Events

The Gearman check does not include any events.

### Service Checks

See [service_checks.json][9] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][10].

[1]: https://app.datadoghq.com/account/settings/agent/latest
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/gearmand/datadog_checks/gearmand/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[6]: https://docs.datadoghq.com/agent/kubernetes/log/
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/gearmand/metadata.csv
[9]: https://github.com/DataDog/integrations-core/blob/master/gearmand/assets/service_checks.json
[10]: https://docs.datadoghq.com/help/
