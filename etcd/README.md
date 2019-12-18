# Etcd Integration

![Etcd Dashboard][1]

## Overview

Collect Etcd metrics to:

* Monitor the health of your Etcd cluster.
* Know when host configurations may be out of sync.
* Correlate the performance of Etcd with the rest of your applications.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The etcd check is included in the [Datadog Agent][3] package, so you don't need to install anything else on your Etcd instance(s).

### Configuration

1. Edit the `etcd.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][4] to start collecting your Etcd performance data.
    See the [sample etcd.d/conf.yaml][5] for all available configuration options.

    ```yaml
	init_config:

	instances:
		- url: "https://server:port" # API endpoint of your Etcd instance
    ```

2. [Restart the Agent][6]

### Validation

[Run the Agent's `status` subcommand][7] and look for `etcd` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][8] for a list of metrics provided by this integration.

Etcd metrics are tagged with `etcd_state:leader` or `etcd_state:follower`, depending on the node status, so you can easily aggregate metrics by status.

### Events
The Etcd check does not include any events.

### Service Checks

`etcd.can_connect`:

Returns 'Critical' if the Agent cannot collect metrics from your Etcd API endpoint.

`etcd.healthy`:

Returns 'Critical' if a member node is not healthy. Returns 'Unknown' if the Agent can't reach the `/health` endpoint, or if the health status is missing.

## Troubleshooting
Need help? Contact [Datadog support][9].

## Further Reading
To get a better idea of how (or why) to integrate etcd with Datadog, check out our [blog post][10] about it.


[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/etcd/images/etcd_dashboard.png
[2]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/etcd/datadog_checks/etcd/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/etcd/metadata.csv
[9]: https://docs.datadoghq.com/help
[10]: https://www.datadoghq.com/blog/monitor-etcd-performance
