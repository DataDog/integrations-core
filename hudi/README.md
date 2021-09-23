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

   This check has a limit of 350 metrics per instance. The number of returned metrics is indicated when running the Datadog Agent [status command][12].
   You can specify the metrics you are interested in by editing the [configuration][6].
   To learn how to customize the metrics to collect visit the [JMX Checks documentation][7] for more detailed instructions.
   If you need to monitor more metrics, contact [Datadog support][8].

3. [Restart the Agent][9]


### Validation

[Run the Agent's `status` subcommand][10] and look for `hudi` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][11] for a list of metrics provided by this integration.

### Events

The Hudi integration does not include any events.

### Service Checks

See [service_checks.json][12] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][8].

[1]: https://hudi.apache.org/
[2]: https://github.com/apache/hudi/releases
[3]: https://docs.datadoghq.com/agent/
[4]: https://hudi.apache.org/docs/configurations#Metrics-Configurations
[5]: https://hudi.apache.org/docs/metrics/#jmxmetricsreporter
[6]: https://github.com/DataDog/integrations-core/blob/master/hudi/datadog_checks/hudi/data/conf.yaml.example
[7]: https://docs.datadoghq.com/integrations/java/
[8]: https://docs.datadoghq.com/help/
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[10]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[11]: https://github.com/DataDog/integrations-core/blob/master/hudi/metadata.csv
[12]: https://github.com/DataDog/integrations-core/blob/master/hudi/assets/service_checks.json
