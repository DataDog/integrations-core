# Riak Check

![Riak Graph][8]

## Overview

This check lets you track node, vnode and ring performance metrics from RiakKV or RiakTS.

## Setup
### Installation

The Riak check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your Riak servers.

### Configuration

1. Edit the `riak.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][9].
	See the [sample riak.yaml][2] for all available configuration options:

    ```yaml
    init_config:

    instances:
      	- url: http://127.0.0.1:8098/stats # or whatever your stats endpoint is
    ```

2. [Restart the Agent][3] to start sending Riak metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][4] and look for `riak` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][5] for a list of metrics provided by this check.

### Events
The Riak check does not include any events at this time.

### Service Checks

**riak.can_connect**:

Returns CRITICAL if the Agent cannot connect to the Riak stats endpoint to collect metrics, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog Support][6].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/riak/datadog_checks/riak/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/riak/metadata.csv
[6]: https://docs.datadoghq.com/help/
[8]: https://raw.githubusercontent.com/DataDog/integrations-core/master/riak/images/riak_graph.png
[9]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
