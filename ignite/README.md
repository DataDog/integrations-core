# Agent Check: Ignite

## Overview

This check monitors [Ignite][1].

## Setup

### Installation

The Ignite check is included in the [Datadog Agent][2] package. No additional installation is needed on your server.

### Configuration

#### Ignite setup

JMX metrics exporter is enabled by default, but you may need to choose the port exposed, or enable authentication depending on your network security. The official docker image uses `49112` by default.

For logging, it's strongly suggested to enable [log4j][3] to benefit from a log format with full dates.

#### Host

1. Edit the `ignite.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your ignite performance data. See the [sample ignite.d/conf.yaml][4] for all available configuration options.

   This check has a limit of 350 metrics per instance. The number of returned metrics is indicated in the info page.
   You can specify the metrics you are interested in by editing the configuration below.
   To learn how to customize the metrics to collect visit the [JMX Checks documentation][5] for more detailed instructions.
   If you need to monitor more metrics, contact [Datadog support][6].

2. [Restart the Agent][7]

##### Log collection

_Available for Agent versions >6.0_

1. Collecting logs is disabled by default in the Datadog Agent, you need to enable it in `datadog.yaml`:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `ignite.d/conf.yaml` file to start collecting your Ignite logs:

   ```yaml
     logs:
       - type: file
         path: <IGNITE_HOME>/work/log/ignite-*.log
         source: ignite
         service: '<SERVICE_NAME>'
         log_processing_rules:
           - type: multi_line
             name: new_log_start_with_date
             pattern: \[\d{4}\-\d{2}\-\d{2}
   ```

    Change the `path` and `service` parameter values and configure them for your environment. See the [sample ignite.d/conf.yaml][4] for all available configuration options.

3. [Restart the Agent][7].

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][8] for guidance on applying the parameters below.

##### Metric collection

To collect metrics with the Datadog-Ignite integration, see the [Autodiscovery with JMX][9] guide.

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Docker log collection][10].

| Parameter      | Value                                                                                                                                                             |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "ignite", "service": "<SERVICE_NAME>", "log_processing_rules":{"type":"multi_line","name":"new_log_start_with_date", "pattern":"\d{4}\-\d{2}\-\d{2}"}}` |


### Validation

[Run the Agent's `status` subcommand][11] and look for `ignite` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][12] for a list of metrics provided by this integration.

### Service Checks

**ignite.can_connect**:<br>
Returns `CRITICAL` if the Agent is unable to connect to and collect metrics from the monitored Ignite instance, otherwise returns `OK`.

### Events

The Ignite integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][4].


[1]: https://ignite.apache.org/
[2]: https://docs.datadoghq.com/agent
[3]: https://apacheignite.readme.io/docs/logging#section-log4j
[4]: https://github.com/DataDog/integrations-core/blob/master/ignite/datadog_checks/ignite/data/conf.yaml.example
[5]: https://docs.datadoghq.com/integrations/java
[6]: https://docs.datadoghq.com/help
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[8]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[9]: https://docs.datadoghq.com/agent/guide/autodiscovery-with-jmx/?tab=containerizedagent
[10]: https://docs.datadoghq.com/agent/docker/log/
[11]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[12]: https://github.com/DataDog/integrations-core/blob/master/ignite/metadata.csv
