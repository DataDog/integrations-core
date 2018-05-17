# Riak Check
{{< img src="integrations/riak/riak_graph.png" alt="Riak Graph" responsive="true" popup="true">}}

## Overview

This check lets you track node, vnode and ring performance metrics from RiakKV or RiakTS.

## Setup
### Installation

The Riak check is packaged with the Agent, so simply [install the Agent][1] on your Riak servers.

### Configuration

1. Edit the `riak.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's directory.  
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
The Riak check does not include any event at this time.

### Service Checks

**riak.can_connect**:

Returns CRITICAL if the Agent cannot connect to the Riak stats endpoint to collect metrics, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog Support][6].

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog][7]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/riak/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/riak/metadata.csv
[6]: http://docs.datadoghq.com/help/
[7]: https://www.datadoghq.com/blog/
