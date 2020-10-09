# Mapreduce Integration

![MapReduce Dashboard][1]

## Overview

Get metrics from mapreduce service in real time to:

- Visualize and monitor mapreduce states
- Be notified about mapreduce failovers and events.

## Setup

### Installation

The Mapreduce check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your servers.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

1. Edit the `mapreduce.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3] to point to your server and port, set the masters to monitor. See the [sample mapreduce.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][6] for guidance on applying the parameters below.

| Parameter            | Value                                                                                         |
| -------------------- | --------------------------------------------------------------------------------------------- |
| `<INTEGRATION_NAME>` | `mapreduce`                                                                                   |
| `<INIT_CONFIG>`      | blank or `{}`                                                                                 |
| `<INSTANCE_CONFIG>`  | `{"resourcemanager_uri": "https://%%host%%:8088", "cluster_name":"<MAPREDUCE_CLUSTER_NAME>"}` |

##### Log collection

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

    ```yaml
    logs_enabled: true
    ```

2. Uncomment and edit the logs configuration block in your `mapreduce.d/conf.yaml` file. Change the `type`, `path`, and `service` parameter values based on your environment. See the [sample mapreduce.d/conf.yaml][4] for all available configuration options.

    ```yaml
    logs:
      - type: file
        path: <LOG_FILE_PATH>
        source: mapreduce
        service: <SERVICE_NAME>
        # To handle multi line that starts with yyyy-mm-dd use the following pattern
        # log_processing_rules:
        #   - type: multi_line
        #     pattern: \d{4}\-\d{2}\-\d{2} \d{2}:\d{2}:\d{2},\d{3}
        #     name: new_log_start_with_date
    ```

3. [Restart the Agent][5].

See [Datadog's documentation][14] for additional information on how to configure the Agent for log collection in Docker environments.

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][7] and look for `mapreduce` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this integration.

### Events

The Mapreduce check does not include any events.

### Service Checks

**mapreduce.resource_manager.can_connect**

Returns `CRITICAL` if the Agent is unable to connect to the Resource Manager.
Returns `OK` otherwise.

**mapreduce.application_master.can_connect**

Returns `CRITICAL` if the Agent is unable to connect to the Application Master.
Returns `OK` otherwise.

## Troubleshooting

Need help? Contact [Datadog support][9].

## Further Reading

- [Hadoop architectural overview][10]
- [How to monitor Hadoop metrics][11]
- [How to collect Hadoop metrics][12]
- [How to monitor Hadoop with Datadog][13]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/mapreduce/images/mapreduce_dashboard.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/mapreduce/datadog_checks/mapreduce/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#restart-the-agent
[6]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/mapreduce/metadata.csv
[9]: https://docs.datadoghq.com/help/
[10]: https://www.datadoghq.com/blog/hadoop-architecture-overview
[11]: https://www.datadoghq.com/blog/monitor-hadoop-metrics
[12]: https://www.datadoghq.com/blog/collecting-hadoop-metrics
[13]: https://www.datadoghq.com/blog/monitor-hadoop-metrics-datadog
[14]: https://docs.datadoghq.com/agent/docker/log/
