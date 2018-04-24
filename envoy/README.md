# Agent Check: Envoy
## Overview

This check collects distributed system observability metrics from [Envoy][1].

## Setup
### Installation

The Envoy check is packaged with the Agent, so simply [install the Agent][2] on your server.

If you need the newest version of the Envoy check, install the `dd-check-envoy` package; this package's check overrides the one packaged with the Agent. See the [integrations-core repository README.md for more details][3].

### Configuration

Create a file `envoy.yaml` in the Datadog Agent's `conf.d` directory. See the [sample envoy.yaml][4] for all available configuration options.

Be sure the Datadog Agent can access Envoy's [admin endpoint][5].

#### via Istio

If you are using Envoy as part of [Istio][6], to access Envoy's [admin endpoint](https://www.envoyproxy.io/docs/envoy/latest/operations/admin) you need to set Istio's [proxyAdminPort][7].

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

Here's an example config (from [this gist](https://gist.github.com/ofek/6051508cd0dfa98fc6c13153b647c6f8)):

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

### Validation

[Run the Agent's `status` subcommand][8] and look for `envoy` under the Checks section:

```
  Checks
  ======
    [...]

    envoy
    -----
      - instance #0 [OK]
      - Collected 244 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The Envoy check is compatible with all platforms.

## Data Collected
### Metrics

See [metadata.csv][9] for a list of metrics provided by this check.
See [metrics.py][10] for a list of tags sent by each metric.

### Events

The Envoy check does not include any events at this time.

### Service Checks

`envoy.can_connect`:

Returns CRITICAL if the Agent cannot connect to Envoy to collect metrics, otherwise OK.

## Troubleshooting

Need help? Contact [Datadog Support][11].

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog][12]


[1]: https://www.envoyproxy.io
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/faq/install-core-extra/
[4]: https://github.com/DataDog/integrations-core/blob/master/envoy/conf.yaml.example
[5]: https://www.envoyproxy.io/docs/envoy/latest/operations/admin
[6]: https://istio.io
[7]: https://istio.io/docs/reference/config/istio.mesh.v1alpha1.html#ProxyConfig
[8]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[9]: https://github.com/DataDog/integrations-core/blob/master/envoy/metadata.csv
[10]: https://github.com/DataDog/integrations-core/blob/master/envoy/datadog_checks/envoy/metrics.py
[11]: http://docs.datadoghq.com/help/
[12]: https://www.datadoghq.com/blog/
