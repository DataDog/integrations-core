# KyotoTycoon Integration

## Overview

The Agent's KyotoTycoon check tracks get, set, and delete operations, and lets you monitor replication lag.

## Setup

### Installation

The KyotoTycoon check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your KyotoTycoon servers.

### Configuration

1. Edit the `kyototycoon.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample kyototycoon.d/conf.yaml][3] for all available configuration options:

   ```yaml
   init_config:

   instances:
     ## @param report_url - string - required
     ## The report URL should be a URL to the Kyoto Tycoon "report" RPC endpoint.
     #
     - report_url: http://localhost:1978/rpc/report
   ```

2. [Restart the Agent][4].

##### Log collection

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

    ```yaml
    logs_enabled: true
    ```

2. Add this configuration block to your `kyototycoon.d/conf.yaml` file to start collecting Kyoto Tycoon logs:

    ```yaml
    logs:
      - type: file
        path: /var/data/ktserver.log
        source: kyototycoon
    ```

    Change the `path` parameter value based on your environment. See the [sample kyototycoon.d/conf.yaml][3] for all available configuration options.

3. [Restart the Agent][4].

### Validation

[Run the Agent's `status` subcommand][5] and look for `kyototycoon` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this check.

### Events

The KyotoTycoon check does not include any events.

### Service Checks

See [service_checks.json][7] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][8].


[1]: https://app.datadoghq.com/account/settings/agent/latest
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/kyototycoon/datadog_checks/kyototycoon/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/kyototycoon/metadata.csv
[7]: https://github.com/DataDog/integrations-core/blob/master/kyototycoon/assets/service_checks.json
[8]: https://docs.datadoghq.com/help/
