# Kong Integration

## Overview

The Agent's Kong check tracks total requests, response codes, client connections, and more.

## Setup
### Installation

The Kong check is packaged with the Agent, so simply [install the Agent][1] on your Kong servers.

### Configuration

Create a `kong.yaml` in the Datadog Agent's `conf.d` directory. See the [sample kong.yaml][2] for all available configuration options:

```
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

[Restart the Agent][3] to begin sending Kong metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][4] and look for `kong` under the Checks section:

```
  Checks
  ======
    [...]

    kong
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The kong check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv][5] for a list of metrics provided by this integration.

### Events
The Kong check does not include any event at this time.

### Service Checks

`kong.can_connect`:

Returns CRITICAL if the Agent cannot connect to Kong to collect metrics, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog Support][6].

## Further Reading

* [Monitor Kong with our new Datadog integration][7]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/kong/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/kong/metadata.csv
[6]: http://docs.datadoghq.com/help/
[7]: https://www.datadoghq.com/blog/monitor-kong-datadog/
