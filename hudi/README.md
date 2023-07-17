# Agent Check: Hudi

## Overview

This check monitors [Hudi][1].
It is compatible with Hudi [versions][2] `0.10.0` and above.

## Setup

### Installation

The Hudi check is included in the [Datadog Agent][3] package.
No additional installation is needed on your server.

### Configuration

1. [Configure][4] the [JMX Metrics Reporter][5] in Hudi:

    ```
    hoodie.metrics.on=true
    hoodie.metrics.reporter.type=JMX
    hoodie.metrics.jmx.host=<JMX_HOST>
    hoodie.metrics.jmx.port=<JMX_PORT>
    ```


2. Edit the `hudi.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your hudi performance data.
   See the [sample hudi.d/conf.yaml][6] for all available configuration options.

   This check has a limit of 350 metrics per instance. The number of returned metrics is indicated when running the Datadog Agent [status command][7].
   You can specify the metrics you are interested in by editing the [configuration][6].
   To learn how to customize the metrics to collect see the [JMX Checks documentation][8] for more detailed instructions.
   If you need to monitor more metrics, contact [Datadog support][9].

3. [Restart the Agent][10]


### Validation

[Run the Agent's `status` subcommand][11] and look for `hudi` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][12] for a list of metrics provided by this integration.


### Log collection

_Available for Agent versions >6.0_

1. Hudi uses the `log4j` logger by default. To customize the format, edit the `log4j.properties` file in either your [Flink][13] or [Spark][14] `conf` directory. An example `log4j.properties` file is:

   ```conf
    log4j.rootCategory=INFO, file
    log4j.appender.file=org.apache.log4j.FileAppender
    log4j.appender.file.File=/var/log/hudi.log
    log4j.appender.file.append=false
    log4j.appender.file.layout=org.apache.log4j.PatternLayout
    log4j.appender.file.layout.ConversionPattern=%d{yyyy-MM-dd HH:mm:ss,SSS} %-5p %-60c %x - %m%n
   ```

2. By default, Datadog's integration pipeline supports the following conversion pattern:

    ```text
    %d{yyyy-MM-dd HH:mm:ss,SSS} %-5p %-60c %x - %m%n
    ```

     An example of a valid timestamp is: `2020-02-03 18:43:12,251`.

     Clone and edit the [integration pipeline][15] if you have a different format.

3. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

4. Uncomment and edit the logs configuration block in your `hudi.d/conf.yaml` file. Change the `path` and `service` parameter values based on your environment. See the [sample hudi.d/conf.yaml][6] for all available configuration options.

   ```yaml
   logs:
     - type: file
       path: /var/log/hudi.log
       source: hudi
       log_processing_rules:
         - type: multi_line
           pattern: \d{4}\-(0?[1-9]|1[012])\-(0?[1-9]|[12][0-9]|3[01])
           name: new_log_start_with_date
   ```
### Events

The Hudi integration does not include any events.

### Service Checks

See [service_checks.json][7] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://hudi.apache.org/
[2]: https://github.com/apache/hudi/releases
[3]: https://app.datadoghq.com/account/settings/agent/latest
[4]: https://hudi.apache.org/docs/configurations#Metrics-Configurations
[5]: https://hudi.apache.org/docs/metrics/#jmxmetricsreporter
[6]: https://github.com/DataDog/integrations-core/blob/master/hudi/datadog_checks/hudi/data/conf.yaml.example
[7]: https://github.com/DataDog/integrations-core/blob/master/hudi/assets/service_checks.json
[8]: https://docs.datadoghq.com/integrations/java/
[9]: https://docs.datadoghq.com/help/
[10]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[11]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[12]: https://github.com/DataDog/integrations-core/blob/master/hudi/metadata.csv
[13]: https://github.com/apache/flink/tree/release-1.11.4/flink-dist/src/main/flink-bin/conf
[14]: https://github.com/apache/spark/tree/v3.1.2/conf
[15]: https://docs.datadoghq.com/logs/processing/#integration-pipelines
