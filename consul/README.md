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




# Validation

```
    2017/03/27 21:38:12 [DEBUG] http: Request GET /v1/status/leader (59.344µs) from=127.0.0.1:53768
    2017/03/27 21:38:12 [DEBUG] http: Request GET /v1/status/peers (62.678µs) from=127.0.0.1:53770
    2017/03/27 21:38:12 [DEBUG] http: Request GET /v1/health/state/any (106.725µs) from=127.0.0.1:53772
    2017/03/27 21:38:12 [DEBUG] http: Request GET /v1/catalog/services (79.657µs) from=127.0.0.1:53774
    2017/03/27 21:38:12 [DEBUG] http: Request GET /v1/health/service/consul (153.917µs) from=127.0.0.1:53776
    2017/03/27 21:38:12 [DEBUG] http: Request GET /v1/coordinate/datacenters (71.778µs) from=127.0.0.1:53778
    2017/03/27 21:38:12 [DEBUG] http: Request GET /v1/coordinate/nodes (84.95µs) from=127.0.0.1:53780
```

# Troubleshooting

# Compatibility

The Consul check is compatible with all major platforms

# Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/consul/metadata.csv) for a list of metrics provided by the Datadog Agent's Consul check.

See the [Consul Agent docs](https://www.consul.io/docs/agent/telemetry.html) for a list of metrics the Consul Agent sents to DogStatsD.
