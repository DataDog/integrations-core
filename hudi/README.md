# Agent Check: Hudi

## Overview

This check monitors [Hudi][1].

## Setup

### Installation

The Hudi check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Configure the [Metrics Reporter][4] in Hudi.

     Update your configuration 

    ```yaml
    hoodie.metrics.on: True
    hoodie.metrics.reporter.type: 
    ```


2. Edit the `hudi.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your hudi performance data.
   See the [sample hudi.d/conf.yaml][2] for all available configuration options.

   This check has a limit of 350 metrics per instance. The number of returned metrics is indicated in the info page.
   You can specify the metrics you are interested in by editing the configuration below.
   To learn how to customize the metrics to collect visit the [JMX Checks documentation][3] for more detailed instructions.
   If you need to monitor more metrics, contact [Datadog support][4].

2. [Restart the Agent][5]


#### Log collection

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

    ```yaml
    logs_enabled: true
    ```

2. Add this configuration block to your `hudi.d/conf.yaml` file to start collecting your VoltDB logs:

    ```yaml
    logs:
      - type: file
        path: /var/log/hudi.log
        source: voltdb
    ```

  Change the `path` value based on your environment. See the [sample `hudi.d/conf.yaml` file][3] for all available configuration options.

  3. [Restart the Agent][4].

  See [Datadog's documentation][9] for additional information on how to configure the Agent for log collection in Kubernetes environments.

### Validation

[Run the Agent's `status` subcommand][6] and look for `hudi` under the Checks section.

## Data Collected

### Metrics

Hudi does not include any metrics.

### Events

The Hudi integration does not include any events.

### Service Checks

See [service_checks.json][7] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][4].


[1]: **LINK_TO_INTEGERATION_SITE**
[2]: https://github.com/DataDog/integrations-core/blob/master/hudi/datadog_checks/hudi/data/conf.yaml.example
[3]: https://docs.datadoghq.com/integrations/java/
[4]: https://docs.datadoghq.com/help/
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/hudi/assets/service_checks.json
