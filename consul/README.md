# Consul Integration

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

The Datadog Agent's Consul Check is included in the Agent package, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Consul nodes.

### Configuration

#### Connect Datadog Agent to Consul Agent

Create a `consul.yaml` in the Datadog Agent's `conf.d` directory. See the [sample consul.yaml](https://github.com/DataDog/integrations-core/blob/master/consul/conf.yaml.example) for all available configuration options:

```
init_config:

instances:
    # where the Consul HTTP Server Lives
    # use 'https' if Consul is configured for SSL
    - url: http://localhost:8500
      # again, if Consul is talking SSL
      # client_cert_file: '/path/to/client.concatenated.pem'

      # submit per-service node status and per-node service status?
      catalog_checks: yes

      # emit leader election events
      self_leader_check: yes

      network_latency_checks: yes
```

See the [sample consul.yaml](https://github.com/DataDog/integrations-core/blob/master/consul/conf.yaml.example) for all available configuration options.

[Restart the Agent](https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent) to start sending Consul metrics to Datadog.

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

### Validation

#### Datadog Agent to Consul Agent

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information) and look for `consul` under the Checks section:

```
  Checks
  ======
	[...]

    consul (5.12.1)
    ---------------
      - instance #0 [OK]
      - Collected 9 metrics, 0 events & 2 service checks

    [...]
```

Also, if your Consul nodes have debug logging enabled, you'll see the Datadog Agent's regular polling in the Consul log:

```
    2017/03/27 21:38:12 [DEBUG] http: Request GET /v1/status/leader (59.344µs) from=127.0.0.1:53768
    2017/03/27 21:38:12 [DEBUG] http: Request GET /v1/status/peers (62.678µs) from=127.0.0.1:53770
    2017/03/27 21:38:12 [DEBUG] http: Request GET /v1/health/state/any (106.725µs) from=127.0.0.1:53772
    2017/03/27 21:38:12 [DEBUG] http: Request GET /v1/catalog/services (79.657µs) from=127.0.0.1:53774
    2017/03/27 21:38:12 [DEBUG] http: Request GET /v1/health/service/consul (153.917µs) from=127.0.0.1:53776
    2017/03/27 21:38:12 [DEBUG] http: Request GET /v1/coordinate/datacenters (71.778µs) from=127.0.0.1:53778
    2017/03/27 21:38:12 [DEBUG] http: Request GET /v1/coordinate/nodes (84.95µs) from=127.0.0.1:53780
```

#### Consul Agent to DogStatsD

Use `netstat` to verify that Consul is sending its metrics, too:

```
$ sudo netstat -nup | grep "127.0.0.1:8125.*ESTABLISHED"
udp        0      0 127.0.0.1:53874         127.0.0.1:8125          ESTABLISHED 23176/consul
```

## Compatibility

The Consul check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/consul/metadata.csv) for a list of metrics provided by the Datadog Agent's Consul check.

See [Consul's Telemetry doc](https://www.consul.io/docs/agent/telemetry.html) for a description of metrics the Consul Agent sends to DogStatsD.

See [Consul's Network Coordinates doc](https://www.consul.io/docs/internals/coordinates.html) if you're curious about how the network latency metrics are calculated.

### Events

`consul.new_leader`:

The Datadog Agent emits an event when the Consul cluster elects a new leader, tagging it with `prev_consul_leader`, `curr_consul_leader`, and `consul_datacenter`.

### Service Checks

`consul.check`:

The Datadog Agent submits a service check for each of Consul's health checks, tagging each with:

* `service:<name>`, if Consul reports a `ServiceName`
* `consul_service_id:<id>`, if Consul reports a `ServiceID`

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading

* [Monitor Consul health and performance with Datadog](https://www.datadoghq.com/blog/monitor-consul-health-and-performance-with-datadog)
* [Consul at Datadog](https://engineering.datadoghq.com/consul-at-datadog/)
