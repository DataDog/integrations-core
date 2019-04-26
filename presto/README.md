# Agent Check: Presto

## Overview

This check collects [Presto][1] metrics, for example:

* Overall activity metrics: completed/failed queries, data input/output size, execution time
* Performance metrics: cluster memory, input CPU, execution CPU time

## Setup

### Installation

The Presto check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server. Install the Agent on each Coordinator and Worker node from which you wish to collect usage and performance metrics.

### Configuration

1. Edit the `presto.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your presto performance data.
   See the [sample presto.d/conf.yaml][2] for all available configuration options.

   This check has a limit of 350 metrics per instance. The number of returned metrics is indicated in the info page.
   You can specify the metrics you are interested in by editing the configuration below.
   To learn how to customize the metrics to collect visit the [JMX Checks documentation][3] for more detailed instructions.
   If you need to monitor more metrics, contact [Datadog support][4].

2. [Restart the Agent][5].

#### Metric Collection

Use the default configuration of your presto.d/conf.yaml file to activate the collection of your Presto metrics. See the sample [presto.d/conf.yaml][2] for all available configuration options.

#### Log Collection

**Available for Agent >6.0**

* Collecting logs is disabled by default in the Datadog Agent, enable it in your datadog.yaml file:

```
logs_enabled: true
```

* Add this configuration block to your presto.d/conf.yaml file to start collecting your Presto logs:

```
logs:
  - type: file
    path: /var/log/presto/*.log
    source: presto
    sourcecategory: database
    service: <SERVICE_NAME>
```

Change the `path` and `service` parameter values and configure them for your environment. See the sample [presto.d/conf.yaml][2] for all available configuration options.

[Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `presto` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this check.

### Service Checks

**presto.can_connect**
Returns CRITICAL if the Agent is unable to connect to and collect metrics from the monitored Presto instance. Returns OK otherwise.

### Events

Presto does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][4].


[1]: https://docs.datadoghq.com/integrations/presto
[2]: https://github.com/DataDog/integrations-core/blob/master/presto/datadog_checks/presto/data/conf.yaml.example
[3]: https://docs.datadoghq.com/integrations/java
[4]: https://docs.datadoghq.com/help
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/presto/metadata.csv
