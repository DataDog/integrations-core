# Agent Check: Pulsar

## Overview

This check monitors [Pulsar][1] through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The Pulsar check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `pulsar.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your pulsar performance data. See the [sample pulsar.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `pulsar` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this check.


### Log collection

1. The Pulsar log integration supports Pulsar's [default log format][10]. Clone and edit the [integration pipeline][11] if you have a different format.

2. Collecting logs is disabled by default in the Datadog Agent. Enable it in your `datadog.yaml` file:
   ```yaml
   logs_enabled: true
   ```

3. Uncomment and edit the logs configuration block in your `pulsar.d/conf.yaml` file. Change the path parameter value based on your environment. See the [sample pulsar.d/conf.yaml][4] for all available configuration options.
   ```yaml
    logs:
      - type: file
        path: /pulsar/logs/pulsar.log
        source: pulsar
   ```
4. [Restart the Agent][5]

### Events

The Pulsar integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://pulsar.apache.org
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/pulsar/datadog_checks/pulsar/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/pulsar/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/pulsar/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://pulsar.apache.org/docs/en/reference-configuration/#log4j
[11]: https://docs.datadoghq.com/logs/processing/#integration-pipelines
