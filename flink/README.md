# Agent Check: flink

## Overview

This check monitors [Flink][1]. Datadog collects Flink metrics through Flink's
[Datadog HTTP Reporter][4], which uses [Datadog's HTTP API][2].

## Setup

### Installation

The Flink check is included in the [Datadog Agent][3] package.
No additional installation is needed on your server.

### Configuration

1. Configure the [Datadog HTTP Reporter][4] in Flink.

    Copy `<FLINK_HOME>/opt/flink-metrics-datadog-1.9.2.jar` into your `<FLINK_HOME>/lib` folder.
    In your `<FLINK_HOME>/conf/flink-conf.yaml`, add these lines, replacing `<API_KEY>` with your Datadog API key:

    ```yaml
    metrics.reporter.dghttp.class: org.apache.flink.metrics.datadog.DatadogHttpReporter
    metrics.reporter.dghttp.apikey: <API_KEY>
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

    **Note**: The system scopes must be remapped for your Flink metrics to be supported, otherwise they will be submitted as cutom metrics.

3. Configure additional [tags][4] in `<FLINK_HOME>/conf/flink-conf.yaml`.
    Here is an example of custom tags:

    ```yaml
    metrics.reporter.dghttp.tags: <KEY1>:<VALUE1>, <VALUE2>
    ```

    **Note**: By default, any variables in metric names will be sent as tags, so there is no need to add custom tags for `job_id`, `task_id`, etc.

4. Restart Flink to start sending your Flink metrics to the Agent.

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
