# Etcd Integration

![Etcd Dashboard][8]

## Overview

Collect etcd metrics to:

* Monitor the health of your etcd cluster.
* Know when host configurations may be out of sync.
* Correlate the performance of etcd with the rest of your applications.

## Setup
### Installation

The etcd check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your etcd instance(s).

### Configuration

1. Edit the `etcd.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][9] to start collecting your etcd performance data.
    See the [sample etcd.d/conf.yaml][2] for all available configuration options.

    ```yaml
	init_config:

	instances:
		- url: "https://server:port" # API endpoint of your etcd instance
    ```

2. [Restart the Agent][3]

### Validation

[Run the Agent's `status` subcommand][4] and look for `etcd` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][5] for a list of metrics provided by this integration.

etcd metrics are tagged with `etcd_state:leader` or `etcd_state:follower`, depending on the node status, so you can easily aggregate metrics by status.

### Events
The Etcd check does not include any events at this time.

### Service Checks

`etcd.can_connect`:

Returns 'Critical' if the Agent cannot collect metrics from your etcd API endpoint.

`etcd.healthy`:

Returns 'Critical' if a member node is not healthy. Returns 'Unknown' if the Agent can't reach the `/health` endpoint, or if the health status is missing.

## Troubleshooting
Need help? Contact [Datadog Support][6].

## Further Reading
To get a better idea of how (or why) to integrate etcd with Datadog, check out our [blog post][7] about it.


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/etcd/datadog_checks/etcd/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/etcd/metadata.csv
[6]: https://docs.datadoghq.com/help/
[7]: https://www.datadoghq.com/blog/monitor-etcd-performance/
[8]: https://raw.githubusercontent.com/DataDog/integrations-core/master/etcd/images/etcd_dashboard.png
[9]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
