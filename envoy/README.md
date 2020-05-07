# Agent Check: Envoy

## Overview

This check collects distributed system observability metrics from [Envoy][1].

## Setup

### Installation

The Envoy check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your server.

#### via Istio

If you are using Envoy as part of [Istio][3], to access Envoy's [admin endpoint][4] you need to set Istio's [proxyAdminPort][5].

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

Here's an example config (from [this gist][6]):

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

#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

##### Metric collection

1. Edit the `envoy.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][7] to start collecting your Envoy performance data. See the [sample envoy.d/conf.yaml][8] for all available configuration options.

    ```yaml
    init_config:

    instances:
      ## @param stats_url - string - required
      ## The admin endpoint to connect to. It must be accessible:
      ## https://www.envoyproxy.io/docs/envoy/latest/operations/admin
      ## Add a `?usedonly` on the end if you wish to ignore
      ## unused metrics instead of reporting them as `0`.
      #
      - stats_url: http://localhost:80/stats
    ```

2. Check if the Datadog Agent can access Envoy's [admin endpoint][4].
3. [Restart the Agent][9].

###### Metric filtering

Metrics can be filtered using a regular expression `metric_whitelist` or `metric_blacklist`. If both are used, then whitelist is applied first, and then blacklist is applied on the resulting set.

The filtering occurs before tag extraction, so you have the option to have certain tags decide whether or not to keep or ignore metrics. An exhaustive list of all metrics and tags can be found in [metrics.py][10]. Let's walk through an example of Envoy metric tagging!

```python
...
'cluster.grpc.success': {
    'tags': (
        ('<CLUSTER_NAME>', ),
        ('<GRPC_SERVICE>', '<GRPC_METHOD>', ),
        (),
    ),
    ...
},
...
```

Here there are `3` tag sequences: `('<CLUSTER_NAME>')`, `('<GRPC_SERVICE>', '<GRPC_METHOD>')`, and empty `()`. The number of sequences corresponds exactly to how many metric parts there are. For this metric, there are `3` parts: `cluster`, `grpc`, and `success`. Envoy separates everything with a `.`, hence the final metric name would be:

`cluster.<CLUSTER_NAME>.grpc.<GRPC_SERVICE>.<GRPC_METHOD>.success`

If you care only about the cluster name and grpc service, you would add this to your whitelist:

`^cluster\.<CLUSTER_NAME>\.grpc\.<GRPC_SERVICE>\.`

##### Log collection

_Available for Agent versions >6.0_

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Next, edit `envoy.d/conf.yaml` by uncommenting the `logs` lines at the bottom. Update the logs `path` with the correct path to your Envoy log files.

   ```yaml
   logs:
     - type: file
       path: /var/log/envoy.log
       source: envoy
       service: envoy
   ```

3. [Restart the Agent][9].

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][11] for guidance on applying the parameters below.

##### Metric collection

| Parameter            | Value                                      |
| -------------------- | ------------------------------------------ |
| `<INTEGRATION_NAME>` | `envoy`                                    |
| `<INIT_CONFIG>`      | blank or `{}`                              |
| `<INSTANCE_CONFIG>`  | `{"stats_url": "http://%%host%%:80/stats}` |

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes log collection documentation][12].

| Parameter      | Value                                              |
| -------------- | -------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "envoy", "service": "<SERVICE_NAME>"}` |

### Validation

[Run the Agent's status subcommand][13] and look for `envoy` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][14] for a list of metrics provided by this integration.

See [metrics.py][10] for a list of tags sent by each metric.

### Events

The Envoy check does not include any events.

### Service Checks

**envoy.can_connect**:<br>
Returns `CRITICAL` if the Agent cannot connect to Envoy to collect metrics, otherwise returns `OK`.

## Troubleshooting

Need help? Contact [Datadog support][15].

[1]: https://www.envoyproxy.io
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://istio.io
[4]: https://www.envoyproxy.io/docs/envoy/latest/operations/admin
[5]: https://istio.io/docs/reference/config
[6]: https://gist.github.com/ofek/6051508cd0dfa98fc6c13153b647c6f8
[7]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[8]: https://github.com/DataDog/integrations-core/blob/master/envoy/datadog_checks/envoy/data/conf.yaml.example
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[10]: https://github.com/DataDog/integrations-core/blob/master/envoy/datadog_checks/envoy/metrics.py
[11]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[12]: https://docs.datadoghq.com/agent/kubernetes/log/
[13]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[14]: https://github.com/DataDog/integrations-core/blob/master/envoy/metadata.csv
[15]: https://docs.datadoghq.com/help/
