# Agent Check: flink

## Overview

This check monitors [Flink][1]. Datadog collects Flink metrics through Flink's
[Datadog HTTP Reporter][2], which uses [Datadog's HTTP API][3].

## Setup

### Installation

The Flink check is included in the [Datadog Agent][4] package.
No additional installation is needed on your server.

### Configuration

#### Metric collection

1. Configure the [Datadog HTTP Reporter][2] in Flink.

     In your `<FLINK_HOME>/conf/flink-conf.yaml`, add these lines, replacing `<DATADOG_API_KEY>` with your Datadog [API key][5]:

    ```yaml
    metrics.reporter.dghttp.factory.class: org.apache.flink.metrics.datadog.DatadogHttpReporterFactory
    metrics.reporter.dghttp.apikey: <DATADOG_API_KEY>
    metrics.reporter.dghttp.dataCenter: {{< region-param key="dd_datacenter" >}}
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

3. Configure additional [tags][2] in `<FLINK_HOME>/conf/flink-conf.yaml`. Here is an example of custom tags:

    ```yaml
    metrics.reporter.dghttp.scope.variables.additional: <KEY1>:<VALUE1>, <KEY1>:<VALUE2>
    ```

     **Note**: By default, any variables in metric names are sent as tags, so there is no need to add custom tags for `job_id`, `task_id`, etc.

4. Restart Flink to start sending your Flink metrics to Datadog.

#### Log collection

_Available for Agent >6.0_

1. Flink uses the `log4j` logger by default. To enable logging to a file, customize the format by editing the `log4j*.properties` configuration files in the `conf/` directory of the Flink distribution. See the [Flink logging documentation][13] for information on which configuration file is relevant for your setup. See [Flink's repository][6] for default configurations.

2. By default, the integration pipeline supports the following layout pattern:

    ```text
    %d{yyyy-MM-dd HH:mm:ss,SSS} %-5p %-60c %x - %m%n
    ```

     An example of a valid timestamp is: `2020-02-03 18:43:12,251`.

     Clone and edit the [integration pipeline][7] if you have a different format.

3. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

4. Uncomment and edit the logs configuration block in your `flink.d/conf.yaml` file. Change the `path` and `service` parameter values based on your environment. See the [sample flink.d/conf.yaml][8] for all available configuration options.

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

5. [Restart the Agent][9].

### Validation

[Run the Agent's status subcommand][10] and look for `flink` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][11] for a list of metrics provided by this integration.

### Service Checks

Flink does not include any service checks.

### Events

Flink does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][12].


[1]: https://flink.apache.org/
[2]: https://nightlies.apache.org/flink/flink-docs-release-1.16/docs/deployment/metric_reporters/#datadog
[3]: https://docs.datadoghq.com/api/?lang=bash#api-reference
[4]: https://app.datadoghq.com/account/settings/agent/latest
[5]: https://app.datadoghq.com/organization-settings/api-keys
[6]: https://github.com/apache/flink/tree/release-1.16/flink-dist/src/main/flink-bin/conf
[7]: https://docs.datadoghq.com/logs/processing/#integration-pipelines
[8]: https://github.com/DataDog/integrations-core/blob/master/flink/datadog_checks/flink/data/conf.yaml.example
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[10]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[11]: https://github.com/DataDog/integrations-core/blob/master/flink/metadata.csv
[12]: https://docs.datadoghq.com/help/
[13]: https://nightlies.apache.org/flink/flink-docs-release-1.16/docs/deployment/advanced/logging/
