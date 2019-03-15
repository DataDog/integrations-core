# Riak Check

![Riak Graph][1]

## Overview

This check lets you track node, vnode and ring performance metrics from RiakKV or RiakTS.

## Setup
### Installation

The Riak check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your Riak servers.

### Configuration

1. Edit the `riak.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3].
	See the [sample riak.yaml][4] for all available configuration options:

    ```yaml
    init_config:

    instances:
      	- url: http://127.0.0.1:8098/stats # or whatever your stats endpoint is
    ```

2. [Restart the Agent][5] to start sending Riak metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][6] and look for `riak` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][7] for a list of metrics provided by this check.

### Events
The Riak check does not include any events.

### Service Checks

**riak.can_connect**:

Returns CRITICAL if the Agent cannot connect to the Riak stats endpoint to collect metrics, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog support][8].

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/riak/images/riak_graph.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/riak/datadog_checks/riak/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[6]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/riak/metadata.csv
[8]: https://docs.datadoghq.com/help
