# Agent Check: Quarkus

## Overview

This check monitors [Quarkus][1] through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The Quarkus check is included in the [Datadog Agent][2] package starting with Agent 7.62.
No additional installation is needed on your server.

### Configuration

Follow [these steps][10] to set up metric generation in Quarkus.

Then configure the Agent:

1. Edit the `quarkus.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your Quarkus performance data. See the [sample quarkus.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

#### Collecting Logs

Follow [these steps][11] to configure Quarkus to emit logs.

Collecting logs is disabled by default in the Datadog Agent. Enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

Edit the `logs` section of your `quarkus.d/conf.yaml` file to start collecting your RabbitMQ logs:

   ```yaml
   logs:
    - type: file
      path: /var/log/application.log
      source: quarkus
      service: quarkus-app
   ```

### Validation

[Run the Agent's status subcommand][6] and look for `quarkus` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Quarkus integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://quarkus.io/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/quarkus/datadog_checks/quarkus/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/quarkus/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/quarkus/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://quarkus.io/guides/telemetry-micrometer-tutorial
[11]: https://quarkus.io/guides/logging
