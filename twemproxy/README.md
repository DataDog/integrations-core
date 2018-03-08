# Twemproxy Integration

## Overview

Track overall and per-pool stats on each of your twemproxy servers. This Agent check collects metrics for client and server connections and errors, request and response rates, bytes in and out of the proxy, and more.

## Setup
### Installation

The Agent's twemproxy check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on each of your Twemproxy servers.

### Configuration

Create a file `twemproxy.yaml` in the Agent's `conf.d` directory. See the [sample twemproxy.yaml](https://github.com/DataDog/integrations-core/blob/master/twemproxy/conf.yaml.example) for all available configuration options:

```
init_config:

instances:
    - host: localhost
      port: 2222 # change if your twemproxy doesn't use the default stats monitoring port
```

[Restart the Agent](https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent) to begin sending twemproxy metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information) and look for `twemproxy` under the Checks section:

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

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/twemproxy/metadata.csv) for a list of metrics provided by this check.

### Events
The Twemproxy check does not include any event at this time.

### Service Checks

`twemproxy.can_connect`:

Returns CRITICAL if the Agent cannot connect to the Twemproxy stats endpoint to collect metrics, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)
