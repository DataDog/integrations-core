# Agent Check: Hudi

## Overview

This check monitors [Hudi][1].

## Setup

### Installation

The Hudi check is included in the [Datadog Agent][9] package.
No additional installation is needed on your server.

### Configuration

1. Configure the [JMX Metrics Reporter][8] in Hudi:

    ```yaml
    hoodie.metrics.on=true
    hoodie.metrics.reporter.type=JMX
    hoodie.metrics.jmx.host=<JMX_HOST>
    hoodie.metrics.jmx.port=<JMX_PORT>
    ```


2. Edit the `hudi.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your hudi performance data.
   See the [sample hudi.d/conf.yaml][2] for all available configuration options.

   This check has a limit of 350 metrics per instance. The number of returned metrics is indicated in the info page.
   You can specify the metrics you are interested in by editing the configuration below.
   To learn how to customize the metrics to collect visit the [JMX Checks documentation][3] for more detailed instructions.
   If you need to monitor more metrics, contact [Datadog support][4].

2. [Restart the Agent][5]


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


[1]: https://hudi.apache.org/
[2]: https://github.com/DataDog/integrations-core/blob/master/hudi/datadog_checks/hudi/data/conf.yaml.example
[3]: https://docs.datadoghq.com/integrations/java/
[4]: https://docs.datadoghq.com/help/
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/hudi/assets/service_checks.json
[8]: https://hudi.apache.org/docs/metrics/#jmxmetricsreporter
[9]: https://docs.datadoghq.com/agent/
