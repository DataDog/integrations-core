# KyotoTycoon Integration

## Overview

The Agent's KyotoTycoon check tracks get, set, and delete operations, and lets you monitor replication lag.

## Setup
### Installation

The KyotoTycoon check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your KyotoTycoon servers.

### Configuration

1. Edit the `kyototycoon.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][8].
    See the [sample kyototycoon.d/conf.yaml][2] for all available configuration options:

    ```yaml
    init_config:

    instances:
        #  Each instance needs a report URL.
        #  name, and optionally tags keys. The report URL should
        #  be a URL to the Kyoto Tycoon "report" RPC endpoint.
        #
        #  Complete example:
        #
        - report_url: http://localhost:1978/rpc/report
        #   name: my_kyoto_instance
        #   tags:
        #     foo: bar
        #     baz: bat
    ```

2. [Restart the Agent][7] to begin sending Kong metrics to Datadog.


### Validation

[Run the Agent's `status` subcommand][3] and look for `kyototycoon` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][4] for a list of metrics provided by this check.

### Events
The KyotoTycoon check does not include any events at this time.

### Service Checks

`kyototycoon.can_connect`:

Returns CRITICAL if the Agent cannot connect to KyotoTycoon to collect metrics, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog Support][5].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/kyototycoon/datadog_checks/kyototycoon/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[4]: https://github.com/DataDog/integrations-core/blob/master/kyototycoon/metadata.csv
[5]: https://docs.datadoghq.com/help/
[7]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[8]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
