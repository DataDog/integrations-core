# Etcd Integration

![Etcd Dashboard][1]

## Overview

Collect etcd metrics to:

* Monitor the health of your etcd cluster.
* Know when host configurations may be out of sync.
* Correlate the performance of etcd with the rest of your applications.

## Setup
### Installation

The etcd check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your etcd instance(s).

### Configuration

1. Edit the `etcd.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3] to start collecting your etcd performance data.
    See the [sample etcd.d/conf.yaml][4] for all available configuration options.

    ```yaml
	init_config:

	instances:
		- url: "https://server:port" # API endpoint of your etcd instance
    ```

2. [Restart the Agent][5]

### Validation

[Run the Agent's `status` subcommand][6] and look for `etcd` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

etcd metrics are tagged with `etcd_state:leader` or `etcd_state:follower`, depending on the node status, so you can easily aggregate metrics by status.

### Events
The Etcd check does not include any events.

### Service Checks

`etcd.can_connect`:

Returns 'Critical' if the Agent cannot collect metrics from your etcd API endpoint.

`etcd.healthy`:

Returns 'Critical' if a member node is not healthy. Returns 'Unknown' if the Agent can't reach the `/health` endpoint, or if the health status is missing.

## Troubleshooting
Need help? Contact [Datadog support][8].

## Further Reading
To get a better idea of how (or why) to integrate etcd with Datadog, check out our [blog post][9] about it.


[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/etcd/images/etcd_dashboard.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/etcd/datadog_checks/etcd/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[6]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/etcd/metadata.csv
[8]: https://docs.datadoghq.com/help
[9]: https://www.datadoghq.com/blog/monitor-etcd-performance
