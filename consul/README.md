# Consul Integration

![Consul Dash][12]

## Overview

The Datadog Agent collects many metrics from Consul nodes, including those for:

* Total Consul peers
* Service health - for a given service, how many of its nodes are up, passing, warning, critical?
* Node health - for a given node, how many of its services are up, passing, warning, critical?
* Network coordinates - inter- and intra-datacenter latencies

The _Consul_ Agent can provide further metrics via DogStatsD. These metrics are more related to the internal health of Consul itself, not to services which depend on Consul. There are metrics for:

* Serf events and member flaps
* The Raft protocol
* DNS performance

And many more.

Finally, in addition to metrics, the Datadog Agent also sends a service check for each of Consul's health checks, and an event after each new leader election.

## Setup
### Installation

The Datadog Agent's Consul check is included in the [Datadog Agent][4] package, so you don't need to install anything else on yourConsul nodes.

### Configuration

Edit the `consul.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][13] to start collecting your Consul [metrics](#metric-collection) and [logs](#log-collection).
See the [sample consul.d/conf.yaml][2] for all available configuration options.

#### Metric Collection

1. Add this configuration block to your `consul.d/conf.yaml` file to start gathering your [Consul Metrics](#metrics):

    ```yaml
    init_config:

    instances:
        # where the Consul HTTP Server Lives
        # use 'https' if Consul is configured for SSL
        - url: http://localhost:8500
          # again, if Consul is talking SSL
          # client_cert_file: '/path/to/client.concatenated.pem'

          # submit per-service node status and per-node service status?
          catalog_checks: true

          # emit leader election events
          self_leader_check: true

          network_latency_checks: true
    ```

    See the [sample consul.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][3] to start sending Consul metrics to Datadog.

#### Connect Consul Agent to DogStatsD

In the main Consul configuration file, add your `dogstatsd_addr` nested under the top-level `telemetry` key:

```
{
  ...
  "telemetry": {
    "dogstatsd_addr": "127.0.0.1:8125"
  },
  ...
}
```

Reload the Consul Agent to start sending more Consul metrics to DogStatsD.

#### Log Collection

**Available for Agent >6.0**

1. Collecting logs is disabled by default in the Datadog Agent, enable it in `datadog.yaml` with:

    ```yaml
    logs_enabled: true
    ```

2. Add this configuration block to your `consul.yaml` file to start collecting your Consul Logs:

    ```yaml
      logs:
          - type: file
            path: /var/log/consul_server.log
            source: consul
            service: myservice
    ```
    Change the `path` and `service` parameter values and configure them for your environment.
    See the [sample consul.d/conf.yaml][2] for all available configuration options.

3. [Restart the Agent][3].

**Learn more about log collection [in the log documentation][4]**

### Validation

[Run the Agent's `status` subcommand][5] and look for `consul` under the Checks section.

**Note**: If your Consul nodes have debug logging enabled, you'll see the Datadog Agent's regular polling in the Consul log:

```
    2017/03/27 21:38:12 [DEBUG] http: Request GET /v1/status/leader (59.344us) from=127.0.0.1:53768
    2017/03/27 21:38:12 [DEBUG] http: Request GET /v1/status/peers (62.678us) from=127.0.0.1:53770
    2017/03/27 21:38:12 [DEBUG] http: Request GET /v1/health/state/any (106.725us) from=127.0.0.1:53772
    2017/03/27 21:38:12 [DEBUG] http: Request GET /v1/catalog/services (79.657us) from=127.0.0.1:53774
    2017/03/27 21:38:12 [DEBUG] http: Request GET /v1/health/service/consul (153.917us) from=127.0.0.1:53776
    2017/03/27 21:38:12 [DEBUG] http: Request GET /v1/coordinate/datacenters (71.778us) from=127.0.0.1:53778
    2017/03/27 21:38:12 [DEBUG] http: Request GET /v1/coordinate/nodes (84.95us) from=127.0.0.1:53780
```

#### Consul Agent to DogStatsD

Use `netstat` to verify that Consul is sending its metrics, too:

```shell
$ sudo netstat -nup | grep "127.0.0.1:8125.*ESTABLISHED"
udp        0      0 127.0.0.1:53874         127.0.0.1:8125          ESTABLISHED 23176/consul
```

## Data Collected
### Metrics

See [metadata.csv][6] for a list of metrics provided by this integration.

See [Consul's Telemetry doc][7] for a description of metrics the Consul Agent sends to DogStatsD.

See [Consul's Network Coordinates doc][8] if you're curious about how the network latency metrics are calculated.

### Events

`consul.new_leader`:

The Datadog Agent emits an event when the Consul cluster elects a new leader, tagging it with `prev_consul_leader`, `curr_consul_leader`, and `consul_datacenter`.

### Service Checks

`consul.check`:

The Datadog Agent submits a service check for each of Consul's health checks, tagging each with:

* `service:<name>`, if Consul reports a `ServiceName`
* `consul_service_id:<id>`, if Consul reports a `ServiceID`

## Troubleshooting
Need help? Contact [Datadog Support][9].

## Further Reading

* [Monitor Consul health and performance with Datadog][10]
* [Consul at Datadog][11]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/consul/datadog_checks/consul/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/logs
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/consul/metadata.csv
[7]: https://www.consul.io/docs/agent/telemetry.html
[8]: https://www.consul.io/docs/internals/coordinates.html
[9]: https://docs.datadoghq.com/help/
[10]: https://www.datadoghq.com/blog/monitor-consul-health-and-performance-with-datadog
[11]: https://engineering.datadoghq.com/consul-at-datadog/
[12]: https://raw.githubusercontent.com/DataDog/integrations-core/master/consul/images/consul-dash.png
[13]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
