# Agent Check: flink

## Overview

This check monitors [flink][1].

## Setup

### Installation

The flink check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Configure the Datadog HTTP Reporter[3] in Flink.

Copy `/opt/flink-metrics-datadog-1.7.2.jar` into the `/lib` folder.
In the `flink/conf/flink-conf.yaml`, add these lines, replacing xxx with your Datadog API key:

```yaml
metrics.reporter.dghttp.class: org.apache.flink.metrics.datadog.DatadogHttpReporter
metrics.reporter.dghttp.apikey: xxx
metrics.reporter.dghttp.tags: myflinkapp,prod
```

2. Re-map system scopes in your `flink/conf/flink-conf.yaml`.

```yaml
metrics.scope.jm: flink.jobmanager
metrics.scope.jm.job: flink.jobmanager.job
metrics.scope.tm: flink.taskmanager
metrics.scope.tm.job: flink.taskmanager.job
metrics.scope.task: flink.task
metrics.scope.operator: flink.operator
```

NOTE: This step is optional, but required if you want your metrics to be supported
and easily searchable.

3. Add any tags you may want in `flink/conf/flink-conf.yaml`. Note that as a default,
any variables in metrics will be sent as tags[6].

```yaml
metrics.reporter.dghttp.tags: myflinkapp
```

4. [Restart the Agent][7].

#### Log collection

**Available for Agent >6.0**

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your datadog.yaml file:

    ```yaml
      logs_enabled: true
    ```

2. Uncomment and edit this configuration block at the bottom of your `flink.d/conf.yaml`:

    ```yaml
      logs:
        - type: file
          path: <PATH_TO_FLINK_DIR>/log/*.log
          source: druid
          service: <SERVICE_NAME>
          log_processing_rules:
            - type: multi_line
    ```

    Change the `path` and `service` parameter values and configure them for your environment.
    If you have changed the default directory for flink logs, then adjust your `path` accordingly.

    NOTE: Any modifications to the default properties in `log4j.appender.file.layout` will create logs _.

3. [Restart the Agent][7].

### Validation

[Run the Agent's status subcommand][10] and look for `flink` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][11] for a list of metrics provided by this integration.

### Service Checks

flink does not include any service checks.

### Events

flink does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help
[4]: https://ci.apache.org/projects/flink/flink-docs-stable/monitoring/metrics.html#system-scope
[6]: https://ci.apache.org/projects/flink/flink-docs-release-1.9/monitoring/metrics.html#datadog-orgapacheflinkmetricsdatadogdatadoghttpreporter
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[10]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[11]: https://github.com/DataDog/integrations-core/blob/master/flink/metadata.csv
