# Twemproxy Integration

## Overview

Track overall and per-pool stats on each of your twemproxy servers. This Agent check collects metrics for client and server connections and errors, request and response rates, bytes in and out of the proxy, and more.

## Setup
### Installation

The Agent's twemproxy check is packaged with the Agent, so simply [install the Agent][1] on each of your Twemproxy servers.

### Configuration

Create a file `twemproxy.yaml` in the Agent's `conf.d` directory. See the [sample twemproxy.yaml][2] for all available configuration options:

```
init_config:

instances:
    - host: localhost
      port: 2222 # change if your twemproxy doesn't use the default stats monitoring port
```

[Restart the Agent][3] to begin sending twemproxy metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][4] and look for `twemproxy` under the Checks section:

```
  Checks
  ======
    [...]

    twemproxy
    -------
      - instance #0 [OK]
      - Collected 20 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The twemproxy check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv][5] for a list of metrics provided by this check.

### Events
The Twemproxy check does not include any event at this time.

### Service Checks

`twemproxy.can_connect`:

Returns CRITICAL if the Agent cannot connect to the Twemproxy stats endpoint to collect metrics, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog Support][6].

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog][7]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/twemproxy/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/twemproxy/metadata.csv
[6]: http://docs.datadoghq.com/help/
[7]: https://www.datadoghq.com/blog/
