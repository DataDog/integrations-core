# Etcd Integration
{{< img src="integrations/etcd/etcd_graph.png" alt="Etcd Graph" responsive="true" popup="true">}}
## Overview

Collect etcd metrics to:

* Monitor the health of your etcd cluster.
* Know when host configurations may be out of sync.
* Correlate the performance of etcd with the rest of your applications.

## Setup
### Installation

The etcd check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your etcd instance(s).  

If you need the newest version of the etcd check, install the `dd-check-etcd` package; this package's check overrides the one packaged with the Agent. See the [integrations-core](https://github.com/DataDog/integrations-core#installing-the-integrations) repository for more details.

### Configuration

Create a file `etcd.yaml` in the Agent's `conf.d` directory. See the [sample etcd.yaml](https://github.com/DataDog/integrations-core/blob/master/etcd/conf.yaml.example) for all available configuration options:

```
init_config:

instances:
  - url: "https://server:port" # API endpoint of your etcd instance
```

[Restart the Agent](https://docs.datadoghq.com/agent/faq/start-stop-restart-the-datadog-agent) to begin sending etcd metrics to Datadog.

### Validation

[Run the Agent's `info` subcommand](https://docs.datadoghq.com/agent/faq/agent-status-and-information/) and look for `etcd` under the Checks section:

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

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/etcd/metadata.csv) for a list of metrics provided by this integration.

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
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading
To get a better idea of how (or why) to integrate etcd with Datadog, check out our [blog post](https://www.datadoghq.com/blog/monitor-etcd-performance/) about it.
