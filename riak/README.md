# Riak Check
{{< img src="integrations/riak/riak_graph.png" alt="Riak Graph" responsive="true" popup="true">}}

## Overview

This check lets you track node, vnode and ring performance metrics from RiakKV or RiakTS.

## Setup
### Installation

The Riak check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Riak servers.

### Configuration

Create a file `riak.yaml` in the Agent's `conf.d` directory. See the [sample riak.yaml](https://github.com/DataDog/integrations-core/blob/master/riak/conf.yaml.example) for all available configuration options:

```
init_config:

instances:
  - url: http://127.0.0.1:8098/stats # or whatever your stats endpoint is
```

[Restart the Agent](https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent) to start sending Riak metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information) and look for `riak` under the Checks section:

```
  Checks
  ======
    [...]

    riak
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The riak check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/riak/metadata.csv) for a list of metrics provided by this check.

### Events
The Riak check does not include any event at this time.

### Service Checks

**riak.can_connect**:

Returns CRITICAL if the Agent cannot connect to the Riak stats endpoint to collect metrics, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)
