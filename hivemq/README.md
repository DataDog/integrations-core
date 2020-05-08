# Agent Check: HiveMQ

## Overview

This check monitors [HiveMQ][1].

## Setup

### Installation

The HiveMQ check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

##### Metric collection

1. Edit the `hivemq.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your HiveMQ performance data.
   See the [sample hivemq.d/conf.yaml][3] for all available configuration options.

   This check has a limit of 350 metrics per instance. The number of returned metrics is indicated in the info page.
   You can specify the metrics you are interested in by editing the configuration below.
   To learn how to customize the metrics to collect visit the [JMX Checks documentation][4] for more detailed instructions.
   If you need to monitor more metrics, contact [Datadog support][5].

2. [Restart the Agent][6]

##### Log collection

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Add the following configuration block to your `hivemq.d/conf.yaml` file. Change the `path` and `service` parameter values based on your environment. See the [sample hivemq.d/conf.yaml][3] for all available configuration options.

   ```yaml
   logs:
     - type: file
       path: /var/log/hivemq.log
       source: hivemq
       service: <SERVICE>
       log_processing_rules:
         - type: multi_line
           name: log_start_with_date
           pattern: \d{4}\.\d{2}\.\d{2}
   ```

3. [Restart the Agent][6].

#### Containerized

##### Metric collection

For containerized environments, see the [Autodiscovery with JMX][7] guide.

##### Log collection

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Docker log collection][8].

| Parameter      | Value                                              |
| -------------- | -------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "hivemq", "service": "<SERVICE_NAME>"}` |

### Validation

[Run the Agent's status subcommand][9] and look for `hivemq` under the **JMXFetch** section:

```text
========
JMXFetch
========
  Initialized checks
  ==================
    hivemq
      instance_name : hivemq-localhost-9999
      message :
      metric_count : 46
      service_check_count : 0
      status : OK
```

## Data Collected

### Metrics

See [metadata.csv][10] for a list of metrics provided by this check.

### Service Checks

**hivemq.can_connect**:<br>
Returns `CRITICAL` if the Agent is unable to connect to and collect metrics from the monitored HiveMQ instance, otherwise returns `OK`.

### Events

HiveMQ does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][5].

[1]: https://www.hivemq.com/hivemq/
[2]: https://docs.datadoghq.com/agent/
[3]: https://github.com/DataDog/integrations-core/blob/master/hivemq/datadog_checks/hivemq/data/conf.yaml.example
[4]: https://docs.datadoghq.com/integrations/java
[5]: https://docs.datadoghq.com/help
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/agent/guide/autodiscovery-with-jmx/?tab=containerizedagent
[8]: https://docs.datadoghq.com/agent/docker/log/
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[10]: https://github.com/DataDog/integrations-core/blob/master/hivemq/metadata.csv
