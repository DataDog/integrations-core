# Consul Integration

# Overview

The Datadog Agent collects many metrics from Consul nodes, including those for:

* Total Consul peers
* Node health - given a service, how many of its nodes are up, passing, warning, critical?
* Service health - given a node, how many of its services are up, passing, warning, critical?
* Network coordinates - inter-datacenter and intra-datacenter latencies

The Agent also sends service checks and emits events for Consul Health Checks and leader elections, respectively.

The _Consul_ Agent can provide its internal health metrics via DogStatsD, including those related to:

* Serf events and member flaps
* The Raft protocol
* DNS performance

And many more.

# Installation

The Datadog Agent's Consul Check is included in the Agent package, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Consul nodes. If you need the newest version of the Consul check, install the `dd-check-consul` package; this package's check will override the one packaged with the Agent. See the [integrations-core](https://github.com/DataDog/integrations-core#installing-the-integrations) repository for more details.

# Configuration

### Connect Datadog Agent to Consul Agent

Create a `consul.yaml` in the Datadog Agent's `conf.d` directory:

```
init_config:

instances:
    # Where your Consul HTTP Server Lives
    # Use 'https' if your Consul setup is configured for SSL
    - url: http://localhost:8500

      # submit per-service node status and per-node service status?
      catalog_checks: yes

      # emit leader election events
      self_leader_check: yes

      network_latency_checks: yes
```

See the [sample consul.yaml](https://github.com/DataDog/integrations-core/blob/master/consul/conf.yaml.example) for all available configuration options. If your Consul HTTP server uses SSL, see the file for options to provide SSL keys and certificates.

Restart the Agent to start sending Consul metrics to Datadog.

### Connect Consul Agent to DogStatsD

In your main Consul configuration file, add `dogstatsd_addr` under the top-level `telemetry` option:

```
{
  ...
  "telemetry": {
    "dogstatsd_addr": "127.0.0.1:8125"
  }
  ...
}
```

Reload the Consul Agent to start sending more Consul metrics to DogStatsD.

# Validation

### Datadog Agent to Consul Agent

Run the Agent's `info` subcommand and look for `consul` under the Checks section:

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

Also, if your Consul nodes have debug logging enabled, you'll see the Datadog Agent's regular requests in the Consul log:

```
    2017/03/27 21:38:12 [DEBUG] http: Request GET /v1/status/leader (59.344µs) from=127.0.0.1:53768
    2017/03/27 21:38:12 [DEBUG] http: Request GET /v1/status/peers (62.678µs) from=127.0.0.1:53770
    2017/03/27 21:38:12 [DEBUG] http: Request GET /v1/health/state/any (106.725µs) from=127.0.0.1:53772
    2017/03/27 21:38:12 [DEBUG] http: Request GET /v1/catalog/services (79.657µs) from=127.0.0.1:53774
    2017/03/27 21:38:12 [DEBUG] http: Request GET /v1/health/service/consul (153.917µs) from=127.0.0.1:53776
    2017/03/27 21:38:12 [DEBUG] http: Request GET /v1/coordinate/datacenters (71.778µs) from=127.0.0.1:53778
    2017/03/27 21:38:12 [DEBUG] http: Request GET /v1/coordinate/nodes (84.95µs) from=127.0.0.1:53780
```

### Consul Agent to DogStatsD

Use `netstat` to verify that Consul is sending its metrics via UDP:

```
$ sudo netstat -nup | grep "127.0.0.1:8125.*ESTABLISHED"
udp        0      0 127.0.0.1:53874         127.0.0.1:8125          ESTABLISHED 23176/consul
```

# Compatibility

The Consul check is compatible with all major platforms.

# Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/consul/metadata.csv) for a list of metrics provided by the Datadog Agent's Consul check.

See the [Consul docs](https://www.consul.io/docs/agent/telemetry.html) for a list of metrics the Consul Agent sends to DogStatsD.

# Service Checks

`consul.check`:

The Agent creates a service check for each Consul Health Check in your cluster, tagging each with:

* `service:<name>` if Consul reports a `ServiceName`
* `consul_service_id:<id>` if Consul reports a `ServiceID`

# Events

`consul.new_leader`:

The Datadog Agent emits an event when the Consul cluster elects a new leader, tagging it with `prev_consul_leader`, `curr_consul_leader`, and `consul_datacenter`. 
