# Consul Integration

![Consul Dash][1]

## Overview

The Datadog Agent collects many metrics from Consul nodes, including those for:

- Total Consul peers
- Service health - for a given service, how many of its nodes are up, passing, warning, critical?
- Node health - for a given node, how many of its services are up, passing, warning, critical?
- Network coordinates - inter- and intra-datacenter latencies

The _Consul_ Agent can provide further metrics via DogStatsD. These metrics are more related to the internal health of Consul itself, not to services which depend on Consul. There are metrics for:

- Serf events and member flaps
- The Raft protocol
- DNS performance

And many more.

Finally, in addition to metrics, the Datadog Agent also sends a service check for each of Consul's health checks, and an event after each new leader election.

## Setup

### Installation

The Datadog Agent's Consul check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your Consul nodes.

### Configuration

#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

##### Metric Collection

1. Edit the `consul.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][4] to start collecting your Consul metrics. See the [sample consul.d/conf.yaml][5] for all available configuration options.

   ```yaml
   init_config:

   instances:
     ## @param url - string - required
     ## Where your Consul HTTP Server Lives
     ## Point the URL at the leader to get metrics about your Consul Cluster.
     ## Remind to use https instead of http if your Consul setup is configured to do so.
     #
     - url: http://localhost:8500
   ```
   
2. [Restart the Agent][6].

Reload the Consul Agent to start sending more Consul metrics to DogStatsD.

##### Log collection

_Available for Agent versions >6.0_

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
   See the [sample consul.d/conf.yaml][5] for all available configuration options.

3. [Restart the Agent][6].

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][7] for guidance on applying the parameters below.

##### Metric collection

| Parameter            | Value                              |
| -------------------- | ---------------------------------- |
| `<INTEGRATION_NAME>` | `consul`                           |
| `<INIT_CONFIG>`      | blank or `{}`                      |
| `<INSTANCE_CONFIG>`  | `{"url": "https://%%host%%:8500"}` |

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes log collection documentation][8].

| Parameter      | Value                                               |
| -------------- | --------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "consul", "service": "<SERVICE_NAME>"}` |

#### DogStatsD

Optionally, you can configure Consul to also send data to the Agent through [DogStatsD][3] instead of relying on the Agent to pull the data from Consul. 

1. Configure Consul to send DogStatsD metrics by adding the `dogstatsd_addr` nested under the top-level `telemetry` key in the main Consul configuration file:

    ```conf
    {
      ...
      "telemetry": {
        "dogstatsd_addr": "127.0.0.1:8125"
      },
      ...
    }
    ```

1. Update the [Datadog Agent main configuration file][16] `datadog.yaml` by adding the following configs to ensure metrics are tagged correctly:

   ```yaml
   # dogstatsd_mapper_cache_size: 1000  # default to 1000
   dogstatsd_mapper_profiles:
     - name: consul
       prefix: "consul."
       mappings:
         - match: 'consul\.http\.([a-zA-Z]+)\.(.*)'
           match_type: "regex"
           name: "consul.http.request"
           tags:
             http_method: "$1"
             path: "$2"
         - match: 'consul\.raft\.replication\.appendEntries\.logs\.([0-9a-f-]+)'
           match_type: "regex"
           name: "consul.raft.replication.appendEntries.logs"
           tags:
             consul_node_id: "$1"
         - match: 'consul\.raft\.replication\.appendEntries\.rpc\.([0-9a-f-]+)'
           match_type: "regex"
           name: "consul.raft.replication.appendEntries.rpc"
           tags:
             consul_node_id: "$1"
         - match: 'consul\.raft\.replication\.heartbeat\.([0-9a-f-]+)'
           match_type: "regex"
           name: "consul.raft.replication.heartbeat"
           tags:
             consul_node_id: "$1"
   ```

3. [Restart the Agent][6].

### Validation

[Run the Agent's status subcommand][9] and look for `consul` under the Checks section.

**Note**: If your Consul nodes have debug logging enabled, you'll see the Datadog Agent's regular polling in the Consul log:

```text
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

See [metadata.csv][10] for a list of metrics provided by this integration.

See [Consul's Telemetry doc][11] for a description of metrics the Consul Agent sends to DogStatsD.

See [Consul's Network Coordinates doc][12] for details on how the network latency metrics are calculated.

### Events

**consul.new_leader**:<br>
The Datadog Agent emits an event when the Consul cluster elects a new leader, tagging it with `prev_consul_leader`, `curr_consul_leader`, and `consul_datacenter`.

### Service Checks

**consul.check**:<br>
The Datadog Agent submits a service check for each of Consul's health checks, tagging each with:

- `service:<name>`, if Consul reports a `ServiceName`
- `consul_service_id:<id>`, if Consul reports a `ServiceID`

## Troubleshooting

Need help? Contact [Datadog support][13].

## Further Reading

- [Monitor Consul health and performance with Datadog][14]
- [Consul at Datadog][15]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/consul/images/consul-dash.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/developers/dogstatsd/
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/consul/datadog_checks/consul/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[8]: https://docs.datadoghq.com/agent/kubernetes/log/
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[10]: https://github.com/DataDog/integrations-core/blob/master/consul/metadata.csv
[11]: https://www.consul.io/docs/agent/telemetry.html
[12]: https://www.consul.io/docs/internals/coordinates.html
[13]: https://docs.datadoghq.com/help/
[14]: https://www.datadoghq.com/blog/monitor-consul-health-and-performance-with-datadog
[15]: https://engineering.datadoghq.com/consul-at-datadog
[16]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/
