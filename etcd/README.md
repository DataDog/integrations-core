# Etcd Integration
{{< img src="integrations/etcd/etcd_graph.png" alt="Etcd Graph" responsive="true" popup="true">}}
## Overview

Collect etcd metrics to:

* Monitor the health of your etcd cluster.
* Know when host configurations may be out of sync.
* Correlate the performance of etcd with the rest of your applications.

## Setup
### Installation

The etcd check is packaged with the Agent, so simply [install the Agent][1] on your etcd instance(s).

### Configuration

Create a file `etcd.yaml` in the Agent's `conf.d` directory. See the [sample etcd.yaml][2] for all available configuration options:

```
init_config:

instances:
  - url: "https://server:port" # API endpoint of your etcd instance
```

[Restart the Agent][3] to begin sending etcd metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][4] and look for `etcd` under the Checks section:

```
  Checks
  ======
    [...]

    etcd
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 0 service checks

    [...]
```

## Compatibility

The etcd check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv][5] for a list of metrics provided by this integration.

etcd metrics are tagged with `etcd_state:leader` or `etcd_state:follower`, depending on the node status, so you can easily aggregate metrics by status.

### Events
The Etcd check does not include any event at this time.

### Service Checks

`etcd.can_connect`:

Returns 'Critical' if the Agent cannot collect metrics from your etcd API endpoint.

`etcd.healthy`:

Returns 'Critical' if a member node is not healthy. Returns 'Unknown' if the Agent
can't reach the `/health` endpoint, or if the health status is missing.

## Troubleshooting
Need help? Contact [Datadog Support][6].

## Further Reading
To get a better idea of how (or why) to integrate etcd with Datadog, check out our [blog post][7] about it.


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/etcd/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/etcd/metadata.csv
[6]: http://docs.datadoghq.com/help/
[7]: https://www.datadoghq.com/blog/monitor-etcd-performance/
