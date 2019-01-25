# Kong Integration

## Overview

The Agent's Kong check tracks total requests, response codes, client connections, and more.

## Setup
### Installation

The Kong check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your Kong servers.

### Configuration

1. Edit the `kong.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][2].
    See the [sample kong.d/conf.yaml][3] for all available configuration options:
    ```yaml
    init_config:

    instances:
        # Each instance needs a `kong_status_url`. Tags are optional.
        -   kong_status_url: http://example.com:8001/status/
            tags:
            - instance:foo
        #-   kong_status_url: http://example2.com:8001/status/
        #    tags:
        #    - instance:bar
    ```

2. [Restart the Agent][4] to begin sending Kong metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][5] and look for `kong` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][6] for a list of metrics provided by this integration.

### Events
The Kong check does not include any events.

### Service Checks

`kong.can_connect`:

Returns CRITICAL if the Agent cannot connect to Kong to collect metrics, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog support][7].

## Further Reading

* [Monitor Kong with our new Datadog integration][8]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/kong/datadog_checks/kong/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/kong/metadata.csv
[7]: https://docs.datadoghq.com/help
[8]: https://www.datadoghq.com/blog/monitor-kong-datadog
