# Agent Check: Envoy
## Overview

This check collects distributed system observability metrics from [Envoy][1].

## Setup

### Installation

The Envoy check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your server.

#### via Istio

If you are using Envoy as part of [Istio][6], to access Envoy's [admin endpoint][5] you need to set Istio's [proxyAdminPort][7].

#### Standard

There are 2 ways to setup the `/stats` endpoint:

##### Unsecured stats endpoint

Here's an example Envoy admin configuration:

```yaml
admin:
  access_log_path: "/dev/null"
  address:
    socket_address:
      address: 0.0.0.0
      port_value: 8001
```

##### Secured stats endpoint

Create a listener/vhost that routes to the admin endpoint (Envoy connecting to itself), but only has a route for `/stats`; all other routes get a static/error response. Additionally, this allows nice integration with L3 filters for auth, for example.

Here's an example config (from [this gist][13]):

```yaml
admin:
  access_log_path: /dev/null
  address:
    socket_address:
      protocol: TCP
      address: 127.0.0.1
      port_value: 8081
static_resources:
  listeners:
    - address:
        socket_address:
          protocol: TCP
          address: 0.0.0.0
          port_value: 80
      filter_chains:
        - filters:
            - name: envoy.http_connection_manager
              config:
                codec_type: AUTO
                stat_prefix: ingress_http
                route_config:
                  virtual_hosts:
                    - name: backend
                      domains:
                        - "*"
                      routes:
                        - match:
                            prefix: /stats
                          route:
                            cluster: service_stats
                http_filters:
                  - name: envoy.router
                    config:
  clusters:
    - name: service_stats
      connect_timeout: 0.250s
      type: LOGICAL_DNS
      lb_policy: ROUND_ROBIN
      hosts:
        - socket_address:
            protocol: TCP
            address: 127.0.0.1
            port_value: 8001
```

### Configuration

1. Edit the `envoy.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][14] to start collecting your Envoy performance data.
  See the [sample envoy.d/conf.yaml][4] for all available configuration options.

2. Check if the Datadog Agent can access Envoy's [admin endpoint][5].

3. [Restart the Agent][3]

Setting | Description
--- | ---
`stats_url` | (REQUIRED) The admin stats endpoint, e.g. `http://localhost:80/stats`. Add a `?usedonly` on the end if you wish to ignore unused metrics instead of reporting them as `0`.
`tags` | A list of custom tags to apply to this instance.
`metric_whitelist` | A list of regular expressions.
`metric_blacklist` | A list of regular expressions.
`cache_metrics` | Cache results of whitelist/blacklist to decrease CPU utilization, at the expense of some memory (default is `true`).
`username` | The username to authenticate with if behind basic auth.
`password` | The password to authenticate with if behind basic auth.
`verify_ssl` | This instructs the check to validate SSL certificates when connecting to Envoy. Defaulting to `true`, set to `false` if you want to disable SSL certificate validation.
`skip_proxy` | If `true`, the check bypasses any proxy settings enabled and attempt to reach Envoy directly.
`timeout` | A custom timeout for network requests in seconds (default is 20).

#### Metric filtering

Metrics can be filtered using a regular expression `metric_whitelist` or `metric_blacklist`. If both are used, then whitelist is applied first, and then blacklist is applied on the resulting set.

The filtering occurs before tag extraction, so you have the option to have certain tags decide whether or not to keep or ignore metrics. An exhaustive list of all metrics and tags can be found in [metrics.py][15]. Let's walk through an example of Envoy metric tagging!

```python
...
'cluster.grpc.success': {
    'tags': (
        ('cluster_name', ),
        ('grpc_service', 'grpc_method', ),
        (),
    ),
    ...
},
...
```

Here there are `3` tag sequences: `('cluster_name')`, `('grpc_service', 'grpc_method')`, and empty `()`. The number of sequences corresponds exactly to how many metric parts there are. For this metric, there are `3` parts: `cluster`, `grpc`, and `success`. Envoy separates everything with a `.`, hence the final metric name would be:

`cluster.<cluster_name>.grpc.<grpc_service>.<grpc_method>.success`

If you care only about the cluster name and grpc service, you would add this to your whitelist:

`^cluster\.(cluster5|cluster7)\.grpc\.serviceXYZ\.`

### Validation

[Run the Agent's `status` subcommand][8] and look for `envoy` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][9] for a list of metrics provided by this integration.

See [metrics.py][10] for a list of tags sent by each metric.

### Events

The Envoy check does not include any events at this time.

### Service Checks

`envoy.can_connect`:

Returns CRITICAL if the Agent cannot connect to Envoy to collect metrics, otherwise OK.

## Troubleshooting

Need help? Contact [Datadog Support][11].


[1]: https://www.envoyproxy.io
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://github.com/DataDog/integrations-core/blob/master/envoy/datadog_checks/envoy/data/conf.yaml.example
[5]: https://www.envoyproxy.io/docs/envoy/latest/operations/admin
[6]: https://istio.io
[7]: https://istio.io/docs/reference/config/
[8]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[9]: https://github.com/DataDog/integrations-core/blob/master/envoy/metadata.csv
[10]: https://github.com/DataDog/integrations-core/blob/master/envoy/datadog_checks/envoy/metrics.py
[11]: https://docs.datadoghq.com/help/
[13]: https://gist.github.com/ofek/6051508cd0dfa98fc6c13153b647c6f8
[14]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
[15]: https://github.com/DataDog/integrations-core/blob/master/envoy/datadog_checks/envoy/metrics.py
