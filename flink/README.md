# Agent Check: flink

## Overview

This check monitors [Flink][1]. Datadog collects Flink metrics through Flink's
[Datadog HTTP Reporter][4], which uses [Datadog's HTTP API][2].

## Setup

### Installation

The Flink check is included in the [Datadog Agent][3] package.
No additional installation is needed on your server.

### Configuration

#### Metric collection

1. Configure the [Datadog HTTP Reporter][4] in Flink.

     Copy `<FLINK_HOME>/opt/flink-metrics-datadog-1.9.2.jar` into your `<FLINK_HOME>/lib` folder. In your `<FLINK_HOME>/conf/flink-conf.yaml`, add these lines, replacing `<DATADOG_API_KEY>` with your Datadog [API key][10]:

    ```yaml
    metrics.reporter.dghttp.class: org.apache.flink.metrics.datadog.DatadogHttpReporter
    metrics.reporter.dghttp.apikey: <DATADOG_API_KEY>
    ```

2. Re-map system scopes in your `<FLINK_HOME>/conf/flink-conf.yaml`.

    ```yaml
    metrics.scope.jm: flink.jobmanager
    metrics.scope.jm.job: flink.jobmanager.job
    metrics.scope.tm: flink.taskmanager
    metrics.scope.tm.job: flink.taskmanager.job
    metrics.scope.task: flink.task
    metrics.scope.operator: flink.operator
    ```

     **Note**: The system scopes must be remapped for your Flink metrics to be supported, otherwise they are submitted as custom metrics.

3. Configure additional [tags][4] in `<FLINK_HOME>/conf/flink-conf.yaml`. Here is an example of custom tags:

    ```yaml
    metrics.reporter.dghttp.tags: <KEY1>:<VALUE1>, <KEY1>:<VALUE2>
    ```

     **Note**: By default, any variables in metric names are sent as tags, so there is no need to add custom tags for `job_id`, `task_id`, etc.

4. Restart Flink to start sending your Flink metrics to the Agent.

#### Log collection

_Available for Agent >6.0_

1. Flink uses the `log4j` logger by default. To activate logging to a file and customize the format edit the `log4j.properties`, `log4j-cli.properties`, `log4j-yarn-session.properties`, or `log4j-console.properties` file. See [Flink's documentation][13] for default configurations. For example `log4j.properties` contains this configuration by default:

   ```conf
   log4j.appender.file=org.apache.log4j.FileAppender
   log4j.appender.file.file=${log.file}
   log4j.appender.file.append=false
   log4j.appender.file.layout=org.apache.log4j.PatternLayout
   log4j.appender.file.layout.ConversionPattern=%d{yyyy-MM-dd HH:mm:ss,SSS} %-5p %-60c %x - %m%n
   ```

2. By default, our integration pipeline supports the following conversion pattern:

    ```text
    %d{yyyy-MM-dd HH:mm:ss,SSS} %-5p %-60c %x - %m%n
    ```

     An example of a valid timestamp is: `2020-02-03 18:43:12,251`.

     Clone and edit the [integration pipeline][11] if you have a different format.

3. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

4. Uncomment and edit the logs configuration block in your `flink.d/conf.yaml` file. Change the `path` and `service` parameter values based on your environment. See the [sample flink.d/conf.yaml][12] for all available configuration options.

   ```yaml
   logs:
     - type: file
       path: /var/log/flink/server.log
       source: flink
       service: myapp
       #To handle multi line that starts with yyyy-mm-dd use the following pattern
       #log_processing_rules:
       #  - type: multi_line
       #    pattern: \d{4}\-(0?[1-9]|1[012])\-(0?[1-9]|[12][0-9]|3[01])
       #    name: new_log_start_with_date
   ```

5. [Restart the Agent][6].

### Validation

[Run the Agent's status subcommand][7] and look for `flink` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this integration.

### Service Checks

Flink does not include any service checks.

### Events

Flink does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][9].

[1]: https://flink.apache.org/
[2]: https://docs.datadoghq.com/api/?lang=bash#api-reference
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://ci.apache.org/projects/flink/flink-docs-release-1.9/monitoring/metrics.html#datadog-orgapacheflinkmetricsdatadogdatadoghttpreporter
[5]: https://ci.apache.org/projects/flink/flink-docs-stable/monitoring/metrics.html#system-scope
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/flink/metadata.csv
[9]: https://docs.datadoghq.com/help
[10]: https://app.datadoghq.com/account/settings#api
[11]: https://docs.datadoghq.com/logs/processing/#integration-pipelines
[12]: https://github.com/DataDog/integrations-core/blob/master/flink/datadog_checks/flink/data/conf.yaml.example
[13]: https://github.com/apache/flink/tree/master/flink-dist/src/main/flink-bin/conf
